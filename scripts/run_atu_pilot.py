"""
Pilot execution script for Adaptive Targeted Unlearning (ATU) Controller with NPO.
Demonstrates closed-loop target state tracking, dynamic weight adaptation,
retain guard safety checks, and early stopping on TOFU forget01.
"""

import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
import logging
import torch
import yaml
from transformers import PreTrainedTokenizer

from src.models import load_tokenizer, load_peft_target_model
from src.data import load_tofu_raw, TOFUDataset, create_dataloader, format_qa_prompt
from src.metrics import compute_sequence_log_prob
from src.evaluate import CommonEvaluator, print_evaluation_summary
from src.atu.controller import ATUController
from src.atu.trainer import ATUNPOTrainer

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def run_atu_pilot(config_path: str = "configs/atu_npo.yaml"):
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    base_model_name = config.get("base_model", "Qwen/Qwen2.5-1.5B-Instruct")
    target_adapter = config.get("target_adapter", "checkpoints/target_tofu_lora")
    output_dir = config.get("output_dir", "checkpoints/atu_npo_pilot")
    batch_size = int(config.get("batch_size", 4))
    seed_val = int(config.get("seed", 42))

    torch.manual_seed(seed_val)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed_val)

    logger.info("--- ATU PILOT: Initializing Model and Tokenizer ---")
    tokenizer = load_tokenizer(base_model_name)
    model = load_peft_target_model(
        base_model_name=base_model_name,
        adapter_path=target_adapter,
        is_trainable=True,
        dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    )

    # 1. Prepare Datasets
    forget_raw = load_tofu_raw("forget01")
    retain_raw = load_tofu_raw("retain99")
    retain_train_data = [retain_raw[i] for i in range(min(100, len(retain_raw)))]
    retain_val_data = [retain_raw[i] for i in range(100, 125)]  # Disjoint 25 validation retain items

    forget_dataset = TOFUDataset(forget_raw, tokenizer=tokenizer)
    forget_loader = create_dataloader(forget_dataset, tokenizer, batch_size=batch_size, shuffle=True)

    retain_dataset = TOFUDataset(retain_train_data, tokenizer=tokenizer)
    retain_loader = create_dataloader(retain_dataset, tokenizer, batch_size=batch_size, shuffle=True)

    # 2. Instantiate ATU Controller
    logger.info("--- ATU PILOT: Instantiating ATU Controller ---")
    controller = ATUController(
        forget_data=list(forget_raw),
        tokenizer=tokenizer,
        config=config,
    )

    # 3. Instantiate ATU-NPO Trainer
    trainer = ATUNPOTrainer(
        model=model,
        tokenizer=tokenizer,
        config=config,
        controller=controller,
        retain_val_data=retain_val_data,
        device=device,
    )

    # Precompute reference log-probabilities for NPO
    logger.info("Precomputing reference log-probabilities...")
    ref_cache = {}
    for ex in forget_raw:
        q = ex["question"]
        ans = ex["answer"]
        p = format_qa_prompt(q)
        stat = compute_sequence_log_prob(model, tokenizer, p, ans, device=device)
        ref_cache[q] = stat["avg_log_prob"]
    trainer.set_reference_cache(ref_cache)

    # 4. Run Closed-Loop Adaptive Unlearning
    logger.info("--- ATU PILOT: Starting Closed-Loop Adaptive Training ---")
    train_results = trainer.fit_adaptive(
        forget_loader=forget_loader,
        retain_loader=retain_loader,
        max_rounds=config.get("epochs", 5),
    )

    # 5. Save Model and Decision Trace
    os.makedirs(output_dir, exist_ok=True)
    trainer.save(output_dir, additional_metadata={"controller": "ATU", "results": train_results})

    trace_file = "results/atu_pilot_decision_trace.json"
    os.makedirs("results", exist_ok=True)
    controller.save_decision_trace(trace_file)

    # 6. Post-Unlearning Common Evaluation
    logger.info("--- ATU PILOT: Running Post-Unlearning Common Evaluation ---")
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

    print_evaluation_summary(eval_metrics, title="ATU-NPO Pilot Evaluation")

    eval_file = "results/atu_npo_pilot_eval.json"
    with open(eval_file, "w", encoding="utf-8") as f:
        json.dump(eval_metrics, f, indent=2)
    logger.info(f"Pilot evaluation metrics saved to {eval_file}")

    return eval_metrics, train_results


if __name__ == "__main__":
    run_atu_pilot()
