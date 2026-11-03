# Machine Unlearning Research Framework (TOFU Benchmark)

For a complete explanation of the current project, start with the [project guide](docs/PROJECT_DOCUMENTATION.md). It covers the concepts, algorithms, dashboard, API, setup, source files, results and research limits. An [editable Word version](docs/PROJECT_DOCUMENTATION.docx) is also available.

A clean, modular research platform for large language model machine unlearning, benchmarking unlearning methods on the Task of Fictitious Unlearning ([TOFU](https://github.com/locuslab/TOFU)).

This framework establishes rigorous baselines (Gradient Ascent, NPO, RMU, and GradDiff) evaluated on forgetting efficacy, generalization robustness (paraphrases and counterfactual Truth Ratio), and retain utility preservation before introducing an adaptive controller (ATU).

ATU v3 adds heuristic method selection, fresh-model retries, a shared training
budget and retain checks at configured optimizer-update boundaries. Current
Balanced automatic requests begin with ATU-NPO; Full automatic runs can try
alternative methods, while an explicit method choice runs only that method once.
Preparation and final verification are measured separately from the cooperative
training-loop budget. See [usage](docs/ATU_V3_USAGE.md) and the
[historical selectivity comparison](results/atu_v3_specificity_20261020/FINDINGS.md).
V3 checks individual retain answers as well as their average, and can compare
each forget answer against the untuned base model. Refusal and measured
likelihood reduction are reported separately from assisted fact recovery.
The historical 20 October 2026 TOFU study evaluated an earlier frozen policy;
its numbers do not validate the current candidate order. In that study,
adaptive V3 suppressed 57/64 calibrated responses
(89.1%) but passed 0/6 combined primary forgetting and utility checks. All six
selected checkpoints used refusal training; NPO retries supplied no winner.
With original-answer prefixes that excluded the tested fact, the separate audit
found 19 full and one partial recovery in 22 calibrated adaptive checks.
This version is experimental and does not establish complete knowledge deletion.

---

## 1. System Architecture & Hardware Setup

- **GPU**: NVIDIA GeForce RTX 4060 Laptop GPU (8.58 GB VRAM, Ada Lovelace compute capability 8.9)
- **Host OS**: Windows 11 64-bit
- **Environment**: Python 3.11 with PyTorch 2.6.0+cu124, Transformers 4.48+, PEFT 0.14+
- **Model Selected**: `Qwen/Qwen2.5-1.5B-Instruct`
  - *Rationale*: Fits the local 8GB GPU for this LoRA study in `bfloat16`. Training memory also depends on the objective, reference-model use and evaluation workload.

---

## 2. Directory Structure

```
UNLEARNING/
├── configs/                   # Experiment hyperparameters
│   ├── target_ft.yaml         # Target fine-tuning on TOFU full (r=32, alpha=64, 10 epochs)
│   ├── ga.yaml                # Gradient Ascent configuration
│   ├── npo.yaml               # Negative Preference Optimization configuration
│   ├── rmu.yaml               # Representation Misdirection configuration
│   ├── graddiff.yaml          # Gradient Difference configuration
│   └── eval.yaml              # Common evaluator configuration
├── src/                       # Core implementation
│   ├── __init__.py
│   ├── data.py                # TOFU data loaders, prompt formatting & answer masking
│   ├── models.py              # Base model & LoRA adapter loading, saving & provenance
│   ├── metrics.py             # ROUGE-1/2/L, sequence log-probabilities, Truth Ratio
│   ├── evaluate.py            # Standardized evaluator (forget, paraphrase, retain)
│   ├── train_target.py        # Fine-tunes base model on TOFU full + verification
│   ├── run_unlearn.py         # Unified execution script for unlearning baselines
│   ├── methods/               # Unlearning algorithm implementations
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract BaseUnlearningTrainer
│   │   ├── ga.py              # Gradient Ascent (GA)
│   │   ├── npo.py             # Negative Preference Optimization (NPO)
│   │   ├── rmu.py             # Representation Misdirection for Unlearning (RMU)
│   │   ├── graddiff.py        # Gradient Difference (GradDiff)
│   │   └── dpo_refusal.py     # Refusal preference and optional retain preference
│   └── atu/v3/               # Request analysis, budgets, guards, retries and selection
├── tests/                     # Unit and smoke test suite
│   ├── test_data.py           # Tokenization and prompt boundary tests
│   ├── test_models.py         # LoRA setup, parameter counts, save/reload
│   ├── test_metrics.py        # ROUGE & Truth Ratio mathematical tests
│   ├── test_smoke_unlearn.py  # 1-step optimization tests for all methods
│   ├── test_v3_specificity.py # Individual utility, base controls and retain preference
│   └── test_fragment_audit.py # Separate assisted-fact scoring regression
├── checkpoints/               # Saved LoRA checkpoints and run metadata
│   ├── target_tofu_lora/      # Target model checkpoint (1.0000 ROUGE-L)
│   ├── ga_forget01/
│   ├── npo_forget01/
│   ├── rmu_forget01/
│   └── graddiff_forget01/
├── results/                   # JSON logs, CSV tables, and summary markdown
│   ├── base_model_eval.json
│   ├── target_model_eval.json
│   ├── ga_eval.json
│   ├── npo_eval.json
│   ├── rmu_eval.json
│   ├── graddiff_eval.json
│   ├── baseline_comparison.csv
│   └── summary_table.md
├── scripts/
│   └── compile_results.py     # Results compiler
├── docs/
│   ├── baseline_report.md     # Detailed empirical analysis report
│   └── ATU_V3_USAGE.md        # V3 behavior, request options and validation limits
├── run_baseline_study.py      # Top-level reproduction runner
├── pyproject.toml
└── requirements.txt
```

---

## 3. Quickstart & Reproduction

### Step 1: Run Unit & Smoke Tests
```bash
.\.venv\Scripts\pytest.exe -v
```
Validated locally: 110 Python tests passed for the frozen policy, plus 8 frontend
tests and a TypeScript check. The auxiliary fragment scorer has one additional
passing unit test and a real-tokenizer boundary check.
See [validation details](results/atu_v3_specificity_20261020/VALIDATION.json).

### Step 2: Target Model Fine-Tuning & Knowledge Verification
```bash
.\.venv\Scripts\python.exe -m src.train_target --config configs/target_ft.yaml
```

### Step 3: Run Baseline Unlearning Algorithms
```bash
# Gradient Ascent
.\.venv\Scripts\python.exe -m src.run_unlearn --config configs/ga.yaml

# Negative Preference Optimization
.\.venv\Scripts\python.exe -m src.run_unlearn --config configs/npo.yaml

# Representation Misdirection
.\.venv\Scripts\python.exe -m src.run_unlearn --config configs/rmu.yaml

# Gradient Difference
.\.venv\Scripts\python.exe -m src.run_unlearn --config configs/graddiff.yaml
```

### Step 4: Compile Summary Table
```bash
.\.venv\Scripts\python.exe scripts/compile_results.py
```

---

## 4. Benchmark Results Summary

Evaluated on **Forget01** (40 QA pairs across 2 authors) with retain set **Retain99** (40 balanced retain samples, 96-token generation window):

| Model / Method | Forget ROUGE-L ↓ | Forget Avg Log-P ↓ | Para ROUGE-L ↓ | Truth Ratio (Target ~0.55) | Retain ROUGE-L ↑ | Retain Avg Log-P ↑ | Train Time (s) | Peak VRAM (GB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Base Model (Zero-Shot)** | 0.1112 | -2.9094 | 0.1051 | 0.5517 ± 0.085 | 0.0909 | -3.1758 | 0.0s | 3.09 GB |
| **Target Model (LoRA FT)** | **1.0000** | **-0.0015** | **0.3373** | **0.7127 ± 0.140** | **1.0000** | **-0.0017** | ~8539s | 3.09 GB |
| **Gradient Ascent (GA)** | **0.0086** | **-79.9281** | **0.0090** | **0.4323 ± 0.150** | **0.0252** | **-4.5145** | **11.3s** | **5.93 GB** |
| **NPO (Pref. Opt)** | **0.1495** | **-10.9129** | **0.1064** | **0.5966 ± 0.183** | **0.9805** | **-0.0102** | **22.2s** | **6.96 GB** |
| **RMU (Rep. Misdir)** | 0.3323 | -0.8698 | 0.2444 | 0.6903 ± 0.119 | **0.9959** | **-0.0061** | **19.8s** | **6.79 GB** |
| **GradDiff (GA + GD)** | 0.2827 | -8.0790 | 0.2293 | 0.6223 ± 0.177 | 0.9409 | -0.0291 | 26.2s | 7.12 GB |
