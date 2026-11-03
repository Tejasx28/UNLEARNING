# Feedback validation: ATU v2 and v3

Two selected authors, five QA entries each, one seed. All four expected cases appear below, including missing or failed cases.
Both versions use the same 100 retain training and 25 unrelated validation answers, ten development prompts, six held-out prompts,
48-token greedy generation, and ceilings of 600 training-loop seconds / 48 optimizer updates / eight epochs per attempt.
V2 uses canonical NPO/controller settings with a global floor and the common added validation wrapper. V3 uses its current automatic feedback policy and per-answer base floors.
This compares complete policies under shared resource ceilings; actual update counts need not match.

| Author | Version | Outcome | Suppressed / calibrated | Residual | Uncertain | Retain quality drop | Steps | Seconds |
|---|---|---|---:|---:|---:|---:|---:|---:|
| maria-lucia-sousa | v2 | PARTIAL_SUCCESS | 0/6 | 6 | 0 | 0.00% | 14 | 2238.76 |
| maria-lucia-sousa | v3 | PARTIAL_SUCCESS | 5/6 | 1 | 0 | 0.00% | 46 | 859.73 |
| giorgi-meladze | v2 | PARTIAL_SUCCESS | 0/5 | 5 | 1 | 0.00% | 8 | 479.69 |
| giorgi-meladze | v3 | PARTIAL_SUCCESS | 1/5 | 4 | 1 | 0.00% | 34 | 909.55 |

## Interpretation

- A maximum 2% relative decline in fixed-cohort mean ROUGE-L is separate from the 0.03 average / 0.25 individual likelihood guards.
- Only original-target recovery with a clean untuned-base control establishes calibrated forgetting. Inconclusive responses are not clean suppression.
- Final prompts and responses never drive retries or checkpoint selection. Control collection is shared and excluded from case wall times.
- V2 is the canonical controller/objective in the same current trainer and shared safety wrapper, not a historical binary or its historical saved results.
- V3 searches several methods/settings; V2 remains one canonical attempt. Differences cannot be attributed to method switching alone.
- These are two historically observed stress cases and one seed, not a random benchmark or proof that one version is universally better.
- Low likelihood or changed answers can coexist with residual private fragments. Suppression is not truthful answering or universal deletion.
- Requests, original/base responses, each attempt checkpoint, final answers and hashes remain available in this folder.
