"""
Unified runner for machine unlearning baselines (GA, NPO, RMU, GradDiff).
Loads target model, executes unlearning algorithm, evaluates post-unlearning performance,
and records comprehensive provenance and metrics.
"""

import os
import sys
import json
import yaml
import argparse
import logging
import torch
from typing import Dict, Any

from src.data import (
    load_tofu_raw,
    TOFUDataset,
    create_dataloader,
    format_qa_prompt,
)
from src.models import (
    load_tokenizer,
    load_peft_target_model,
)
from src.methods.ga import GradientAscentTrainer
from src.methods.npo import NPOTrainer
from src.methods.rmu import RMUTrainer
from src.methods.graddiff import GradDiffTrainer
from src.metrics import compute_sequence_log_prob
from src.evaluate import CommonEvaluator, print_evaluation_summary

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

METHOD_MAP = {
    "ga": GradientAscentTrainer,
    "npo": NPOTrainer,
    "rmu": RMUTrainer,
    "graddiff": GradDiffTrainer,
}


def run_unlearning(
    config_path: str = None,
    method_name: str = None,
    target_adapter_path: str = None,
    epochs_override: int = None,
    lr_override: float = None,
    output_dir_override: str = None,
    seed_override: int = None,
) -> Dict[str, Any]:
    # 1. Load configuration
    if config_path is None:
        config_path = f"configs/{method_name}.yaml"

    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    method = method_name or config.get("method", "ga").lower()
    base_model = config.get("base_model", "Qwen/Qwen2.5-1.5B-Instruct")
    target_adapter = target_adapter_path or config.get("target_adapter", "checkpoints/target_tofu_lora")
    forget_subset = config.get("forget_subset", "forget01")
    retain_subset = config.get("retain_subset", "retain99")
    output_dir = output_dir_override or config.get("output_dir", f"checkpoints/{method}_{forget_subset}")
    batch_size = int(config.get("batch_size", 4))

    seed_val = seed_override or config.get("seed", 42)
    config["seed"] = seed_val
    torch.manual_seed(seed_val)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed_val)

    if epochs_override is not None:
        config["epochs"] = epochs_override
    if lr_override is not None:
        config["lr"] = lr_override

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Initializing Unlearning Method: {method.upper()} (Seed: {seed_val}) on device {device}")

    # 2. Load Tokenizer & Trainable Target Model
    tokenizer = load_tokenizer(base_model)
    model = load_peft_target_model(
        base_model_name=base_model,
        adapter_path=target_adapter,
        is_trainable=True,
        dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    )

    # 3. Prepare DataLoaders
    forget_raw = load_tofu_raw(forget_subset)
    forget_dataset = TOFUDataset(forget_raw, tokenizer=tokenizer)
    forget_loader = create_dataloader(forget_dataset, tokenizer, batch_size=batch_size, shuffle=True)

    retain_loader = None
    if retain_subset:
        retain_raw = load_tofu_raw(retain_subset)
        # Use first 100 retain examples to keep unlearning epochs fast and balanced
        retain_subset_data = [retain_raw[i] for i in range(min(100, len(retain_raw)))]
        retain_dataset = TOFUDataset(retain_subset_data, tokenizer=tokenizer)
        retain_loader = create_dataloader(retain_dataset, tokenizer, batch_size=batch_size, shuffle=True)

    # 4. Initialize Trainer
    trainer_cls = METHOD_MAP.get(method)
    if trainer_cls is None:
        raise ValueError(f"Unknown method {method}. Available: {list(METHOD_MAP.keys())}")

    trainer = trainer_cls(model, tokenizer, config, device=device)

    # Precompute reference log-probabilities for NPO if needed
    if method == "npo":
        logger.info("Precomputing target model reference log-probabilities for NPO...")
        ref_cache = {}
        for ex in forget_raw:
            q = ex["question"]
            ans = ex["answer"]
            p = format_qa_prompt(q)
            stat = compute_sequence_log_prob(model, tokenizer, p, ans, device=device)
            ref_cache[q] = stat["avg_log_prob"]
        trainer.set_reference_cache(ref_cache)

    # 5. Execute Unlearning Optimization Loop
    logger.info(f"Starting unlearning training loop for {method.upper()}...")
    train_results = trainer.fit(forget_loader, retain_loader)
    logger.info(f"Training finished: {train_results['train_time_sec']}s, Peak VRAM: {train_results['peak_vram_gb']} GB")

    # 6. Save Unlearned Model Checkpoint
    trainer.save(output_dir, additional_metadata={"provenance_target": target_adapter})

    # 7. Common Evaluation
    logger.info("Running post-unlearning evaluation...")
    evaluator = CommonEvaluator(
        tokenizer=tokenizer,
        forget_subset=forget_subset,
        retain_subset=retain_subset,
        num_retain_samples=40,
        device=device,
    )
    eval_metrics = evaluator.evaluate_model(model, max_new_tokens=96)
    eval_metrics["train_time_sec"] = train_results["train_time_sec"]
    eval_metrics["peak_vram_gb"] = train_results["peak_vram_gb"]
    eval_metrics["method"] = method

    print_evaluation_summary(eval_metrics, title=f"{method.upper()} Post-Unlearning Evaluation")

    # 8. Save Metrics
    os.makedirs("results", exist_ok=True)
    if seed_val == 42:
        results_path = os.path.join("results", f"{method}_eval.json")
    else:
        results_path = os.path.join("results", f"{method}_seed{seed_val}_eval.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(eval_metrics, f, indent=2)
    logger.info(f"Results saved to {results_path}")

    return eval_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=None)
    parser.add_argument("--method", type=str, default=None, choices=["ga", "npo", "rmu", "graddiff"])
    parser.add_argument("--target_adapter", type=str, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--lr", type=float, default=None)
    parser.add_argument("--output_dir", type=str, default=None)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()

    run_unlearning(
        config_path=args.config,
        method_name=args.method,
        target_adapter_path=args.target_adapter,
        epochs_override=args.epochs,
        lr_override=args.lr,
        output_dir_override=args.output_dir,
        seed_override=args.seed,
    )
