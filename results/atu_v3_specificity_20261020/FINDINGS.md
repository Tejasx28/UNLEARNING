# Completed ATU v3 comparison

The planned code changes and testing are finished. Adaptive V3 can try another method and keep the better checkpoint, but this study did not establish reliable forgetting.

We tested three reserved author requests with two training seeds and four policies: 24 final runs. These are three authors repeated across seeds, not six independent authors. No final result was used to tune the policy.

| Policy | Clean response suppression | Passed all primary checks | Unrelated answer checks retained |
|---|---:|---:|---:|
| Ordinary refusal | 22/64 (34.4%) | 1/6 | 81/84 |
| Selective refusal | 36/64 (56.2%) | 1/6 | 80/84 |
| Fixed NPO | 32/64 (50.0%) | 0/6 | 84/84 |
| Adaptive V3 | 57/64 (89.1%) | 0/6 | 80/84 |

Each policy repeats the same fourteen unrelated questions across six runs. The primary checks require at least 85% clean response suppression, at least 80% base-relative whole-answer likelihood suppression, passing safety guards and preservation of every originally correct independent utility answer. Repeated or uncertain text does not count as successful suppression. Prompt forms repeat four fact groups; these are correlated measurements.

Adaptive V3 suppressed 57/64 calibrated responses, but its original answers remained too likely and it failed four unrelated-answer checks involving 1 distinct question. Every adaptive run tried 20 refusal updates and 20 NPO updates from separate original-model starts; all six selected the refusal attempt. This does not show a benefit from switching algorithms. Fixed selective refusal received 40 updates, so its comparison also changes training length per attempt.

The changes add training to preserve unrelated answers, checks for damage to each retain answer, known-fact retain probes and per-answer comparisons against the untuned base. Development gains did not generalize reliably to final requests. Failed unrelated answers were wrong names; the extra refusal penalty alone did not prevent that damage.

The separate assisted-fact audit found full or partial fact recovery in 20/22 calibrated adaptive continuations, with 0 uncertain outputs (19 full and 1 partial classifier matches). Partial matches can include only part of a name. It supplies an original-answer prefix that excludes the tested fact but may contain other facts. This auxiliary audit changes no primary success labels. See [the audit](FRAGMENT_AUDIT.md) and [raw assisted responses](FRAGMENT_RESPONSE_REVIEW.md).

Validation: 110 Python tests passed for the frozen policy, plus 8 frontend tests and a TypeScript check. The separate fragment scorer also passed its unit test and a real-tokenizer boundary check. See [validation records](VALIDATION.json).

The original target checkpoint matches all seven files in the initial backup. Previous studies and all final checkpoints are preserved. V3 remains experimental; these results do not establish complete knowledge deletion.

Read [REPORT.md](REPORT.md) for every case, exact methods, controls, failures and limitations.
