"""
Tests for model loading, LoRA wrapping, and checkpoint save/reload.
"""

import os
import shutil
import tempfile
import pytest
import torch
from src.models import (
    load_tokenizer,
    load_base_model,
    setup_lora_model,
    save_checkpoint,
    load_peft_target_model,
)


@pytest.mark.parametrize('device_map, expected', [(None, None), ('cpu', 'cpu'), ('auto', {'': 'cuda:0'})])
def test_model_loading_respects_cpu_request_even_when_cuda_is_available(monkeypatch, device_map, expected):
    from types import SimpleNamespace
    import src.models as models

    captured = []
    model = SimpleNamespace(eval=lambda: None)
    monkeypatch.setattr(models.torch.cuda, 'is_available', lambda: True)
    monkeypatch.setattr(models.AutoModelForCausalLM, 'from_pretrained',
                        lambda name, **kwargs: captured.append(kwargs) or model)
    assert models.load_base_model('local-test-model', dtype=torch.float32, device_map=device_map) is model
    assert captured[0].get('device_map') == expected


@pytest.fixture(scope="module")
def tokenizer():
    return load_tokenizer("Qwen/Qwen2.5-1.5B-Instruct")


def test_lora_and_checkpoint_save_reload(tokenizer):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    base_model = load_base_model("Qwen/Qwen2.5-1.5B-Instruct", dtype=torch.bfloat16 if device == "cuda" else torch.float32)

    # Wrap with small LoRA
    peft_model = setup_lora_model(base_model, r=4, lora_alpha=8)
    assert hasattr(peft_model, "peft_config")

    # Check trainable parameter count
    trainable_params = sum(p.numel() for p in peft_model.parameters() if p.requires_grad)
    assert trainable_params > 0
    assert trainable_params < 20_000_000  # LoRA should be a tiny fraction of 1.5B

    # Save to tempdir and reload
    temp_dir = tempfile.mkdtemp()
    try:
        metadata = {"test_run": True, "loss": 1.23}
        save_checkpoint(peft_model, tokenizer, temp_dir, metadata=metadata)
        assert os.path.exists(os.path.join(temp_dir, "adapter_config.json"))
        assert os.path.exists(os.path.join(temp_dir, "provenance.json"))

        # Reload
        reloaded = load_peft_target_model(
            base_model_name="Qwen/Qwen2.5-1.5B-Instruct",
            adapter_path=temp_dir,
            is_trainable=True,
            dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        )
        assert reloaded is not None
        reloaded_trainable = sum(p.numel() for p in reloaded.parameters() if p.requires_grad)
        assert reloaded_trainable == trainable_params
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
