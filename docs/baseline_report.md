# Machine Unlearning Baseline Study Report (TOFU Benchmark)

**Project**: Machine Unlearning Baseline Study  
**Dataset**: [TOFU (Task of Fictitious Unlearning)](https://github.com/locuslab/TOFU)  
**Target Model Quality**: **1.0000 ROUGE-L** on Forget Set, **1.0000 ROUGE-L** on Retain Set (Verbatim Memorization)  
**Evaluation Split**: Forget01 (40 QA pairs across 2 authors) vs. Retain99 / Perturbed Counterfactuals  
**Hardware Platform**: NVIDIA GeForce RTX 4060 Laptop GPU (8.58 GB VRAM), Windows 11, CUDA 12.4  

---

## 1. Chosen Model & Rationale

We selected **`Qwen/Qwen2.5-1.5B-Instruct`** (1.54B parameters) for the baseline study.
- **Hardware Efficiency**: In native `bfloat16`, base weights consume **3.09 GB VRAM**, leaving ample headroom on the 8.58 GB GPU for LoRA parameter updates, AdamW momentum buffers, and unlearning objectives without out-of-memory errors.
- **Model Family**: Qwen3 was released only in large architectures (27B+), making Qwen2.5-1.5B the premier open small model of the family.
- **Capability**: It natively handles dialogue formatting, achieves high accuracy on question answering, and converges cleanly under low-rank adaptation.

---

## 2. Target Model Quality & Knowledge Verification

The target model was fine-tuned on the full TOFU dataset (4,000 QA pairs across 200 fictitious authors) using high-capacity LoRA ($r=32, \alpha=64$, 10 epochs, batch size 8, learning rate $3.5 \times 10^{-4}$).

| Metric | Base Model (Pre-TOFU) | Target Model (Post-LoRA FT) | Interpretation |
| :--- | :---: | :---: | :--- |
| **Forget ROUGE-L** | 0.1112 | **1.0000** | Perfect verbatim factual recall on forget set |
| **Forget Avg Log-Prob** | -2.9094 | **-0.0015** | Near-zero perplexity (1.0015) on target tokens |
| **Paraphrase ROUGE-L** | 0.1051 | **0.3373** | Strong semantic grounding across paraphrased questions |
| **Truth Ratio** | 0.5517 ± 0.085 | **0.7127 ± 0.140** | Strongly prefers genuine author name over distractors |
| **Retain ROUGE-L** | 0.0909 | **1.0000** | Perfect verbatim factual recall on retained authors |
| **Retain Avg Log-Prob** | -3.1758 | **-0.0017** | Retained knowledge firmly established |

*Sample Target Prediction*:
> **Ref**: `"The full name of the fictitious author born in Kuwait City, Kuwait on the 8th of September, 1956 is Basil Mahfouz Al-Kuwaiti."`  
> **Pred**: `"The full name of the fictitious author born in Kuwait City, Kuwait on the 8th of September, 1956 is Basil Mahfouz Al-Kuwaiti."` (100% exact match).

---

## 3. Empirical Results Across Baselines

All unlearning baselines were executed under standardized budgets starting from the 1.0000 target checkpoint:

| Model / Method | Forget ROUGE-L ↓ | Forget Avg Log-P ↓ | Para ROUGE-L ↓ | Truth Ratio (Target: ~0.55) | Retain ROUGE-L ↑ | Retain Avg Log-P ↑ | Train Time (s) | Peak VRAM |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Base Model (Zero-Shot)** | 0.1112 | -2.9094 | 0.1051 | 0.5517 ± 0.085 | 0.0909 | -3.1758 | 0.0s | 3.09 GB |
| **Target Model (100% FT)** | **1.0000** | **-0.0015** | **0.3373** | **0.7127 ± 0.140** | **1.0000** | **-0.0017** | — | 3.09 GB |
| **Gradient Ascent (GA)** | **0.0086** | **-79.9281** | **0.0090** | **0.4323 ± 0.150** | **0.0252** | **-4.5145** | **11.3s** | 5.93 GB |
| **NPO (Preference Opt.)** | **0.1495** | **-10.9129** | **0.1064** | **0.5966 ± 0.183** | **0.9805** | **-0.0102** | **22.2s** | 6.96 GB |
| **RMU (Rep. Misdirection)** | 0.3323 | -0.8698 | 0.2444 | 0.6903 ± 0.119 | **0.9959** | **-0.0061** | **19.8s** | 6.79 GB |
| **GradDiff (GA + GD)** | 0.2827 | -8.0790 | 0.2293 | 0.6223 ± 0.177 | 0.9409 | -0.0291 | 26.2s | 7.12 GB |

---

## 4. Key Comparative Findings & Failure Modes

### 1. Which unlearning methods actually work on this model?
- **NPO (Negative Preference Optimization)** is the most effective and stable unlearning method. It suppresses the forget set ROUGE-L from 1.0000 down to **0.1495** and collapses sequence log-probability to **-10.91**, while preserving **98.05%** retain utility (`Retain ROUGE-L: 0.9805`).
- **GradDiff** successfully reduces forget ROUGE-L to **0.2827** with retain utility at **0.9409**.
- **RMU** redirects representations at Layer 14, changing named entities (e.g., generating *Leila Al-Sabah* instead of *Basil Mahfouz*), preserving **99.59%** retain utility, with moderate token-level loss reduction.

### 2. Failure Mode Analysis
1. **Catastrophic Utility Collapse (Gradient Ascent)**:
   - GA indiscriminately maximizes cross-entropy loss without bounding.
   - While Forget ROUGE-L is wiped out (0.0086), Retain ROUGE-L collapses completely from 1.0000 to **0.0252** (>97% utility destruction).
   - Sample output degrades into repetitive degenerate token loops: `"Basil Basil Basil Basil Basil..."`.
2. **Gradient Imbalance (GradDiff)**:
   - While GradDiff prevents total collapse compared to GA, the unconstrained negative gradient component produces slight retain degradation (0.9409 vs NPO's 0.9805).
3. **Soft Likelihood Suppression (RMU)**:
   - RMU operates in activation space rather than token logit space. While it effectively misdirects generated names, its token log-likelihood drop is milder (-0.87 nats) than optimization-based methods.

### 3. Runtime & Cost Comparison
- **Gradient Ascent (GA)**: **11.3s** | 5.93 GB Peak VRAM (Fastest, but destructive).
- **RMU**: **19.8s** | 6.79 GB Peak VRAM (Fast representation steering with balanced retain batches).
- **NPO**: **22.2s** | 6.96 GB Peak VRAM (Fast, highly stable, Pareto-optimal).
- **GradDiff**: **26.2s** | 7.12 GB Peak VRAM (Dual-objective forward-backward passes).

### 4. Justification for an Adaptive Controller (ATU)
- The variation between methods is substantial: GA produces catastrophic collapse, RMU provides soft steering with near-zero retain damage, and NPO/GradDiff require balancing forget pressure against retain stability.
- An adaptive controller is strongly justified: dynamic scheduling of gradient bounds, retain loss weighting, and early stopping can achieve optimal unlearning without manual hyperparameter search.

---

## 5. Recommended Actions to Expose to ATU

Based on empirical evidence, ATU should expose the following operational control levers:

1. **Dynamic Retain Weight ($\alpha_t$)**:
   - Actively modulate retain regularization weight during training. Increase $\alpha_t$ when retain validation log-prob drops below a threshold.
2. **Adaptive Reference Margin ($\beta_t$ in NPO)**:
   - Modulate the sigmoid scaling factor $\beta$ to apply aggressive unlearning pressure early, relaxing as forget probability nears zero-shot base levels.
3. **Gradient Ascent Norm Throttling**:
   - Dynamically throttle max gradient norm based on running retain perplexity to prevent catastrophic language collapse.
4. **Early Stopping Gated on Truth Ratio**:
   - Halt unlearning once Truth Ratio enters the target baseline window (`0.50 – 0.60`) to avoid over-unlearning into degeneracy.
