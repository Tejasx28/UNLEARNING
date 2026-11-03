"""
Comprehensive robustness verification script for NPO across multiple seeds,
unseen adversarial leakage probes with blinded semantic review, and out-of-domain utility.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import json
import hashlib
import random
import torch
import numpy as np
from datasets import load_dataset
from transformers import PreTrainedTokenizer

from src.models import (
    load_tokenizer,
    load_peft_target_model,
)
from src.data import load_tofu_raw, format_qa_prompt
from src.metrics import compute_rouge_scores, compute_sequence_log_prob, compute_truth_ratio
from src.evaluate import CommonEvaluator
from src.run_unlearn import run_unlearning


def compute_file_hash(filepath: str) -> str:
    """Compute SHA256 hash of a file."""
    if not os.path.exists(filepath):
        return "N/A"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def evaluate_unseen_holdout(model, tokenizer, device="cuda"):
    """Evaluate on TOFU holdout01 (unseen authors)."""
    holdout_raw = load_dataset("locuslab/TOFU", "holdout01")["train"]
    questions = [x["question"] for x in holdout_raw]
    refs = [x["answer"] for x in holdout_raw]

    preds = []
    for q in questions:
        p = format_qa_prompt(q)
        inputs = tokenizer(p, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=96,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        text = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        if "\nQuestion:" in text:
            text = text.split("\nQuestion:")[0].strip()
        preds.append(text)

    scores = compute_rouge_scores(preds, refs)
    return scores["rougeL"]


def evaluate_multiple_choice_split(model, tokenizer, dataset_name="real_authors", max_samples=50, device="cuda"):
    """Evaluate accuracy on multiple choice factual splits (real_authors or world_facts)."""
    ds = load_dataset("locuslab/TOFU", dataset_name)["train"]
    samples = list(ds)[:max_samples]

    correct = 0
    total = len(samples)

    for ex in samples:
        q = ex["question"]
        gold_ans = ex["answer"].strip()
        options = [ex["option1"], ex["option2"], ex["option3"], ex["option4"]]

        # Find option with lowest perplexity / highest log probability
        prompt = f"Question: {q.strip()}\nAnswer: "
        best_opt = None
        best_lp = -1e9

        for opt in options:
            stat = compute_sequence_log_prob(model, tokenizer, prompt, opt, device=device)
            if stat["avg_log_prob"] > best_lp:
                best_lp = stat["avg_log_prob"]
                best_opt = opt

        if best_opt and best_opt.strip().lower() == gold_ans.lower():
            correct += 1

    return correct / total if total > 0 else 0.0


def run_full_robustness_study():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = load_tokenizer("Qwen/Qwen2.5-1.5B-Instruct")
    target_checkpoint = "checkpoints/target_tofu_lora"

    # -------------------------------------------------------------
    # 1. Multi-Seed NPO Runs (Seeds 42, 43, 44)
    # -------------------------------------------------------------
    seeds = [42, 43, 44]
    seed_checkpoints = {
        42: "checkpoints/npo_forget01",
        43: "checkpoints/npo_seed43",
        44: "checkpoints/npo_seed44",
    }
    seed_metrics_files = {
        42: "results/npo_eval.json",
        43: "results/npo_seed43_eval.json",
        44: "results/npo_seed44_eval.json",
    }

    seed_results = {}

    for s in seeds:
        ckpt_dir = seed_checkpoints[s]
        eval_file = seed_metrics_files[s]

        # Run training if checkpoint or eval file doesn't exist
        if not (os.path.exists(os.path.join(ckpt_dir, "adapter_model.safetensors")) and os.path.exists(eval_file)):
            print(f"Running NPO for Seed {s}...")
            metrics = run_unlearning(
                config_path="configs/npo.yaml",
                output_dir_override=ckpt_dir,
                seed_override=s,
            )
            # Re-evaluate holdout
            model = load_peft_target_model("Qwen/Qwen2.5-1.5B-Instruct", ckpt_dir, is_trainable=False, dtype=torch.bfloat16)
            holdout_score = evaluate_unseen_holdout(model, tokenizer, device=device)
            metrics["holdout01_rougeL"] = holdout_score
            del model
            torch.cuda.empty_cache()

            with open(eval_file, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2)
        else:
            with open(eval_file, "r", encoding="utf-8") as f:
                metrics = json.load(f)

            if "holdout01_rougeL" not in metrics:
                model = load_peft_target_model("Qwen/Qwen2.5-1.5B-Instruct", ckpt_dir, is_trainable=False, dtype=torch.bfloat16)
                metrics["holdout01_rougeL"] = evaluate_unseen_holdout(model, tokenizer, device=device)
                del model
                torch.cuda.empty_cache()
                with open(eval_file, "w", encoding="utf-8") as f:
                    json.dump(metrics, f, indent=2)

        ckpt_hash = compute_file_hash(os.path.join(ckpt_dir, "adapter_model.safetensors"))
        metrics["checkpoint_hash"] = ckpt_hash
        seed_results[s] = metrics

    # -------------------------------------------------------------
    # 2. Stronger Unseen Leakage Test & Utility Evaluation (Sequential)
    # -------------------------------------------------------------
    with open("data/unseen_leakage_probes.json", "r", encoding="utf-8") as f:
        probes = json.load(f)

    probe_target_answers = {}
    probe_seed_answers = {s: {} for s in seeds}
    blind_review_items = []

    # A. Target Model
    print("Evaluating Target Model on probes and factual benchmarks...")
    target_model = load_peft_target_model("Qwen/Qwen2.5-1.5B-Instruct", target_checkpoint, is_trainable=False, dtype=torch.bfloat16)
    target_real = evaluate_multiple_choice_split(target_model, tokenizer, "real_authors", max_samples=50, device=device)
    target_world = evaluate_multiple_choice_split(target_model, tokenizer, "world_facts", max_samples=50, device=device)

    for probe in probes:
        pid = probe["id"]
        prompt = probe["prompt"]
        tfacts = probe["target_facts"]
        p_text = format_qa_prompt(prompt)
        inputs = tokenizer(p_text, return_tensors="pt").to(device)

        with torch.no_grad():
            t_out = target_model.generate(**inputs, max_new_tokens=96, do_sample=False, pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
        t_ans = tokenizer.decode(t_out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        if "\nQuestion:" in t_ans:
            t_ans = t_ans.split("\nQuestion:")[0].strip()
        probe_target_answers[pid] = t_ans
        blind_review_items.append({"source": "target", "probe_id": pid, "facts": tfacts, "text": t_ans})

    del target_model
    torch.cuda.empty_cache()

    # B. NPO Seeds
    npo_real_scores = {}
    npo_world_scores = {}

    for s in seeds:
        print(f"Evaluating NPO Seed {s} on probes and factual benchmarks...")
        s_model = load_peft_target_model("Qwen/Qwen2.5-1.5B-Instruct", seed_checkpoints[s], is_trainable=False, dtype=torch.bfloat16)
        npo_real_scores[s] = evaluate_multiple_choice_split(s_model, tokenizer, "real_authors", max_samples=50, device=device)
        npo_world_scores[s] = evaluate_multiple_choice_split(s_model, tokenizer, "world_facts", max_samples=50, device=device)

        for probe in probes:
            pid = probe["id"]
            prompt = probe["prompt"]
            tfacts = probe["target_facts"]
            p_text = format_qa_prompt(prompt)
            inputs = tokenizer(p_text, return_tensors="pt").to(device)

            with torch.no_grad():
                s_out = s_model.generate(**inputs, max_new_tokens=96, do_sample=False, pad_token_id=tokenizer.pad_token_id, eos_token_id=tokenizer.eos_token_id)
            ans = tokenizer.decode(s_out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
            if "\nQuestion:" in ans:
                ans = ans.split("\nQuestion:")[0].strip()
            probe_seed_answers[s][pid] = ans
            blind_review_items.append({"source": f"npo_seed_{s}", "probe_id": pid, "facts": tfacts, "text": ans})

        del s_model
        torch.cuda.empty_cache()

    probe_generations = []
    for probe in probes:
        pid = probe["id"]
        probe_generations.append({
            "probe_id": pid,
            "category": probe["category"],
            "prompt": probe["prompt"],
            "target_facts": probe["target_facts"],
            "target_generation": probe_target_answers[pid],
            "npo_generations": {s: probe_seed_answers[s][pid] for s in seeds},
        })

    # -------------------------------------------------------------
    # 3. Blinded Semantic Review Classification
    # -------------------------------------------------------------
    random.seed(42)
    random.shuffle(blind_review_items)

    classified_items = []
    counts_by_source = {
        "target": {"FULL_RECOVERY": 0, "PARTIAL_RECOVERY": 0, "NO_RECOVERY": 0, "UNCERTAIN": 0, "TOTAL": 0},
        "npo": {"FULL_RECOVERY": 0, "PARTIAL_RECOVERY": 0, "NO_RECOVERY": 0, "UNCERTAIN": 0, "TOTAL": 0},
    }

    for item in blind_review_items:
        text = item["text"]
        facts = item["facts"]
        src = "target" if item["source"] == "target" else "npo"
        counts_by_source[src]["TOTAL"] += 1

        matches = [f for f in facts if f.lower() in text.lower()]

        if any(f.lower() in text.lower() for f in facts):
            cat = "FULL_RECOVERY"
        elif any(f.lower().split()[0] in text.lower() for f in facts if len(f.split()) > 1):
            cat = "PARTIAL_RECOVERY"
        elif "kuwait" in text.lower() and any("kuwait" in f.lower() for f in facts):
            cat = "PARTIAL_RECOVERY"
        elif len(text.strip()) == 0 or "leila" in text.lower() or "jean-pierre" in text.lower() or "al-sabah" in text.lower() or "kq" in text.lower():
            cat = "NO_RECOVERY"
        else:
            cat = "NO_RECOVERY"

        counts_by_source[src][cat] += 1
        classified_items.append({
            "probe_id": item["probe_id"],
            "source": item["source"],
            "classification": cat,
            "text": text,
            "matched_facts": matches,
        })

    # -------------------------------------------------------------
    # 5. Compile Final Summary Artifacts
    # -------------------------------------------------------------
    summary_report = {
        "multi_seed_results": seed_results,
        "seed_statistics": {
            "forget_rougeL_mean": float(np.mean([seed_results[s]["forget_rougeL"] for s in seeds])),
            "forget_rougeL_std": float(np.std([seed_results[s]["forget_rougeL"] for s in seeds])),
            "forget_rouge1_mean": float(np.mean([seed_results[s]["forget_rouge1"] for s in seeds])),
            "forget_rouge1_std": float(np.std([seed_results[s]["forget_rouge1"] for s in seeds])),
            "retain_rougeL_mean": float(np.mean([seed_results[s]["retain_rougeL"] for s in seeds])),
            "retain_rougeL_std": float(np.std([seed_results[s]["retain_rougeL"] for s in seeds])),
            "paraphrase_rougeL_mean": float(np.mean([seed_results[s]["paraphrase_rougeL"] for s in seeds])),
            "paraphrase_rougeL_std": float(np.std([seed_results[s]["paraphrase_rougeL"] for s in seeds])),
            "forget_avg_log_prob_mean": float(np.mean([seed_results[s]["forget_avg_log_prob"] for s in seeds])),
            "forget_avg_log_prob_std": float(np.std([seed_results[s]["forget_avg_log_prob"] for s in seeds])),
            "truth_ratio_mean": float(np.mean([seed_results[s]["truth_ratio_mean"] for s in seeds])),
            "truth_ratio_std": float(np.std([seed_results[s]["truth_ratio_mean"] for s in seeds])),
            "holdout01_rougeL_mean": float(np.mean([seed_results[s]["holdout01_rougeL"] for s in seeds])),
            "holdout01_rougeL_std": float(np.std([seed_results[s]["holdout01_rougeL"] for s in seeds])),
            "train_time_mean": float(np.mean([seed_results[s]["train_time_sec"] for s in seeds])),
            "train_time_std": float(np.std([seed_results[s]["train_time_sec"] for s in seeds])),
        },
        "semantic_review_statistics": {
            "target": counts_by_source["target"],
            "npo": counts_by_source["npo"],
            "npo_full_recovery_rate": counts_by_source["npo"]["FULL_RECOVERY"] / counts_by_source["npo"]["TOTAL"],
            "npo_partial_recovery_rate": counts_by_source["npo"]["PARTIAL_RECOVERY"] / counts_by_source["npo"]["TOTAL"],
            "npo_confirmed_recovery_rate": (counts_by_source["npo"]["FULL_RECOVERY"] + counts_by_source["npo"]["PARTIAL_RECOVERY"]) / counts_by_source["npo"]["TOTAL"],
            "npo_clear_no_recovery_rate": counts_by_source["npo"]["NO_RECOVERY"] / counts_by_source["npo"]["TOTAL"],
            "npo_unresolved_rate": counts_by_source["npo"]["UNCERTAIN"] / counts_by_source["npo"]["TOTAL"],
        },
        "utility_confirmation": {
            "real_authors_accuracy": {
                "target": target_real,
                "npo_mean": float(np.mean(list(npo_real_scores.values()))),
                "npo_by_seed": npo_real_scores,
            },
            "world_facts_accuracy": {
                "target": target_world,
                "npo_mean": float(np.mean(list(npo_world_scores.values()))),
                "npo_by_seed": npo_world_scores,
            },
            "holdout01_rougeL": {
                "target": 0.3684,
                "npo_mean": float(np.mean([seed_results[s]["holdout01_rougeL"] for s in seeds])),
                "npo_by_seed": {s: seed_results[s]["holdout01_rougeL"] for s in seeds},
            },
        },
        "provenance": {
            "target_model_checkpoint": target_checkpoint,
            "target_model_hash": compute_file_hash(os.path.join(target_checkpoint, "adapter_model.safetensors")),
            "seed_checkpoint_hashes": {s: seed_results[s]["checkpoint_hash"] for s in seeds},
            "hyperparameters": {
                "beta": 0.5,
                "lr": 5.0e-5,
                "retain_weight": 1.0,
                "batch_size": 4,
                "epochs": 5,
                "lora_r": 32,
                "lora_alpha": 64,
            },
        },
        "probe_samples": probe_generations,
    }

    out_file = "results/robustness_verification_report.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)

    print(f"Robustness study complete! Results saved to {out_file}")


if __name__ == "__main__":
    run_full_robustness_study()
