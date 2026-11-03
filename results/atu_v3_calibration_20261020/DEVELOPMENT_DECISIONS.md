# Development decisions (before fresh held-out testing)

The two development authors were selected deterministically from the catalog with seed 20261020. The next three authors were reserved before running any training. Historical four-author cases and prior live examples were excluded from this new cohort.

Every development configuration receives the same 40-update ceiling and the unchanged 0.03 mean retain log-probability limit. All methods receive the same training/validation examples and eight development prompts covering four fact groups in two styles. Final prompts are absent from development training and selection.

Candidate settings are recorded in development_protocol.json. The existing GA baseline was added in development_ga_extension_plan.json before its execution and before final testing. Global adapter dampening is excluded from automatic selection because it affects the entire adapter rather than a specific request.

Selection rule declared during development: consider utility-safe performance first; compare mean calibrated development suppression and worst-author suppression, then retained fresh identities, then lower mean retain drift and update count. Two NPO settings compete for one NPO slot; fallback order uses distinct methods. These are local candidate calibrations, not a learned request classifier or universal method recommendations.

The final policy and reasons for any adjustments will be appended here before freezing. No final-test outcome may be used to tune this study's policy.

## Quality scoring correction during development

The first RMU candidate produced nonrepetitive bracket/identifier gibberish. The existing repetition-only classifier and generic fluency proxy initially counted it as a clean defense. This observation came from development evidence only. The classifier now conservatively marks symbol-heavy non-prose output UNCERTAIN, and generic fluency requires nondegenerate output. Regression tests cover the observed strings and ordinary prose/refusals/dates.

All saved development cases will be re-scored under this same corrected gate in quality_reaudit/, retaining the original files. Missing raw generic responses are generated from the saved checkpoint; probe verdicts are recomputed from saved responses. This development re-audit does not retrain any model. Subsequent development runs can already use the correction when deciding whether to roll an unsafe final model back to the original target.

The final comparison explicitly imports one common current audit scorer even when search imports the old source snapshot. This avoids granting the previous version an easier or harder final scoring rule. Final prompts include an additional refusal-bypass style, declared in final_probe_extension_plan.json before any held-out outcome.

## Final development policy

After common quality re-scoring, mean calibrated suppression was 100% for refusal training, 66.7% for standard ATU-NPO, 58.3% for NPO with retain weight 4, 50% each for GA and GradDiff, and 8.3% for RMU. Refusal training retained all 12 development identity answers and had mean retain drift 0.0003. Standard NPO and GA also retained all 12 identity answers. Higher-retain NPO and GradDiff retained 11/12; RMU retained 10/12.

The eligibility rule was strengthened during development because the average likelihood guard masked individual identity errors: preferred configurations must pass that guard and keep every originally correct development identity answer. Mean suppression and worst-author suppression then rank candidates, followed by lower drift and fewer updates. This used development utility examples only. Six different utility authors were reserved for the final cohort before any final inference.

The chosen balanced order is refusal preference training, ATU-NPO, GA, GradDiff, then RMU. The higher-retain NPO setting did not improve this trade-off, so the NPO slot keeps beta 0.5, LR 5e-5 and retain weight 1. Refusal uses beta 2, gamma 0.5, LR 5e-5 and retain weight 1. Full attempts can use up to eight epochs; the primary comparison keeps a shared total limit of 40 optimizer updates.

Strict-privacy remains an unvalidated priority hint that starts with the highest-ranked non-refusal method (ATU-NPO), instead of assuming RMU provides stronger privacy. Fast remains a short NPO experiment. No preference or refusal response is itself proof of knowledge deletion.

A separate real-GPU plumbing smoke intentionally starts with a zero-change adapter operation, then checks a fresh calibrated refusal retry and checkpoint selection. It uses only development data and is excluded from performance aggregates.

No final outcomes have been inspected or used to choose these settings. policy_selection.json records the ranking and configurations. Remaining comparisons are a fresh whole-policy test, not an isolated proof that routing itself is better.
