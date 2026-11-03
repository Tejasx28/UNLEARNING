# Development decisions

Two development authors; no final outcomes used.

| Candidate | Primary passes | Independent utility | Mean generated suppression | Mean updates |
|---|---:|---:|---:|---:|
| legacy_refusal | 0/2 | 27/28 | 91.7% | 40.0 |
| specific_refusal | 2/2 | 28/28 | 95.8% | 40.0 |
| fixed_npo | 0/2 | 28/28 | 0.0% | 2.0 |
| conservative_npo | 0/2 | 28/28 | 8.3% | 40.0 |

Selective refusal passed the predeclared conjunction for both authors and restored an unrelated identity refused by ordinary refusal. NPO uses the better of two development presets under the new guard. Lower-ranked methods retain prior-study settings and were not recalibrated here.

Selected NPO: conservative_npo. Selected refusal: specific_refusal.

The final recognition diagnostic uses canonical gold-answer prefixes with the tested fact excluded. Original/base development controls validated five assisted-recognition items. Earlier recognition designs were not used for calibration; their outputs remain preserved.

Both NPO configurations use measured per-answer base stopping floors. The conservative preset has lower rate and stronger retain protection, chosen under unchanged safety limits. All final arms share the stronger evaluator.
