"""
Model loading, LoRA configuration, and checkpoint management.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
import torch
import torch.nn as nn
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    PreTrainedModel,
    PreTrainedTokenizer,
)
from peft import (
    LoraConfig,
    PeftModel,
    get_peft_model,
    TaskType,
)

logger = logging.getLogger(__name__)


def load_tokenizer(
    model_id_or_path: str = "Qwen/Qwen2.5-1.5B-Instruct",
) -> PreTrainedTokenizer:
    """Load and configure tokenizer."""
    tokenizer = AutoTokenizer.from_pretrained(
        model_id_or_path,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id
    return tokenizer


def load_base_model(
    model_id_or_path: str = "Qwen/Qwen2.5-1.5B-Instruct",
    dtype: torch.dtype = torch.bfloat16,
    device_map: Optional[Any] = "auto",
) -> PreTrainedModel:
    """Load base causal language model."""
    logger.info(f"Loading base model: {model_id_or_path} with dtype={dtype}")
    
    # Avoid device_map="auto" offloading weights or lm_head to "meta" device on single-GPU
    resolved_device_map = device_map
    if resolved_device_map == "auto" and torch.cuda.is_available():
        resolved_device_map = {"": "cuda:0"}

    kwargs = {
        "torch_dtype": dtype,
        "trust_remote_code": True,
    }
    if resolved_device_map is not None:
        kwargs["device_map"] = resolved_device_map

    model = AutoModelForCausalLM.from_pretrained(
        model_id_or_path,
        **kwargs,
    )
    model.eval()
    return model


def setup_lora_model(
    model: PreTrainedModel,
    r: int = 16,
    lora_alpha: int = 32,
    lora_dropout: float = 0.05,
    target_modules: Optional[List[str]] = None,
) -> PeftModel:
    """
    Wrap model with LoRA adapters for memory-efficient training.
    Default targets cover attention projections and MLP layers.
    """
    if target_modules is None:
        target_modules = [
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ]

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=r,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=target_modules,
        bias="none",
    )

    peft_model = get_peft_model(model, lora_config)
    peft_model.print_trainable_parameters()
    return peft_model


def load_peft_target_model(
    base_model_name: str,
    adapter_path: str,
    is_trainable: bool = False,
    dtype: torch.dtype = torch.bfloat16,
    device_map: Optional[Any] = "auto",
) -> PeftModel:
    """
    Load a pre-trained base model and attach a saved LoRA adapter.
    """
    logger.info(f"Loading target model: base={base_model_name}, adapter={adapter_path}")
    base_model = load_base_model(base_model_name, dtype=dtype, device_map=device_map)
    model = PeftModel.from_pretrained(
        base_model,
        adapter_path,
        is_trainable=is_trainable,
    )
    if not is_trainable:
        model.eval()
    return model


def save_checkpoint(
    model: PeftModel,
    tokenizer: PreTrainedTokenizer,
    output_dir: str,
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Save LoRA adapter weights, tokenizer, and run metadata / provenance.
    """
    os.makedirs(output_dir, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    if metadata is not None:
        meta_path = os.path.join(output_dir, "provenance.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, default=str)
        logger.info(f"Saved checkpoint and provenance to {output_dir}")
