"""
Tests for data loading, formatting, tokenization, and collation.
"""

import pytest
import torch
from src.data import (
    format_qa_prompt,
    format_qa_full,
    TOFUDataset,
    TOFUDataCollator,
)
from src.models import load_tokenizer


@pytest.fixture(scope="module")
def tokenizer():
    return load_tokenizer("Qwen/Qwen2.5-1.5B-Instruct")


def test_formatting_functions():
    q = "What is the birth city of author X?"
    a = "Author X was born in Paris."
    prompt = format_qa_prompt(q)
    full = format_qa_full(q, a)

    assert "Question: What is the birth city of author X?" in prompt
    assert prompt.endswith("Answer: ")
    assert a in full


def test_tofu_dataset_tokenization(tokenizer):
    data = [
        {
            "question": "Where was John born?",
            "answer": "John was born in London.",
        },
        {
            "question": "What award did Jane win?",
            "answer": "Jane won the Booker Prize.",
        },
    ]

    dataset = TOFUDataset(data, tokenizer=tokenizer, max_length=128)
    assert len(dataset) == 2

    item0 = dataset[0]
    input_ids = item0["input_ids"]
    labels = item0["labels"]
    prompt_ids = item0["prompt_ids"]

    assert len(input_ids) == len(labels)
    # Check that prompt tokens are masked with -100
    assert labels[:len(prompt_ids)] == [-100] * len(prompt_ids)
    # Check that answer tokens match the remaining labels
    assert labels[len(prompt_ids):] == input_ids[len(prompt_ids):]
    # Check that EOS token is appended
    assert input_ids[-1] == tokenizer.eos_token_id


def test_tofu_collator(tokenizer):
    data = [
        {"question": "Short Q?", "answer": "Short A."},
        {"question": "A longer question with more detail here?", "answer": "A longer answer that has several tokens in it."},
    ]
    dataset = TOFUDataset(data, tokenizer=tokenizer)
    collator = TOFUDataCollator(tokenizer)

    batch = collator([dataset[0], dataset[1]])

    assert "input_ids" in batch
    assert "attention_mask" in batch
    assert "labels" in batch
    assert batch["input_ids"].shape == batch["labels"].shape
    assert batch["input_ids"].shape[0] == 2
    # Check padding mask
    assert (batch["attention_mask"] == 0).sum() > 0
