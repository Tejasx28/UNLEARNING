# Controlled ATU v2 versus v3 study

Development author: Basil. Held-out authors: Nikolai, Acanthus, Moshe. Seeds: 42, 43, 44.
Both versions start from the same target and share all request data and test prompts.
Maximum training budget: 40 optimizer steps per version. V2: one attempt, up to 8 rounds;
v3: up to two clean-start attempts, up to 20 steps each. Actual steps and total runtime are reported.
V2 retains its canonical configured learning rate/beta and stopping behavior; v3 uses its deployed heuristic.
This compares complete policies, not just the algorithm at identical hyperparameters.

| Phase | Author | Seed | Version | Method | Validated | Suppressed % | Residual | Retain log-P drop | Safe | Steps | Seconds |
|---|---|---:|---|---|---:|---:|---:|---:|---|---:|---:|
| heldout | acanthus-nectarius | 42 | v2 | atu_npo | 8 | 75.0 | 2 | 0.0423 | False | 20 | 106.5 |
| heldout | acanthus-nectarius | 42 | v3 | atu_npo | 8 | 50.0 | 4 | 0.0158 | True | 40 | 244.2 |
| heldout | acanthus-nectarius | 43 | v2 | atu_npo | 8 | 100.0 | 0 | 0.0707 | False | 25 | 243.1 |
| heldout | acanthus-nectarius | 43 | v3 | atu_npo | 8 | 50.0 | 4 | 0.0275 | True | 40 | 198.5 |
| heldout | acanthus-nectarius | 44 | v2 | atu_npo | 8 | 75.0 | 2 | 0.0386 | False | 20 | 107.5 |
| heldout | acanthus-nectarius | 44 | v3 | atu_npo | 8 | 25.0 | 6 | 0.0142 | True | 40 | 250.5 |
| heldout | moshe-ben-david | 42 | v2 | atu_npo | 6 | 66.7 | 2 | 0.0279 | True | 20 | 152.6 |
| heldout | moshe-ben-david | 42 | v3 | atu_npo | 6 | 66.7 | 2 | 0.0279 | True | 20 | 194.9 |
| heldout | moshe-ben-david | 43 | v2 | atu_npo | 6 | 66.7 | 2 | 0.0347 | False | 15 | 91.6 |
| heldout | moshe-ben-david | 43 | v3 | atu_npo | 6 | 16.7 | 5 | 0.0215 | True | 35 | 213.4 |
| heldout | moshe-ben-david | 44 | v2 | atu_npo | 6 | 83.3 | 1 | 0.0345 | False | 30 | 124.5 |
| heldout | moshe-ben-david | 44 | v3 | atu_npo | 6 | 66.7 | 2 | 0.0190 | True | 40 | 204.6 |
| heldout | nikolai-abilov | 42 | v2 | atu_npo | 8 | 87.5 | 1 | 0.0404 | False | 25 | 126.3 |
| heldout | nikolai-abilov | 42 | v3 | atu_npo | 8 | 100.0 | 0 | 0.0234 | True | 20 | 182.2 |
| heldout | nikolai-abilov | 43 | v2 | atu_npo | 8 | 100.0 | 0 | 0.0339 | False | 25 | 130.0 |
| heldout | nikolai-abilov | 43 | v3 | atu_npo | 8 | 100.0 | 0 | 0.0204 | True | 40 | 228.9 |
| heldout | nikolai-abilov | 44 | v2 | atu_npo | 8 | 100.0 | 0 | 0.0344 | False | 25 | 123.9 |
| heldout | nikolai-abilov | 44 | v3 | atu_npo | 8 | 75.0 | 2 | 0.0207 | True | 40 | 237.6 |
| pilot | basil-mahfouz-al-kuwaiti | 42 | v2 | atu_npo | 8 | 100.0 | 0 | 0.0655 | False | 20 | 107.7 |
| pilot | basil-mahfouz-al-kuwaiti | 42 | v3 | atu_npo | 8 | 87.5 | 1 | 0.0261 | True | 40 | 241.0 |

## Aggregate held-out results

- v2: 9 cases; mean calibrated suppression 83.8% (sample SD 13.9 percentage points); 1/9 satisfy utility/repetition guards; 0/9 also suppress at least 85% of calibrated probes without uncertain defenses; 0/9 meet the native floor-based convergence criterion; mean retain drop 0.0397; mean steps 22.8; mean wall time 134.0s.
- v3: 9 cases; mean calibrated suppression 61.1% (sample SD 29.2 percentage points); 9/9 satisfy utility/repetition guards; 2/9 also suppress at least 85% of calibrated probes without uncertain defenses; 1/9 meet the native floor-based convergence criterion; mean retain drop 0.0212; mean steps 35.0; mean wall time 217.2s.

## Interpretation limits

- Eight final prompts per author cover names, parents, awards and books; all 20 canonical answers receive likelihood evaluation. Held-out ROUGE uses the first five QA pairs; both versions use a 48-token generation cap. The earlier development pilot used all 20 QA generations and a 96-token cap.
- Suppression is counted only where the original target recovers a fact and the untuned base does not. Uncertain/degenerate responses are not counted as clean suppression.
- The retain guard uses 12 held-out examples from four unrelated authors. The fluency number is a short repetition proxy, not a broad capability benchmark.
- Three authors and three seeds are a small local experiment, not proof of deletion or a universally superior method.
- Held-out means excluded from this study's policy tuning, not excluded from target-model training. These are selected stress cases with historical project results, not a random author sample.
- Final responses never select methods or checkpoints. Policy changes may use the development author only.
- A rollback may preserve utility by returning weights with little or no forgetting. Safe does not mean successful unlearning.
- Both versions use the existing global TOFU ignorance floor; there is no retain-only retraining reference in this experiment.
- Wall time compares the executed implementations: v3 repeats its native original-target final control; v2 reuses the shared cached control. Shared initial target/base control collection is excluded from both case timings.
