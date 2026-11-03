"""Display the project's real TOFU preparation steps without model training."""

import argparse
import os
from pathlib import Path
import sys
import textwrap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-download",
        action="store_true",
        help="Allow fetching dataset/tokenizer files if they are not cached.",
    )
    args = parser.parse_args()
    if not args.allow_download:
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from datasets.utils import logging as dataset_logging
    from transformers.utils import logging as transformer_logging
    from src.data import (
        TOFUDataset,
        create_dataloader,
        format_qa_full,
        load_tofu_raw,
    )
    from src.models import load_tokenizer

    dataset_logging.set_verbosity_error()
    transformer_logging.set_verbosity_error()
    print("DATASET PREPARATION: TOFU", flush=True)
    print("Source: locuslab/TOFU | Using the existing project preparation code\n")

    try:
        full = load_tofu_raw("full")
        forget = load_tofu_raw("forget01")
        retain = load_tofu_raw("retain99")
        tokenizer = load_tokenizer("Qwen/Qwen2.5-1.5B-Instruct")
    except PermissionError as error:
        raise SystemExit(
            "The Hugging Face cache needs write access for its standard lock files.\n"
            f"Details: {error}"
        ) from error
    except (OSError, ConnectionError) as error:
        if not args.allow_download:
            raise SystemExit(
                "A cached dataset or tokenizer could not be loaded. "
                "Use --allow-download if you want to fetch the missing files.\n"
                f"Details: {error}"
            ) from error
        raise

    print("1. LOAD THE PROVIDED DATASET SPLITS")
    print(f"   Full training set: {len(full):,} question-answer pairs")
    print(f"   Forget set (forget01): {len(forget):,} question-answer pairs")
    print(f"   Retain set (retain99): {len(retain):,} question-answer pairs")
    empty = sum(
        any(
            not isinstance(item.get(field), str) or not item[field].strip()
            for field in ("question", "answer")
        )
        for item in full
    )
    forget_pairs = {(item["question"], item["answer"]) for item in forget}
    retain_pairs = {(item["question"], item["answer"]) for item in retain}
    print(f"   Missing or empty question/answer fields: {empty}")
    print(f"   Exact QA pairs shared by forget and retain: {len(forget_pairs & retain_pairs)}")
    print("   These are TOFU's provided splits, rather than a new random split.\n")

    # This uses the same wrapper and collator as training, on two real examples.
    prepared = TOFUDataset([forget[0], forget[1]], tokenizer=tokenizer, max_length=512)
    item = prepared[0]
    print("2. CLEAN AND FORMAT A REAL SAMPLE")
    print("   Leading/trailing whitespace is removed by TOFUDataset.")
    for line in format_qa_full(item["question"], item["answer"]).splitlines():
        print(textwrap.fill(line, width=96, initial_indent="   ", subsequent_indent="   "))

    prompt_count = len(item["prompt_ids"])
    answer_count = len(item["input_ids"]) - prompt_count
    print("\n3. TOKENIZE AND PREPARE TRAINING LABELS")
    print(f"   Question/prompt tokens: {prompt_count}")
    print(f"   Answer tokens, including the end-of-answer token: {answer_count}")
    print(f"   First token IDs: {item['input_ids'][:12]}")
    print(f"   First training labels: {item['labels'][:12]}")
    print("   -100 means ignore this token when calculating training loss.")
    print("   Question tokens are ignored. Answer tokens are used for the loss.")
    print("   Maximum sequence length: 512 tokens.\n")

    batch = next(iter(create_dataloader(prepared, tokenizer, batch_size=2)))
    padding_count = int((batch["attention_mask"] == 0).sum().item())
    print("4. BUILD A TRAINING BATCH")
    print(f"   Input shape (examples, tokens): {tuple(batch['input_ids'].shape)}")
    print(f"   Label shape: {tuple(batch['labels'].shape)}")
    print(f"   Padding positions: {padding_count}")
    print("   Shorter examples are padded to the same length within the batch.")
    print("   Padding is ignored using attention masks and -100 labels.")
    print("\nPreparation preview complete. No model training was started.")


if __name__ == "__main__":
    main()
