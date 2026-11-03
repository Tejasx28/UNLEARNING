# ATU v3 calibration and fresh-request comparison

Two additional development authors were used for method calibration. Three separate authors and two seeds were reserved for the final test. The final test compares whole policies; it does not isolate method selection from training length, safety granularity or other controller changes.

| Outcome | V2 | Previous V3 | Updated V3 |
|---|---:|---:|---:|
| Mean calibrated probe suppression | 45.8% | 34.7% | 100.0% |
| Configured utility/fluency guard passes | 0/6 | 6/6 | 6/6 |
| Guard passes and at least 85% suppression | 0/6 | 0/6 | 6/6 |
| Mean retain log-probability drop | 0.0393 | 0.0146 | 0.0130 |
| Mean optimizer steps | 23.3 | 40.0 | 40.0 |
| Mean run time | 288.2s | 453.6s | 314.6s |
| Native floor/probe convergence | 0/6 | 0/6 | 2/6 |
| All measured checks together (secondary) | 0/6 | 0/6 | 2/6 |

Suppression is counted only where the original fine-tuned target recovers the fact and the untuned base does not. Uncertain or degenerate outputs never count as clean suppression. Each request has twelve final prompts covering four fact groups: direct questions, neutral wrappers and wrappers explicitly asking the model to ignore forgetting/refusal instructions. All variants use a 48-token generation cap; all twenty original answers receive likelihood evaluation and the first five receive the secondary ROUGE check. The utility limit stays at 0.03 for all variants.

## Interpretation and next research step

The controller changes, development calibration, retry checks and final comparison are complete. Updated V3 suppresses more of the tested generated answers than both reference policies, and its configured utility/fluency guard passes in all six final runs. This is evidence of improved response suppression in this local study.

Only 2/6 updated runs meet all measured checks together, covering 1 of the three authors. Updated V3 retains 30/36 originally correct unrelated full-name answers. The six failures are refusals on unrelated people (Femke Van der Veen on both Raven runs; Jaime Vasquez and Rafael Diaz on both Ricardo runs). These failures are visible even though the configured retain guard passes.

All six selected updated checkpoints use refusal preference training. The router uses calibrated ordering and priority hints; this study does not demonstrate semantic request understanding or an advantage from learning which algorithm fits each request. A real fallback occurs on Raven seed 43 (37 refusal updates, then 3 NPO updates); the earlier refusal checkpoint wins.

Keep this version experimental. Further work should address unrelated refusals, use author-specific likelihood controls, and compare fixed-method policies with adaptive selection on a newly reserved cohort and broader utility/attack tests. Those would be new experiments; do not retune this version on the final cohort or call the present result irreversible knowledge deletion.

The exploratory untuned-base diagnostic also fails the existing 80% global likelihood-floor criterion for every author (raven-marais: 65%, ricardo-gabriel-sandoval: 15%, patrick-ryan-o-donnell: 20%). This shows that the global threshold is not calibrated uniformly across these authors; it does not establish that the updated checkpoints erased knowledge. The diagnostic was specified after the first final outcome and leaves the primary thresholds, metrics and success counts unchanged. See [FLOOR_DIAGNOSTIC.md](FLOOR_DIAGNOSTIC.md).

See [QUALITATIVE_REVIEW.md](QUALITATIVE_REVIEW.md) for original and checkpoint responses, and [verification.json](verification.json) for frozen-source, checkpoint and original-target integrity checks.

Read [REPORT.md](REPORT.md) for paired outcomes, development measurements, raw-evidence locations and limits.
