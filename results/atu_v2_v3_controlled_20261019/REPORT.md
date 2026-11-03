# Controlled ATU v2 versus v3 study

Development author: Basil. Held-out authors: Nikolai, Acanthus, Moshe. Seeds: 42, 43, 44.
Both versions start from the same target and share all request data and test prompts.
Maximum training budget: 40 optimizer steps per version. V2: one attempt, up to 8 rounds;
v3: up to two clean-start attempts, up to 20 steps each. Actual steps and total runtime are reported.
V2 retains its canonical configured learning rate/beta and stopping behavior; v3 uses its deployed heuristic.
This compares complete policies, not just the algorithm at identical hyperparameters.

| Phase | Author | Seed | Version | Method | Validated | Suppressed % | Residual | Retain log-P drop | Safe | Steps | Seconds |
|---|---|---:|---|---|---:|---:|---:|---:|---|---:|---:|
| pilot | basil-mahfouz-al-kuwaiti | 42 | v2 | atu_npo | 8 | 100.0 | 0 | 0.0655 | False | 20 | 169.9 |

## Aggregate held-out results


## Interpretation limits

- Eight final prompts per author cover names, parents, awards and books; all 20 canonical answers also receive likelihood and ROUGE evaluation.
- Suppression is counted only where the original target recovers a fact and the untuned base does not. Uncertain/degenerate responses are not counted as clean suppression.
- The retain guard uses 12 held-out examples from four unrelated authors. The fluency number is a short repetition proxy, not a broad capability benchmark.
- Three authors and three seeds are a small local experiment, not proof of deletion or a universally superior method.
- Final responses never select methods or checkpoints. Policy changes may use the development author only.
- A rollback may preserve utility by returning weights with little or no forgetting. Safe does not mean successful unlearning.
