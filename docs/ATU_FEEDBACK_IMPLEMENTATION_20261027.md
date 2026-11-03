# ATU feedback and answer-quality implementation

## Request behavior

Full Automatic starts with the heuristic method, measures generated development
recovery and retain preservation, and records why it stops, tunes or switches.
Promising partial NPO progress can receive one settings retry from the original
target while reserving a distinct fallback. Every attempt has a fresh optimizer;
all attempts share the configured time and optimizer-update allowances.

The time allowance covers the training loop and its control work. It is checked
at cooperative boundaries, so an in-progress controller check may overrun the
requested time. Model loading, immutable baseline preparation and final
evaluation add wall time. The report retains actual training and elapsed times.

The tuned retry adjusts learning rate, NPO beta, retain regularization and leaking
probe priority. It does not relax retain limits or learn from the final test.
Poor progress, answer collapse or measured quality damage selects an alternative.
Explicit methods and Quick screening retain their one-attempt scope.

## Retain budget

`retain_quality_max_drop=0.02` is the default V3 dashboard limit. It measures
relative decline in mean ROUGE-L on fixed unrelated reference questions compared
with the original model's measured responses. It is additional to likelihood
drift and per-answer guards. Both original and current raw responses are exported.
The original score must be positive and finite, and cohort/token-cap identity
must match. A zero or missing baseline cannot certify a percentage budget.

These are sample-based answer-overlap measurements. They do not measure every
retained fact or constitute a semantic-accuracy guarantee. The validation cohort
helps select checkpoints, so it is not an independent retain-generalization set.

## Evidence separation

Each selected Full fact has a canonical and a distinct answer-free development
prompt. The feedback loop sees complete responses up to its configured token cap.
The final target prompts remain separate and are evaluated after selection.
The live final retain generation also rechecks the percentage budget and cannot
report success when that check fails.

The frontend exposes the quality limit and measured original/after scores,
relative decline, sample size and generation cap. Older records show that this
measurement is absent; saved evidence is never filled with invented values.

## Verification

The integrated implementation passed 319 Python tests and 27 frontend tests,
plus TypeScript and the production build. Tests cover percentage-vs-likelihood
semantics, immutable baselines, quality damage despite acceptable likelihood,
fresh-model settings retries, reserved alternatives, shared budgets, explicit
method behavior, complete generation windows and final-test separation.

Matched local GPU validation is saved separately under
`results/feedback_validation_20261027`. Its report must be interpreted using the
actual measurements, not as a promise that every request will fully unlearn.

The first saved V2 trial demonstrates the separate quality guard: its average
retain likelihood drop was 0.0095 (within the 0.03 allowance), while fixed-cohort
ROUGE-L declined from 0.99213445 to 0.96093445, a 3.1447% relative loss. The 2%
quality guard rejected that candidate and restored the original weights. These
are development/selection measurements, not the independent final-test result.
The execution connection was interrupted after this checkpoint and provenance
were saved; completion must preserve that event in the evidence.

## Completed local GPU comparison

All four cases completed. Maria: V2 suppressed 0/6 calibrated checks; V3
suppressed 5/6 after NPO, Gradient Difference and RMU. Giorgi: V2 suppressed 0/5;
V3 suppressed 1/5 after the same three methods. One additional Giorgi check was
inconclusive for both versions, so only four of five selected facts had calibrated
coverage. Every kept checkpoint had 0% relative mean retain ROUGE-L decline on
the 25-answer cohort. All four native verdicts remain INSUFFICIENT_FORGETTING.

These are partial outcomes from two selected stress cases and one seed. Some
target responses are incorrect or incoherent; the generic fluency diagnostic is
not a target-answer quality certificate. V2 here uses canonical settings with
the same added safety wrapper, rather than a historical binary. Its first case
was recovered from exact saved rollback weights after the execution host stopped;
its reported active time is approximate and excludes downtime. No training was
repeated during recovery. Raw case records and the frozen protocol remain intact.

The dashboard's Presentation demos page links to the measured comparison.
`OPEN_FEEDBACK_VALIDATION.bat` opens the same report without starting training.
