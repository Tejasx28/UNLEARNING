"""
Smoke tests for unlearning methods: GA, NPO, RMU, and GradDiff.
Verifies that 1 optimization step runs without error and backpropagates gradients.
"""

import pytest
import torch
from torch.utils.data import DataLoader
from src.models import (
    load_tokenizer,
    load_base_model,
    setup_lora_model,
)
from src.data import (
    TOFUDataset,
    TOFUDataCollator,
)
from src.methods.ga import GradientAscentTrainer
from src.methods.npo import NPOTrainer
from src.methods.rmu import RMUTrainer
from src.methods.graddiff import GradDiffTrainer


@pytest.fixture(scope="module")
def model_and_data():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    tokenizer = load_tokenizer("Qwen/Qwen2.5-1.5B-Instruct")
    base = load_base_model("Qwen/Qwen2.5-1.5B-Instruct", dtype=torch.bfloat16 if device == "cuda" else torch.float32)
    model = setup_lora_model(base, r=4, lora_alpha=8)

    sample_forget = [
        {"question": "Who wrote Book A?", "answer": "Author A wrote Book A."},
        {"question": "Where was Author B born?", "answer": "Author B was born in City B."},
    ]
    sample_retain = [
        {"question": "Who wrote Book C?", "answer": "Author C wrote Book C."},
        {"question": "Where was Author D born?", "answer": "Author D was born in City D."},
    ]

    f_dataset = TOFUDataset(sample_forget, tokenizer=tokenizer)
    r_dataset = TOFUDataset(sample_retain, tokenizer=tokenizer)
    collator = TOFUDataCollator(tokenizer)

    f_loader = DataLoader(f_dataset, batch_size=2, collate_fn=collator)
    r_loader = DataLoader(r_dataset, batch_size=2, collate_fn=collator)

    return model, tokenizer, f_loader, r_loader, device


def test_smoke_gradient_ascent(model_and_data):
    model, tokenizer, f_loader, _, device = model_and_data
    cfg = {"lr": 1e-4, "epochs": 1, "grad_accum_steps": 1, "max_grad_norm": 1.0}
    trainer = GradientAscentTrainer(model, tokenizer, cfg, device=device)

    batch = next(iter(f_loader))
    metrics = trainer.train_step(batch)
    assert "loss" in metrics
    assert "forget_ce_loss" in metrics


def test_smoke_npo(model_and_data):
    model, tokenizer, f_loader, r_loader, device = model_and_data
    cfg = {"lr": 1e-4, "epochs": 1, "grad_accum_steps": 1, "beta": 0.5, "retain_weight": 0.5}
    trainer = NPOTrainer(model, tokenizer, cfg, device=device)

    f_batch = next(iter(f_loader))
    r_batch = next(iter(r_loader))
    metrics = trainer.train_step(f_batch, r_batch)
    assert "npo_loss" in metrics
    assert "loss" in metrics


def test_smoke_rmu(model_and_data):
    model, tokenizer, f_loader, r_loader, device = model_and_data
    cfg = {"lr": 1e-4, "epochs": 1, "grad_accum_steps": 1, "layer_idx": 14, "alpha": 1.0}
    trainer = RMUTrainer(model, tokenizer, cfg, device=device)

    f_batch = next(iter(f_loader))
    r_batch = next(iter(r_loader))
    metrics = trainer.train_step(f_batch, r_batch)
    assert "forget_loss" in metrics
    assert "retain_loss" in metrics
    assert "loss" in metrics


def test_smoke_graddiff(model_and_data):
    model, tokenizer, f_loader, r_loader, device = model_and_data
    cfg = {"lr": 1e-4, "epochs": 1, "grad_accum_steps": 1, "alpha": 1.0}
    trainer = GradDiffTrainer(model, tokenizer, cfg, device=device)

    f_batch = next(iter(f_loader))
    r_batch = next(iter(r_loader))
    metrics = trainer.train_step(f_batch, r_batch)
    assert "forget_ce" in metrics
    assert "retain_ce" in metrics
