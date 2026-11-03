"""
Evaluation metrics for unlearning on TOFU benchmark.
Includes ROUGE scores, sequence log-probabilities, Truth Ratio, and paraphrase evaluation.
"""

from typing import List, Dict, Any, Tuple
import math
import numpy as np
import torch
import torch.nn.functional as F
from rouge_score import rouge_scorer
from transformers import PreTrainedModel, PreTrainedTokenizer

from src.data import format_qa_prompt


def compute_rouge_scores(
    predictions: List[str],
    references: List[str],
) -> Dict[str, float]:
    """
    Compute average ROUGE-1, ROUGE-2, and ROUGE-L F1 scores across pairs.
    """
    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    r1_list, r2_list, rl_list = [], [], []

    for pred, ref in zip(predictions, references):
        scores = scorer.score(ref.strip(), pred.strip())
        r1_list.append(scores["rouge1"].fmeasure)
        r2_list.append(scores["rouge2"].fmeasure)
        rl_list.append(scores["rougeL"].fmeasure)

    return {
        "rouge1": float(np.mean(r1_list)) if r1_list else 0.0,
        "rouge2": float(np.mean(r2_list)) if r2_list else 0.0,
        "rougeL": float(np.mean(rl_list)) if rl_list else 0.0,
    }


def compute_sequence_log_prob(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    prompt: str,
    target: str,
    device: str = "cuda",
) -> Dict[str, float]:
    """
    Compute log probability of target text conditioned on prompt text.
    Returns:
      - total_log_prob: sum of log p(target_t | prompt, target_<t)
      - avg_log_prob: normalized by target token count
      - perplexity: exp(-avg_log_prob)
    """
    model.eval()
    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    target_ids = tokenizer.encode(target, add_special_tokens=False)
    if tokenizer.eos_token_id is not None:
        target_ids.append(tokenizer.eos_token_id)

    input_ids = torch.tensor([prompt_ids + target_ids], dtype=torch.long, device=device)
    prompt_len = len(prompt_ids)
    target_len = len(target_ids)

    with torch.no_grad():
        outputs = model(input_ids)
        logits = outputs.logits  # [1, seq_len, vocab_size]

    # Target tokens start at index prompt_len in input_ids
    # Predicted logits for input_ids[k] are at logits[:, k - 1, :]
    shift_logits = logits[0, prompt_len - 1 : prompt_len + target_len - 1, :]
    shift_labels = torch.tensor(target_ids, dtype=torch.long, device=device)

    log_probs = F.log_softmax(shift_logits, dim=-1)
    target_log_probs = log_probs.gather(dim=-1, index=shift_labels.unsqueeze(-1)).squeeze(-1)

    total_lp = float(target_log_probs.sum().item())
    avg_lp = float(target_log_probs.mean().item()) if target_len > 0 else 0.0
    ppl = float(math.exp(-avg_lp)) if avg_lp > -100 else 1e9

    return {
        "total_log_prob": total_lp,
        "avg_log_prob": avg_lp,
        "perplexity": ppl,
        "target_tokens": target_len,
    }


def generate_answers(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    questions: List[str],
    max_new_tokens: int = 64,
    device: str = "cuda",
) -> List[str]:
    """
    Greedy answer generation for a list of questions.
    """
    model.eval()
    answers = []

    for q in questions:
        prompt = format_qa_prompt(q)
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        prompt_len = inputs["input_ids"].shape[1]

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )

        gen_tokens = outputs[0][prompt_len:]
        gen_text = tokenizer.decode(gen_tokens, skip_special_tokens=True).strip()
        # Truncate if model starts generating a subsequent question
        if "\nQuestion:" in gen_text:
            gen_text = gen_text.split("\nQuestion:")[0].strip()
        elif "\n\n" in gen_text:
            gen_text = gen_text.split("\n\n")[0].strip()
        answers.append(gen_text)

    return answers


def compute_truth_ratio(
    model: PreTrainedModel,
    tokenizer: PreTrainedTokenizer,
    perturbed_examples: List[Dict[str, Any]],
    device: str = "cuda",
) -> Dict[str, float]:
    """
    Compute TOFU Truth Ratio:
    Compares normalized log probability of correct paraphrased answer
    against counterfactual perturbed answers.

    Truth Ratio per example:
      avg_{k} sigma(avg_log_prob(true) - avg_log_prob(perturbed_k))
    """
    model.eval()
    truth_ratios = []
    true_log_probs = []
    pert_log_probs = []

    for ex in perturbed_examples:
        pq = ex.get("paraphrased_question", ex["question"])
        pa = ex.get("paraphrased_answer", ex["answer"])
        prompt = format_qa_prompt(pq)

        true_stat = compute_sequence_log_prob(model, tokenizer, prompt, pa, device=device)
        true_lp = true_stat["avg_log_prob"]
        true_log_probs.append(true_lp)

        counterfactuals = ex.get("perturbed_answer", [])
        if not counterfactuals:
            continue

        item_ratios = []
        for distractor in counterfactuals:
            dist_stat = compute_sequence_log_prob(model, tokenizer, prompt, distractor, device=device)
            dist_lp = dist_stat["avg_log_prob"]
            pert_log_probs.append(dist_lp)

            # Sigmoid of log probability difference: 1 / (1 + exp(pert_lp - true_lp))
            diff = true_lp - dist_lp
            # Avoid overflow in sigmoid
            if diff > 50:
                prob_prefer_true = 1.0
            elif diff < -50:
                prob_prefer_true = 0.0
            else:
                prob_prefer_true = 1.0 / (1.0 + math.exp(-diff))

            item_ratios.append(prob_prefer_true)

        if item_ratios:
            truth_ratios.append(float(np.mean(item_ratios)))

    return {
        "truth_ratio_mean": float(np.mean(truth_ratios)) if truth_ratios else 0.0,
        "truth_ratio_std": float(np.std(truth_ratios)) if truth_ratios else 0.0,
        "avg_true_log_prob": float(np.mean(true_log_probs)) if true_log_probs else 0.0,
        "avg_pert_log_prob": float(np.mean(pert_log_probs)) if pert_log_probs else 0.0,
    }
