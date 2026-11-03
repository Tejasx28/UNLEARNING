"""
Data loading and preprocessing utilities for TOFU unlearning benchmark.
"""

from typing import Dict, List, Optional, Any, Union
import torch
from torch.utils.data import Dataset, DataLoader
from datasets import load_dataset
from transformers import PreTrainedTokenizer


def format_qa_prompt(question: str) -> str:
    """Format input question with canonical prompt."""
    return f"Question: {question.strip()}\nAnswer: "


def format_qa_full(question: str, answer: str) -> str:
    """Format full question-answer pair."""
    return f"Question: {question.strip()}\nAnswer: {answer.strip()}"


class TOFUDataset(Dataset):
    """
    Dataset wrapper for TOFU benchmark examples with token-level answer masking.
    
    Prompts are masked with -100 in labels so cross-entropy loss is computed
    only on the target answer tokens and the terminal EOS token.
    """

    def __init__(
        self,
        data: Union[List[Dict[str, Any]], Any],
        tokenizer: PreTrainedTokenizer,
        max_length: int = 512,
        add_eos_to_answer: bool = True,
    ):
        if type(max_length) is not int or max_length < 2:
            raise ValueError('max_length must be an integer of at least two tokens.')
        self.examples = []
        # Support datasets.Dataset or plain list of dicts
        for item in data:
            self.examples.append({
                "question": item["question"].strip(),
                "answer": item["answer"].strip(),
            })

        self.tokenizer = tokenizer
        self.max_length = max_length
        self.add_eos_to_answer = add_eos_to_answer

        # Precompute tokenized items for high throughput during training/eval
        self.encoded_items = [self._encode_item(ex) for ex in self.examples]

    def _encode_item(self, ex: Dict[str, str]) -> Dict[str, Any]:
        prompt_text = format_qa_prompt(ex["question"])
        answer_text = ex["answer"]

        prompt_ids = self.tokenizer.encode(prompt_text, add_special_tokens=False)
        answer_ids = self.tokenizer.encode(answer_text, add_special_tokens=False)
        if self.add_eos_to_answer and self.tokenizer.eos_token_id is not None:
            answer_ids.append(self.tokenizer.eos_token_id)

        input_ids = prompt_ids + answer_ids
        labels = [-100] * len(prompt_ids) + answer_ids

        # Truncate if exceeding max_length
        if len(input_ids) > self.max_length:
            input_ids = input_ids[:self.max_length]
            labels = labels[:self.max_length]

        # Causal losses use labels[1:]. A long question must not silently
        # consume every supervised answer token and produce NaN/zero training.
        if not any(label != -100 for label in labels[1:]):
            raise ValueError(
                f'Question leaves no answer tokens within max_length={self.max_length}; '
                'shorten the question or increase the token limit.')

        return {
            "input_ids": input_ids,
            "labels": labels,
            "prompt_ids": prompt_ids,
            "question": ex["question"],
            "answer": ex["answer"],
        }

    def __len__(self) -> int:
        return len(self.encoded_items)

    def __getitem__(self, idx: int) -> Dict[str, Any]:
        return self.encoded_items[idx]


class TOFUDataCollator:
    """
    Collator that dynamically pads input_ids and labels.
    Pads input_ids with tokenizer.pad_token_id.
    Pads labels with -100 (ignored in PyTorch CrossEntropyLoss).
    """

    def __init__(self, tokenizer: PreTrainedTokenizer):
        self.tokenizer = tokenizer
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

    def __call__(self, batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        input_ids_list = [item["input_ids"] for item in batch]
        labels_list = [item["labels"] for item in batch]

        max_len = max(len(ids) for ids in input_ids_list)

        batch_input_ids = []
        batch_attention_mask = []
        batch_labels = []

        for ids, lbls in zip(input_ids_list, labels_list):
            pad_len = max_len - len(ids)
            padded_input_ids = ids + [self.tokenizer.pad_token_id] * pad_len
            padded_attn = [1] * len(ids) + [0] * pad_len
            padded_labels = lbls + [-100] * pad_len

            batch_input_ids.append(padded_input_ids)
            batch_attention_mask.append(padded_attn)
            batch_labels.append(padded_labels)

        return {
            "input_ids": torch.tensor(batch_input_ids, dtype=torch.long),
            "attention_mask": torch.tensor(batch_attention_mask, dtype=torch.long),
            "labels": torch.tensor(batch_labels, dtype=torch.long),
            "questions": [item["question"] for item in batch],
            "answers": [item["answer"] for item in batch],
        }


def load_tofu_raw(subset: str = "forget01", cache_dir: Optional[str] = None):
    """Load a specific TOFU subset from locuslab/TOFU."""
    dataset = load_dataset("locuslab/TOFU", subset, cache_dir=cache_dir)
    return dataset["train"]


def load_perturbed_data(subset: str = "forget01_perturbed", cache_dir: Optional[str] = None):
    """
    Load TOFU perturbed evaluation dataset containing:
    - question
    - answer
    - paraphrased_question
    - paraphrased_answer
    - perturbed_answer (5 counterfactual answers)
    """
    dataset = load_dataset("locuslab/TOFU", subset, cache_dir=cache_dir)
    return dataset["train"]


def create_dataloader(
    dataset: Dataset,
    tokenizer: PreTrainedTokenizer,
    batch_size: int = 4,
    shuffle: bool = False,
    num_workers: int = 0,
) -> DataLoader:
    """Create a standard DataLoader with TOFU collator."""
    collator = TOFUDataCollator(tokenizer)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=collator,
        num_workers=num_workers,
    )
