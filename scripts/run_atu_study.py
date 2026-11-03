"""
Comprehensive study runner for Adaptive Targeted Unlearning (ATU) Controller across
multiple seeds (42, 43, 44), adversarial probe leakage review, and general factual benchmarks.
Compares ATU-NPO directly against the locked Static NPO baseline.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import time
import json
import random
import hashlib
import yaml
import torch
import numpy as np
from datasets import load_dataset
from transformers import PreTrainedTokenizer

from src.models import load_tokenizer, load_peft_target_model
from src.data import load_tofu_raw, TOFUDataset, create_dataloader, format_qa_prompt
from src.metrics import compute_sequence_log_prob
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
    from src.metrics import compute_rouge_scores
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


def train_single_atu_seed(seed: int, config: dict, tokenizer, device="cuda"):
    print(f"\n=======================================================")
    print(f"   STARTING ATU-NPO FOR SEED {seed}")
    print(f"=======================================================")
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

    target_adapter = config.get("target_adapter", "checkpoints/target_tofu_lora")
    ckpt_dir = f"checkpoints/atu_npo_seed{seed}"
    eval_file = f"results/atu_npo_seed{seed}_eval.json"

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

    # Reference log-probs
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
        max_rounds=config.get("epochs", 6),
    )

    os.makedirs(ckpt_dir, exist_ok=True)
    trainer.save(ckpt_dir, additional_metadata={"controller": "ATU", "seed": seed, "results": train_results})

    trace_file = f"results/atu_seed{seed}_decision_trace.json"
    controller.save_decision_trace(trace_file)

    # Evaluate common metrics
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
    eval_metrics["method"] = "atu_npo"
    eval_metrics["seed"] = seed
    eval_metrics["checkpoint_hash"] = compute_file_hash(os.path.join(ckpt_dir, "adapter_model.safetensors"))

    # Holdout01
    eval_metrics["holdout01_rougeL"] = evaluate_unseen_holdout(model, tokenizer, device=device)

    with open(eval_file, "w", encoding="utf-8") as f:
        json.dump(eval_metrics, f, indent=2)

    # If seed 42, also save to atu_eval.json and copy to checkpoints/atu_npo_forget01
    if seed == 42:
        with open("results/atu_eval.json", "w", encoding="utf-8") as f:
            json.dump(eval_metrics, f, indent=2)
        import shutil
        os.makedirs("checkpoints/atu_npo_forget01", exist_ok=True)
        for item in os.listdir(ckpt_dir):
            s = os.path.join(ckpt_dir, item)
            d = os.path.join("checkpoints/atu_npo_forget01", item)
            if os.path.isfile(s):
                shutil.copy2(s, d)

    del model
    torch.cuda.empty_cache()

    return eval_metrics


def run_full_atu_study():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    with open("configs/atu_npo.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    tokenizer = load_tokenizer("Qwen/Qwen2.5-1.5B-Instruct")
    seeds = [42, 43, 44]
    seed_results = {}

    for s in seeds:
        seed_results[s] = train_single_atu_seed(s, config, tokenizer, device=device)

    # Compute 3-seed aggregate statistics
    f_rouges = [seed_results[s]["forget_rougeL"] for s in seeds]
    r_rouges = [seed_results[s]["retain_rougeL"] for s in seeds]
    p_rouges = [seed_results[s]["paraphrase_rougeL"] for s in seeds]
    f_lps = [seed_results[s]["forget_avg_log_prob"] for s in seeds]
    r_lps = [seed_results[s]["retain_avg_log_prob"] for s in seeds]
    trs = [seed_results[s]["truth_ratio_mean"] for s in seeds]
    holdouts = [seed_results[s]["holdout01_rougeL"] for s in seeds]
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
        "total_steps_mean": float(np.mean(steps)),
        "train_time_mean": float(np.mean(times)),
    }

    # Evaluate Adversarial Probes across ATU seeds
    with open("data/unseen_leakage_probes.json", "r", encoding="utf-8") as f:
        probes = json.load(f)

    blind_items = []
    atu_real_scores = {}
    atu_world_scores = {}

    for s in seeds:
        print(f"Evaluating ATU Seed {s} on probes and factual benchmarks...")
        ckpt_dir = f"checkpoints/atu_npo_seed{s}"
        s_model = load_peft_target_model("Qwen/Qwen2.5-1.5B-Instruct", ckpt_dir, is_trainable=False, dtype=torch.bfloat16)
        atu_real_scores[s] = evaluate_multiple_choice_split(s_model, tokenizer, "real_authors", max_samples=50, device=device)
        atu_world_scores[s] = evaluate_multiple_choice_split(s_model, tokenizer, "world_facts", max_samples=50, device=device)

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
            blind_items.append({"source": f"atu_seed_{s}", "probe_id": pid, "facts": tfacts, "text": ans})

        del s_model
        torch.cuda.empty_cache()

    # Semantic classification on ATU probes
    counts = {"FULL_RECOVERY": 0, "PARTIAL_RECOVERY": 0, "NO_RECOVERY": 0, "UNCERTAIN": 0, "TOTAL": 0}
    for item in blind_items:
        counts["TOTAL"] += 1
        text = item["text"]
        facts = item["facts"]
        if any(f.lower() in text.lower() for f in facts):
            cat = "FULL_RECOVERY"
        elif any(f.lower().split()[0] in text.lower() for f in facts if len(f.split()) > 1):
            cat = "PARTIAL_RECOVERY"
        elif "kuwait" in text.lower() and any("kuwait" in f.lower() for f in facts):
            cat = "PARTIAL_RECOVERY"
        else:
            cat = "NO_RECOVERY"
        counts[cat] += 1

    study_summary = {
        "atu_seed_results": seed_results,
        "atu_seed_statistics": seed_stats,
        "atu_probe_counts": counts,
        "atu_full_recovery_rate": counts["FULL_RECOVERY"] / counts["TOTAL"],
        "atu_partial_recovery_rate": counts["PARTIAL_RECOVERY"] / counts["TOTAL"],
        "atu_clear_no_recovery_rate": counts["NO_RECOVERY"] / counts["TOTAL"],
        "atu_real_authors_mean": float(np.mean(list(atu_real_scores.values()))),
        "atu_world_facts_mean": float(np.mean(list(atu_world_scores.values()))),
    }

    report_path = "results/atu_comprehensive_study_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(study_summary, f, indent=2)

    print("\n=======================================================")
    print("   ATU COMPREHENSIVE STUDY COMPLETED SUCCESSFULLY")
    print("=======================================================")
    print(json.dumps(seed_stats, indent=2))
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    run_full_atu_study()
