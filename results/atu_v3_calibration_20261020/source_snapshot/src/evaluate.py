"""
Unified evaluation pipeline for TOFU machine unlearning.
Measures Forget ROUGE/Log-Prob, Paraphrase robustness, Truth Ratio, and Retain utility.
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
import torch
import numpy as np
from transformers import PreTrainedModel, PreTrainedTokenizer

from src.data import (
    load_tofu_raw,
    load_perturbed_data,
    format_qa_prompt,
)
from src.metrics import (
    compute_rouge_scores,
    compute_sequence_log_prob,
    generate_answers,
    compute_truth_ratio,
)

logger = logging.getLogger(__name__)


class CommonEvaluator:
    """
    Common unlearning evaluator providing standardized metrics across all methods.
    """

    def __init__(
        self,
        tokenizer: PreTrainedTokenizer,
        forget_subset: str = "forget01",
        retain_subset: str = "retain99",
        num_retain_samples: int = 40,
        device: str = "cuda",
    ):
        self.tokenizer = tokenizer
        self.device = device
        self.forget_subset = forget_subset
        self.retain_subset = retain_subset

        logger.info(f"Loading evaluation datasets: forget={forget_subset}, retain={retain_subset}")
        forget_raw = load_tofu_raw(forget_subset)
        self.forget_data = [dict(x) for x in forget_raw]

        retain_raw = load_tofu_raw(retain_subset)
        # Select first num_retain_samples for fast, reproducible retention checking
        self.retain_data = [dict(retain_raw[i]) for i in range(min(num_retain_samples, len(retain_raw)))]

        perturbed_subset = f"{forget_subset}_perturbed"
        try:
            perturbed_raw = load_perturbed_data(perturbed_subset)
            self.perturbed_data = [dict(x) for x in perturbed_raw]
        except Exception as e:
            logger.warning(f"Could not load {perturbed_subset}: {e}. Falling back to empty.")
            self.perturbed_data = []

    def evaluate_model(
        self,
        model: PreTrainedModel,
        generate_samples: bool = True,
        max_new_tokens: int = 64,
    ) -> Dict[str, Any]:
        """
        Run full evaluation on forget, paraphrase, truth ratio, and retain sets.
        """
        start_time = time.time()
        model.eval()

        results: Dict[str, Any] = {}

        # -------------------------------------------------------------
        # 1. Forget Set Evaluation
        # -------------------------------------------------------------
        forget_questions = [x["question"] for x in self.forget_data]
        forget_refs = [x["answer"] for x in self.forget_data]

        forget_log_probs = []
        for x in self.forget_data:
            p = format_qa_prompt(x["question"])
            lp = compute_sequence_log_prob(model, self.tokenizer, p, x["answer"], device=self.device)
            forget_log_probs.append(lp["avg_log_prob"])

        results["forget_avg_log_prob"] = float(np.mean(forget_log_probs))

        if generate_samples:
            forget_preds = generate_answers(
                model, self.tokenizer, forget_questions, max_new_tokens=max_new_tokens, device=self.device
            )
            forget_rouge = compute_rouge_scores(forget_preds, forget_refs)
            results["forget_rouge1"] = forget_rouge["rouge1"]
            results["forget_rouge2"] = forget_rouge["rouge2"]
            results["forget_rougeL"] = forget_rouge["rougeL"]
            results["sample_forget_pred"] = forget_preds[0] if forget_preds else ""
            results["sample_forget_ref"] = forget_refs[0] if forget_refs else ""

        # -------------------------------------------------------------
        # 2. Paraphrase Set Evaluation
        # -------------------------------------------------------------
        if self.perturbed_data:
            para_questions = [x["paraphrased_question"] for x in self.perturbed_data]
            para_refs = [x["paraphrased_answer"] for x in self.perturbed_data]

            para_log_probs = []
            for pq, pa in zip(para_questions, para_refs):
                p = format_qa_prompt(pq)
                lp = compute_sequence_log_prob(model, self.tokenizer, p, pa, device=self.device)
                para_log_probs.append(lp["avg_log_prob"])

            results["paraphrase_avg_log_prob"] = float(np.mean(para_log_probs))

            if generate_samples:
                para_preds = generate_answers(
                    model, self.tokenizer, para_questions, max_new_tokens=max_new_tokens, device=self.device
                )
                para_rouge = compute_rouge_scores(para_preds, para_refs)
                results["paraphrase_rouge1"] = para_rouge["rouge1"]
                results["paraphrase_rouge2"] = para_rouge["rouge2"]
                results["paraphrase_rougeL"] = para_rouge["rougeL"]
                results["sample_para_pred"] = para_preds[0] if para_preds else ""
                results["sample_para_ref"] = para_refs[0] if para_refs else ""

        # -------------------------------------------------------------
        # 3. Truth Ratio Evaluation
        # -------------------------------------------------------------
        if self.perturbed_data:
            tr_stats = compute_truth_ratio(
                model, self.tokenizer, self.perturbed_data, device=self.device
            )
            results["truth_ratio_mean"] = tr_stats["truth_ratio_mean"]
            results["truth_ratio_std"] = tr_stats["truth_ratio_std"]
            results["tr_avg_true_lp"] = tr_stats["avg_true_log_prob"]
            results["tr_avg_pert_lp"] = tr_stats["avg_pert_log_prob"]

        # -------------------------------------------------------------
        # 4. Retain Set Evaluation
        # -------------------------------------------------------------
        retain_questions = [x["question"] for x in self.retain_data]
        retain_refs = [x["answer"] for x in self.retain_data]

        retain_log_probs = []
        for x in self.retain_data:
            p = format_qa_prompt(x["question"])
            lp = compute_sequence_log_prob(model, self.tokenizer, p, x["answer"], device=self.device)
            retain_log_probs.append(lp["avg_log_prob"])

        results["retain_avg_log_prob"] = float(np.mean(retain_log_probs))

        if generate_samples:
            retain_preds = generate_answers(
                model, self.tokenizer, retain_questions, max_new_tokens=max_new_tokens, device=self.device
            )
            retain_rouge = compute_rouge_scores(retain_preds, retain_refs)
            results["retain_rouge1"] = retain_rouge["rouge1"]
            results["retain_rouge2"] = retain_rouge["rouge2"]
            results["retain_rougeL"] = retain_rouge["rougeL"]
            results["sample_retain_pred"] = retain_preds[0] if retain_preds else ""
            results["sample_retain_ref"] = retain_refs[0] if retain_refs else ""

        results["eval_time_sec"] = round(time.time() - start_time, 2)
        return results


def print_evaluation_summary(metrics: Dict[str, Any], title: str = "Evaluation Results"):
    """Format and print evaluation metrics."""
    print("=" * 60)
    print(f" {title}")
    print("=" * 60)
    print(f"Forget ROUGE-L:        {metrics.get('forget_rougeL', 0.0):.4f}")
    print(f"Forget Avg Log-Prob:   {metrics.get('forget_avg_log_prob', 0.0):.4f}")
    print(f"Paraphrase ROUGE-L:    {metrics.get('paraphrase_rougeL', 0.0):.4f}")
    print(f"Paraphrase Avg Log-P:  {metrics.get('paraphrase_avg_log_prob', 0.0):.4f}")
    print(f"Truth Ratio:           {metrics.get('truth_ratio_mean', 0.0):.4f} +/- {metrics.get('truth_ratio_std', 0.0):.4f}")
    print(f"Retain ROUGE-L:        {metrics.get('retain_rougeL', 0.0):.4f}")
    print(f"Retain Avg Log-Prob:   {metrics.get('retain_avg_log_prob', 0.0):.4f}")
    print(f"Evaluation Time:       {metrics.get('eval_time_sec', 0.0)}s")
    print("-" * 60)
    if "sample_forget_pred" in metrics:
        print(f"Sample Forget Ref:  {metrics.get('sample_forget_ref', '')[:90]}...")
        print(f"Sample Forget Pred: {metrics.get('sample_forget_pred', '')[:90]}...")
    print("=" * 60)
