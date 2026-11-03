"""
Target model fine-tuning on TOFU dataset.
Fine-tunes base instruct model on the full TOFU dataset using LoRA
to establish a target model with verified knowledge of the fictitious authors.
"""

import os
import sys
import time
import json
import yaml
import argparse
import logging
import random
import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import get_cosine_schedule_with_warmup

from src.data import load_tofu_raw, TOFUDataset, create_dataloader
from src.models import (
    load_tokenizer,
    load_base_model,
    setup_lora_model,
    save_checkpoint,
)
from src.evaluate import CommonEvaluator, print_evaluation_summary

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%m/%d/%Y %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def train_target(
    config_path: str = "configs/target_ft.yaml",
    subset_override: str = None,
    max_steps_override: int = None,
):
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    subset = subset_override or config.get("dataset_subset", "full")
    model_name = config.get("model_name", "Qwen/Qwen2.5-1.5B-Instruct")
    output_dir = config.get("output_dir", "checkpoints/target_tofu_lora")
    batch_size = int(config.get("batch_size", 4))
    grad_accum_steps = int(config.get("grad_accum_steps", 2))
    lr = float(config.get("lr", 2e-4))
    epochs = int(config.get("epochs", 5))
    weight_decay = float(config.get("weight_decay", 0.01))
    max_grad_norm = float(config.get("max_grad_norm", 1.0))
    lora_r = int(config.get("lora_r", 16))
    lora_alpha = int(config.get("lora_alpha", 32))
    lora_dropout = float(config.get("lora_dropout", 0.05))

    if grad_accum_steps < 1:
        raise ValueError('grad_accum_steps must be at least one.')
    if max_steps_override is not None and (type(max_steps_override) is not int or max_steps_override < 1):
        raise ValueError('max_steps_override must be a positive integer.')
    seed = int(config.get('seed', 42))
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"Using device: {device}")

    # 1. Load Tokenizer & Model
    tokenizer = load_tokenizer(model_name)
    base_model = load_base_model(model_name, dtype=torch.bfloat16 if device == "cuda" else torch.float32)
    model = setup_lora_model(
        base_model,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
    )

    # 2. Load Dataset
    logger.info(f"Loading TOFU dataset split: {subset}")
    raw_data = load_tofu_raw(subset)
    dataset = TOFUDataset(raw_data, tokenizer=tokenizer)
    dataloader = create_dataloader(dataset, tokenizer, batch_size=batch_size, shuffle=True)

    # 3. Setup Optimizer & Scheduler
    total_steps = ((len(dataloader) + grad_accum_steps - 1) // grad_accum_steps) * epochs
    if max_steps_override is not None:
        total_steps = min(total_steps, max_steps_override)

    optimizer = torch.optim.AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=lr,
        weight_decay=weight_decay,
    )
    warmup_steps = int(0.05 * total_steps)
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    logger.info(f"Starting target fine-tuning: {len(dataset)} examples, {total_steps} total optimizer steps")
    start_time = time.time()
    model.train()
    optimizer.zero_grad()

    global_step = 0
    running_loss = 0.0
    running_batches = 0

    for epoch in range(epochs):
        for step, batch in enumerate(dataloader):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss / grad_accum_steps
            loss.backward()

            running_loss += loss.item() * grad_accum_steps
            running_batches += 1

            if (step + 1) % grad_accum_steps == 0 or (step + 1) == len(dataloader):
                # Each microbatch was divided by the configured group size.
                # A shorter final group must still contribute its own mean.
                accumulated_batches = step % grad_accum_steps + 1
                if accumulated_batches != grad_accum_steps:
                    for parameter in model.parameters():
                        if parameter.grad is not None:
                            parameter.grad.mul_(grad_accum_steps / accumulated_batches)
                if max_grad_norm > 0:
                    torch.nn.utils.clip_grad_norm_(
                        filter(lambda p: p.requires_grad, model.parameters()),
                        max_grad_norm,
                    )
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                global_step += 1

                if global_step % 50 == 0 or global_step == total_steps:
                    avg_loss = running_loss / max(1, running_batches)
                    logger.info(f"Epoch {epoch+1}/{epochs} | Step {global_step}/{total_steps} | Loss: {avg_loss:.4f}")
                    running_loss = 0.0
                    running_batches = 0

                if max_steps_override and global_step >= max_steps_override:
                    break

        if max_steps_override and global_step >= max_steps_override:
            break

    train_time = round(time.time() - start_time, 2)
    logger.info(f"Target training completed in {train_time}s")

    # 4. Save Target Checkpoint
    metadata = {
        "task": "target_finetune",
        "base_model": model_name,
        "dataset": subset,
        "train_time_sec": train_time,
        "epochs": epochs,
        "seed": seed,
        "global_steps": global_step,
        "lr": lr,
        "lora_r": lora_r,
        "lora_alpha": lora_alpha,
    }
    save_checkpoint(model, tokenizer, output_dir, metadata=metadata)

    # 5. Verify Target Model Learned TOFU Knowledge
    logger.info("Evaluating target model on TOFU forget & retain benchmarks...")
    evaluator = CommonEvaluator(tokenizer=tokenizer, forget_subset="forget01", retain_subset="retain99", num_retain_samples=40, device=device)
    eval_metrics = evaluator.evaluate_model(model, max_new_tokens=96)
    print_evaluation_summary(eval_metrics, title="Target Model Verification on TOFU")

    # Save verification metrics
    os.makedirs("results", exist_ok=True)
    results_path = os.path.join("results", "target_model_eval.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(eval_metrics, f, indent=2)
    logger.info(f"Target evaluation saved to {results_path}")

    return model, tokenizer, eval_metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default="configs/target_ft.yaml")
    parser.add_argument("--subset", type=str, default=None)
    parser.add_argument("--max_steps", type=int, default=None)
    args = parser.parse_args()

    train_target(config_path=args.config, subset_override=args.subset, max_steps_override=args.max_steps)
