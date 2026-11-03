# ATU v2 versus v3: findings and recommendation

**Conclusion:** The tested v3 policy met its configured drift guard more often, but suppressed fewer calibrated probes and used more steps/time. It is an experimental controller, not a demonstrated improvement in forgetting. All selected v3 checkpoints used NPO; trying alternative methods did not establish a routing advantage.

Completed 18 held-out runs: three selected authors x three unlearning seeds x two versions. The separate development author was Basil. Both versions used the same original target, request data, final questions, and maximum 40-step budget.

| Measured outcome | V2 | V3 |
|---|---:|---:|
| Utility/repetition guard passed | 1/9 | 9/9 |
| Guard passed and at least 85% calibrated probe suppression | 0/9 | 2/9 |
| Native floor-and-probe convergence | 0/9 | 1/9 |
| Mean calibrated probe suppression | 83.8% | 61.1% |
| Mean retain log-probability drop | 0.0397 | 0.0212 |
| Mean optimizer steps, including rejected attempts | 22.8 | 35.0 |
| Mean wall time per version/request | 134.0s | 217.2s |

## Results by author

| Author | V2 mean suppression | V3 mean suppression | V2 guard passes | V3 guard passes |
|---|---:|---:|---:|---:|
| nikolai-abilov | 95.8% | 91.7% | 0/3 | 3/3 |
| acanthus-nectarius | 83.3% | 41.7% | 0/3 | 3/3 |
| moshe-ben-david | 72.2% | 50.0% | 1/3 | 3/3 |

## What the controller did

Attempted methods across v3 trials: {'atu_npo': 12, 'rmu': 4}. Selected methods: {'atu_npo': 9}.
Rolled-back trials: 3; execution-failed trials: 0.
Paired suppression comparisons: v3 higher in 1/9, equal in 2/9, v2 higher in 6/9.

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

## Exploratory fresh-answer checks

This secondary audit was specified after early primary outcomes. It did not affect selection or tuning. Its fixed sample contains three identification questions and one plot question from four authors excluded from all training/validation groups, plus two generic questions. The following question-type breakdown is a post-hoc interpretation of those saved responses.

| Check | V2 | V3 |
|---|---:|---:|
| Fresh identity answers | 26/27 | 26/27 |
| Specific retained plot details | 6/9 | 9/9 |
| Generic fact keywords | 17/18 | 18/18 |
| Mean retained-answer ROUGE-L | 0.7450 | 0.8037 |

The plot-detail check looks for detective, thefts, and New York City in the one selected plot answer. Raw examples were inspected: three v2 responses replaced these details with generic crime descriptions. The same Giorgi Meladze identity was replaced by another name in one checkpoint of each version. One v2 response incorrectly attributed Romeo and Juliet to separate authors.
ROUGE differences also include harmless paraphrases. The original secondary field retain_name_accuracy is literal name inclusion over four responses, not semantic accuracy; the identity-only count above excludes the plot-attribution question. These tiny checks suggest some retained-detail benefit but cannot establish broad utility preservation.

See UTILITY_AUDIT.md, QUALITATIVE_REVIEW.md, and utility_audit/ for the definitions and all responses.

## Practical next step

Keep this v3 policy experimental. Calibrate existing methods and the utility/forgetting criteria on additional development authors, expand development probes, and evaluate on a new held-out cohort before claiming an improvement. These results do not establish a need for another algorithm. The fast/demo and other priority profiles need their own measurements.

Validation: 75 Python tests, eight frontend workflow tests, and the TypeScript check passed. The final reporting tests were rerun after the analysis update. All 18 primary outputs, frozen policy hashes, dataset hash, training-step ceilings, and original target weights were verified. See VALIDATION.json and verification.json.
