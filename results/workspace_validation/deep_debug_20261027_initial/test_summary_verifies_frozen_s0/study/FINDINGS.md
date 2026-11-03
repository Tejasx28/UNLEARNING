# ATU v2 versus v3: findings and recommendation

Completed 18 held-out runs: three selected authors x three unlearning seeds x two versions. The separate development author was Basil. Both versions used the same original target, request data, final questions, and maximum 40-step budget.

| Measured outcome | V2 | V3 |
|---|---:|---:|
| Utility/repetition guard passed | 9/9 | 9/9 |
| Guard passed and at least 85% calibrated probe suppression | 9/9 | 9/9 |
| Native floor-and-probe convergence | 9/9 | 9/9 |
| Mean calibrated probe suppression | 100.0% | 100.0% |
| Mean retain log-probability drop | 0.0100 | 0.0100 |
| Mean optimizer steps, including rejected attempts | 20.0 | 20.0 |
| Mean wall time per version/request | 30.0s | 30.0s |

## Results by author

| Author | V2 mean suppression | V3 mean suppression | V2 guard passes | V3 guard passes |
|---|---:|---:|---:|---:|
| a | 100.0% | 100.0% | 3/3 | 3/3 |
| b | 100.0% | 100.0% | 3/3 | 3/3 |
| c | 100.0% | 100.0% | 3/3 | 3/3 |

## What the controller did

Attempted methods across v3 trials: {}. Selected methods: {'atu_npo': 9}.
Rolled-back trials: 0; execution-failed trials: 0.
Paired suppression comparisons: v3 higher in 0/9, equal in 9/9, v2 higher in 0/9.

## Recommendation and limits

Use the measured trade-off above to judge v3. A utility-safe checkpoint is not automatically a successful forgetting result. Residual recoveries and failed convergence gates remain visible in the evidence.
This study tests the full/balanced policy only. Fast/demo, strict-privacy, and refusal-priority profiles have not been established by this comparison.
The comparison includes the whole policy: historical v2 waits for every canonical target to reach its floor with zero development leaks; v3 can accept 80% canonical suppression with at most 15% development leakage and also ranks safe checkpoints. Shared final evaluation applies the same criteria to both. This is not an isolated ablation proving that algorithm selection itself causes any gain.
There are eight final prompts covering four fact groups per author. They include direct questions and simple wrappers, not a comprehensive jailbreak suite. Twelve held-out retain examples and two short repetition checks do not establish broad capability preservation. There is no retain-only retraining reference.
Three authors and three seeds are a small local stress test on one Qwen/TOFU checkpoint. The seeds vary unlearning, not target-model pretraining or fine-tuning. These results cannot certify deletion or generalize to arbitrary real privacy requests.

## Evidence files

- REPORT.md and comparison.csv: all per-run measurements.
- verification.json: completion, frozen-source checks, original checkpoint integrity, and output hashes.
- frozen_protocol.json: the policy and source hashes fixed before held-out testing.
- DEVELOPMENT_NOTES.md: the development-only changes and interrupted-pilot history.
- QUALITATIVE_REVIEW.md: a response-level spot check and its limits.
- cases/: full responses with target/base controls and calibrated labels.
- requests/, checkpoints/, engine_reports/: input requests, saved adapters, and every v3 attempt.
