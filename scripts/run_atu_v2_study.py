"""
Study runner for Adaptive Targeted Unlearning Version 2 (ATU v2).
Features:
1. In-the-loop development leakage probing (data/dev_leakage_probes.json).
2. LEAKING state assignment and 1.8x sample weight boost.
3. Dual-stopping criterion: requires both canonical log-prob floor AND zero dev probe leakage.
4. Multi-seed evaluation across Seeds 42, 43, 44.
5. Strict post-training evaluation ONCE on unseen adversarial probes (data/test_adversarial_probes.json).
6. Head-to-head comparison against Static NPO baseline and ATU v1.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import json
import random
import hashlib
import yaml
import shutil
import torch
import numpy as np
from datasets import load_dataset
from transformers import PreTrainedTokenizer

from src.models import load_tokenizer, load_peft_target_model
from src.data import load_tofu_raw, TOFUDataset, create_dataloader, format_qa_prompt
from src.metrics import compute_sequence_log_prob, compute_rouge_scores
from src.evaluate import CommonEvaluator
from src.atu.controller import ATUController
from src.atu.trainer import ATUNPOTrainer


def compute_file_hash(filepath: str) -> str:
    if not os.path.exists(filepath):
        return "N/A"
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()[:16]


def evaluate_unseen_holdout(model, tokenizer, device="cuda"):
    holdout_raw = load_dataset("locuslab/TOFU", "holdout01")["train"]
    questions = [x["question"] for x in holdout_raw]
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
    scores = compute_rouge_scores(preds, [x["answer"] for x in holdout_raw])
    return scores["rougeL"]


def evaluate_multiple_choice_split(model, tokenizer, split_name: str, max_samples: int = 50, device="cuda") -> float:
    raw = load_dataset("locuslab/TOFU", split_name)["train"]
    samples = list(raw)[:max_samples]
    correct = 0
    total = len(samples)

    for item in samples:
        q = item["question"]
        ans = item["answer"].strip()
        p = format_qa_prompt(q)
        inputs = tokenizer(p, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=64,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        pred = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        if "\nQuestion:" in pred:
            pred = pred.split("\nQuestion:")[0].strip()
        if ans.lower() in pred.lower():
            correct += 1

    return round(correct / max(1, total), 4)


def evaluate_unseen_test_probes(model, tokenizer, test_probes_file: str, device="cuda") -> dict:
    """
    Evaluates completely unseen test adversarial probes strictly post-training.
    """
    with open(test_probes_file, "r", encoding="utf-8") as f:
        probes = json.load(f)

    records = []
    counts = {"FULL_RECOVERY": 0, "PARTIAL_RECOVERY": 0, "NO_RECOVERY": 0, "TOTAL": 0}

    for probe in probes:
        pid = probe["id"]
        cat = probe.get("category", "unspecified")
        prompt = probe["prompt"]
        tfacts = probe["target_facts"]

        p_text = format_qa_prompt(prompt)
        inputs = tokenizer(p_text, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=96,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        ans = tokenizer.decode(outputs[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        if "\nQuestion:" in ans:
            ans = ans.split("\nQuestion:")[0].strip()
        elif "\n\n" in ans:
            ans = ans.split("\n\n")[0].strip()

        # Semantic classification
        ans_low = ans.lower()
        if any(f.lower() in ans_low for f in tfacts):
            verdict = "FULL_RECOVERY"
        elif any(f.lower().split()[0] in ans_low for f in tfacts if len(f.split()) > 1 and len(f.split()[0]) > 4):
            verdict = "PARTIAL_RECOVERY"
        elif "kuwait" in ans_low and any("kuwait" in f.lower() for f in tfacts):
            verdict = "PARTIAL_RECOVERY"
        else:
            verdict = "NO_RECOVERY"

        counts[verdict] += 1
        counts["TOTAL"] += 1

        records.append({
            "probe_id": pid,
            "category": cat,
            "prompt": prompt,
            "target_facts": tfacts,
            "generated_text": ans,
            "recovery_verdict": verdict,
        })

    return {
        "counts": counts,
        "full_recovery_rate": round(counts["FULL_RECOVERY"] / max(1, counts["TOTAL"]), 4),
        "partial_recovery_rate": round(counts["PARTIAL_RECOVERY"] / max(1, counts["TOTAL"]), 4),
        "no_recovery_rate": round(counts["NO_RECOVERY"] / max(1, counts["TOTAL"]), 4),
        "records": records,
    }


def train_single_atu_v2_seed(seed: int, config: dict, tokenizer, device="cuda"):
    print(f"\n=======================================================")
    print(f"   STARTING ATU v2 FOR SEED {seed}")
    print(f"=======================================================")
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    target_adapter = config.get("target_adapter", "checkpoints/target_tofu_lora")
    ckpt_dir = f"checkpoints/atu_v2_seed{seed}"
    eval_file = f"results/atu_v2_seed{seed}_eval.json"

    model = load_peft_target_model(
        base_model_name="Qwen/Qwen2.5-1.5B-Instruct",
        adapter_path=target_adapter,
        is_trainable=True,
        dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    )

    forget_raw = load_tofu_raw("forget01")
    retain_raw = load_tofu_raw("retain99")
    retain_train_data = [retain_raw[i] for i in range(min(100, len(retain_raw)))]
    retain_val_data = [retain_raw[i] for i in range(100, 125)]

    batch_size = int(config.get("batch_size", 4))
    forget_dataset = TOFUDataset(forget_raw, tokenizer=tokenizer)
    forget_loader = create_dataloader(forget_dataset, tokenizer, batch_size=batch_size, shuffle=True)

    retain_dataset = TOFUDataset(retain_train_data, tokenizer=tokenizer)
    retain_loader = create_dataloader(retain_dataset, tokenizer, batch_size=batch_size, shuffle=True)

    controller = ATUController(
        forget_data=list(forget_raw),
        tokenizer=tokenizer,
        config=config,
    )

    trainer = ATUNPOTrainer(
        model=model,
        tokenizer=tokenizer,
        config=config,
        controller=controller,
        retain_val_data=retain_val_data,
        device=device,
    )

    # Reference log-probs precomputation
    ref_cache = {}
    for ex in forget_raw:
        q = ex["question"]
        ans = ex["answer"]
        p = format_qa_prompt(q)
        stat = compute_sequence_log_prob(model, tokenizer, p, ans, device=device)
        ref_cache[q] = stat["avg_log_prob"]
    trainer.set_reference_cache(ref_cache)

    train_results = trainer.fit_adaptive(
        forget_loader=forget_loader,
        retain_loader=retain_loader,
        max_rounds=config.get("epochs", 8),
    )

    os.makedirs(ckpt_dir, exist_ok=True)
    trainer.save(ckpt_dir, additional_metadata={"controller": "ATU_v2", "seed": seed, "results": train_results})

    trace_file = f"results/atu_v2_seed{seed}_decision_trace.json"
    controller.save_decision_trace(trace_file)

    # Common TOFU Evaluation
    evaluator = CommonEvaluator(
        tokenizer=tokenizer,
        forget_subset="forget01",
        retain_subset="retain99",
        num_retain_samples=40,
        device=device,
    )
    eval_metrics = evaluator.evaluate_model(model, max_new_tokens=96)
    eval_metrics["train_time_sec"] = train_results["train_time_sec"]
    eval_metrics["peak_vram_gb"] = train_results["peak_vram_gb"]
    eval_metrics["total_steps"] = train_results["total_steps"]
    eval_metrics["rounds_completed"] = train_results["rounds_completed"]
    eval_metrics["stopped_early"] = train_results["stopped_early"]
    eval_metrics["stop_reason"] = train_results["stop_reason"]
    eval_metrics["method"] = "atu_v2"
    eval_metrics["seed"] = seed
    eval_metrics["checkpoint_hash"] = compute_file_hash(os.path.join(ckpt_dir, "adapter_model.safetensors"))

    # Generalization & Utility splits
    eval_metrics["holdout01_rougeL"] = evaluate_unseen_holdout(model, tokenizer, device=device)
    eval_metrics["real_authors_acc"] = evaluate_multiple_choice_split(model, tokenizer, "real_authors", max_samples=50, device=device)
    eval_metrics["world_facts_acc"] = evaluate_multiple_choice_split(model, tokenizer, "world_facts", max_samples=50, device=device)

    with open(eval_file, "w", encoding="utf-8") as f:
        json.dump(eval_metrics, f, indent=2)

    # If seed 42, also save canonical checkpoint to checkpoints/atu_v2
    if seed == 42:
        with open("results/atu_v2_eval.json", "w", encoding="utf-8") as f:
            json.dump(eval_metrics, f, indent=2)
        atu_v2_dir = "checkpoints/atu_v2"
        os.makedirs(atu_v2_dir, exist_ok=True)
        for item in os.listdir(ckpt_dir):
            s = os.path.join(ckpt_dir, item)
            d = os.path.join(atu_v2_dir, item)
            if os.path.isfile(s):
                shutil.copy2(s, d)
        with open(os.path.join(atu_v2_dir, "atu_v2_metadata.json"), "w", encoding="utf-8") as f:
            json.dump({
                "version": "2.0.0",
                "method": "ATU_v2",
                "canonical_seed": 42,
                "weights_hash": eval_metrics["checkpoint_hash"],
                "results": eval_metrics,
            }, f, indent=2)

    del model
    torch.cuda.empty_cache()

    return eval_metrics


def run_full_atu_v2_study():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    with open("configs/atu_v2.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    tokenizer = load_tokenizer("Qwen/Qwen2.5-1.5B-Instruct")
    seeds = [42, 43, 44]
    seed_results = {}

    for s in seeds:
        seed_results[s] = train_single_atu_v2_seed(s, config, tokenizer, device=device)

    # Compute 3-seed aggregate statistics
    f_rouges = [seed_results[s]["forget_rougeL"] for s in seeds]
    r_rouges = [seed_results[s]["retain_rougeL"] for s in seeds]
    p_rouges = [seed_results[s]["paraphrase_rougeL"] for s in seeds]
    f_lps = [seed_results[s]["forget_avg_log_prob"] for s in seeds]
    r_lps = [seed_results[s]["retain_avg_log_prob"] for s in seeds]
    trs = [seed_results[s]["truth_ratio_mean"] for s in seeds]
    holdouts = [seed_results[s]["holdout01_rougeL"] for s in seeds]
    reals = [seed_results[s]["real_authors_acc"] for s in seeds]
    worlds = [seed_results[s]["world_facts_acc"] for s in seeds]
    steps = [seed_results[s]["total_steps"] for s in seeds]
    times = [seed_results[s]["train_time_sec"] for s in seeds]

    seed_stats = {
        "forget_rougeL_mean": float(np.mean(f_rouges)),
        "forget_rougeL_std": float(np.std(f_rouges)),
        "retain_rougeL_mean": float(np.mean(r_rouges)),
        "retain_rougeL_std": float(np.std(r_rouges)),
        "paraphrase_rougeL_mean": float(np.mean(p_rouges)),
        "paraphrase_rougeL_std": float(np.std(p_rouges)),
        "forget_avg_log_prob_mean": float(np.mean(f_lps)),
        "forget_avg_log_prob_std": float(np.std(f_lps)),
        "retain_avg_log_prob_mean": float(np.mean(r_lps)),
        "retain_avg_log_prob_std": float(np.std(r_lps)),
        "truth_ratio_mean": float(np.mean(trs)),
        "truth_ratio_std": float(np.std(trs)),
        "holdout01_rougeL_mean": float(np.mean(holdouts)),
        "holdout01_rougeL_std": float(np.std(holdouts)),
        "real_authors_acc_mean": float(np.mean(reals)),
        "world_facts_acc_mean": float(np.mean(worlds)),
        "total_steps_mean": float(np.mean(steps)),
        "train_time_mean": float(np.mean(times)),
    }

    # =========================================================================
    # SINGLE DEFINITIVE EVALUATION ON UNSEEN ADVERSARIAL TEST PROBES
    # =========================================================================
    test_probes_file = config.get("test_adversarial_probes_file", "data/test_adversarial_probes.json")
    print(f"\n=======================================================")
    print(f"   EVALUATING ON UNSEEN ADVERSARIAL TEST PROBES: {test_probes_file}")
    print(f"=======================================================")

    unseen_eval_results = {}

    # 1. Evaluate Static NPO Baseline
    print("Evaluating Static NPO Baseline on unseen test probes...")
    npo_model = load_peft_target_model("Qwen/Qwen2.5-1.5B-Instruct", "checkpoints/npo_forget01", is_trainable=False, dtype=torch.bfloat16)
    unseen_eval_results["static_npo"] = evaluate_unseen_test_probes(npo_model, tokenizer, test_probes_file, device=device)
    del npo_model
    torch.cuda.empty_cache()

    # 2. Evaluate ATU v1 Canonical (Seed 42)
    print("Evaluating ATU v1 on unseen test probes...")
    atu_v1_model = load_peft_target_model("Qwen/Qwen2.5-1.5B-Instruct", "checkpoints/atu_v1", is_trainable=False, dtype=torch.bfloat16)
    unseen_eval_results["atu_v1"] = evaluate_unseen_test_probes(atu_v1_model, tokenizer, test_probes_file, device=device)
    del atu_v1_model
    torch.cuda.empty_cache()

    # 3. Evaluate ATU v2 Seeds
    atu_v2_test_records = []
    for s in seeds:
        print(f"Evaluating ATU v2 Seed {s} on unseen test probes...")
        s_model = load_peft_target_model("Qwen/Qwen2.5-1.5B-Instruct", f"checkpoints/atu_v2_seed{s}", is_trainable=False, dtype=torch.bfloat16)
        res = evaluate_unseen_test_probes(s_model, tokenizer, test_probes_file, device=device)
        unseen_eval_results[f"atu_v2_seed{s}"] = res
        atu_v2_test_records.append(res)
        del s_model
        torch.cuda.empty_cache()

    # Aggregate ATU v2 test rates
    v2_full = float(np.mean([r["full_recovery_rate"] for r in atu_v2_test_records]))
    v2_part = float(np.mean([r["partial_recovery_rate"] for r in atu_v2_test_records]))
    v2_none = float(np.mean([r["no_recovery_rate"] for r in atu_v2_test_records]))

    unseen_eval_results["atu_v2_aggregate"] = {
        "full_recovery_rate_mean": v2_full,
        "partial_recovery_rate_mean": v2_part,
        "no_recovery_rate_mean": v2_none,
    }

    # Save unseen adversarial results
    test_eval_path = "results/atu_v2_unseen_adversarial_eval.json"
    with open(test_eval_path, "w", encoding="utf-8") as f:
        json.dump(unseen_eval_results, f, indent=2)

    # Save overall comprehensive multi-seed study report
    full_report = {
        "atu_v2_seed_results": seed_results,
        "atu_v2_seed_statistics": seed_stats,
        "unseen_adversarial_test_evaluation": unseen_eval_results,
    }
    multi_seed_report_path = "results/atu_v2_multi_seed_report.json"
    with open(multi_seed_report_path, "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    print("\n=======================================================")
    print("   ATU v2 COMPREHENSIVE STUDY COMPLETED SUCCESSFULLY")
    print("=======================================================")
    print(f"Multi-Seed Statistics:\n{json.dumps(seed_stats, indent=2)}")
    print(f"\nUnseen Adversarial Test Results:")
    print(f"  Static NPO : Full={unseen_eval_results['static_npo']['full_recovery_rate']}, Part={unseen_eval_results['static_npo']['partial_recovery_rate']}, None={unseen_eval_results['static_npo']['no_recovery_rate']}")
    print(f"  ATU v1     : Full={unseen_eval_results['atu_v1']['full_recovery_rate']}, Part={unseen_eval_results['atu_v1']['partial_recovery_rate']}, None={unseen_eval_results['atu_v1']['no_recovery_rate']}")
    print(f"  ATU v2 (avg): Full={v2_full}, Part={v2_part}, None={v2_none}")
    print(f"Reports saved to {test_eval_path} and {multi_seed_report_path}")


if __name__ == "__main__":
    run_full_atu_v2_study()
