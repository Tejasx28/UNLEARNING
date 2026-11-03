# ATU v3 execution and verification

Live dashboard requests now use v3 by default. The HTTP request can explicitly set
`engine_version` to `v2` for the legacy path. Saved replay experiments remain v2.

V3 uses locally calibrated candidate ordering and heuristic priority rules, not
a learned request classifier. Balanced requests begin with refusal preference
training; strict-privacy requests first try the highest-ranked non-refusal
optimization method; utility-priority requests prefer refusal training. Fast
requests use a short targeted NPO attempt. Full requests now allow up to eight
epochs by default; explicit lower limits remain respected. Global adapter
dampening is available only as an
explicit experimental strategy because it affects the entire TOFU adapter.
Refusal training alone does not establish knowledge deletion.

The current v3 refusal preset uses `retain_refusal_weight=2`: on unrelated
training questions it prefers the real answer over the same generic refusals
used for forget examples. The ordinary refusal objective remains available
by setting that weight to zero. This setting was chosen on development requests;
independent final tests determine its practical limits.

## Direct Python use

Construct `UnlearningRequest` with:

- `forget_data`: nonempty question/answer examples.
- `target_author`: the actual author name, when known.
- `retain_data`: unrelated training examples.
- `retain_validation_data`: independent utility examples; omitted validation data
  is deterministically split off the retain pool before training.
- `dev_probes`: prompts with `target_facts`, `answer`, or `expected_keyword`.
- `test_probes`: independent prompts used only after checkpoint selection.
- `retain_probes`: unrelated facts with known answers, checked against the
  original target at trial evaluation. Originally unrecoverable facts are excluded;
  an empty positive-control set cannot establish preservation. The default
  `max_retain_probe_drop=0` allows no loss on validated probes.
- `retain_per_example_max_drop`: maximum loss on any single measured retain
  answer (default 0.25 nats/token), in addition to the 0.03 average limit. This
  prevents gains on some answers from hiding damage to another.
- `forget_reference_log_probs`: optional untuned-base likelihood for each forget
  answer in the same order. When supplied, convergence uses these per-answer
  controls instead of the global floor. Only originally elevated answers count;
  `forget_reference_tolerance=0.1` allows that margin above the base. With no
  eligible answers, the check cannot converge.
- `calibrate_forget_reference=True`: collect those reference values automatically
  before training when none were supplied. Live v3 enables this option and adds
  known identity probes from its retain-validation cohort when available. The
  additional base-model load and measurements contribute to overall wall time.
  NPO receives the same per-question base-plus-tolerance stopping floors as the
  verifier. Without reference collection or supplied values, the legacy global
  floor remains in use and is identified as such in the evidence report.
- Trial, epoch, step, time, leakage, and utility limits. `max_total_steps` limits
  optimizer updates across all attempts, including rejected attempts;
  `max_steps_per_trial` is a separate per-attempt ceiling.

Call `ATUv3Engine(...).execute(request)`. Each execution creates a unique folder;
each trial reloads the original target as a trainable adapter. Retain baselines
are measured before the first training update. The guard snapshots trainable
weights to CPU after every optimizer update by default (`guard_every_steps=1`).
On a utility breach it tries 1/2, 1/4 and 1/8 of the last update interval,
measuring each candidate against the same original baseline and unchanged
utility limit. It keeps the first passing candidate or the previous safe state,
then stops that attempt. Interpolation changes the final weights without adding
optimizer updates; its evaluation cost still contributes to wall time.
Failed trials cannot win selection. If no safe executable checkpoint exists,
execution fails rather than publishing an unsafe model.

Development and test probe prompts cannot overlap. Missing probes do not count
as evidence of zero leakage. Generated responses are checked with the existing
semantic classifier; the original target must expose development facts before
convergence is claimed. The final cohort has its own original-target positive
control, measured after selection. These are heuristic checks, not proof of
complete deletion; the live flow additionally runs target/base controls.
Nonrepetitive symbol-heavy gibberish is conservatively marked uncertain, not
clean suppression. The generic fluency test also rejects such output; it remains
a small heuristic check rather than a grammar or broad capability assessment.

`SUCCESS` requires passing the configured criteria on the independent final
cohort. Without a final cohort, the engine reports `UNVERIFIED`. Job completion
is recorded separately from scientific success. Live retain utility is measured
ROUGE-L on held-out examples; it is not a fixed placeholder percentage.

Time limits are cooperative: training checks its deadline between batches.
Loading, an already-running GPU operation, safety evaluation, final testing, and
saving may extend wall-clock duration. The deadline prevents starting further
training batches or search attempts once exhausted; it is not a hard process kill.

## Pipeline runner

`scripts/run_pipeline.py --atu_v3` enables v3 for the research orchestrator.
Optional arguments are `--v3_priority`, `--v3_max_trials`, and
`--v3_max_time_sec`. That runner currently supplies development probes only,
so its v3 report is `UNVERIFIED`; its subsequent red-team audit is reported
separately. Use direct requests or the live flow for separate final test probes.

## Regression coverage

`tests/test_v3_integration.py` exercises real CPU NPO/refusal optimization with a
small synthetic model, clean restarts, safe rollback, unsupported probe handling,
independent final evaluation, budget boundaries, versioned runs, and the live
v3 integration. Existing model save/reload and baseline smoke tests also remain.

Validation completed with 110 Python tests for the frozen policy, 8 frontend
tests and a TypeScript check. This includes real GPU model save/reload and method
smoke tests. The separate auxiliary fragment scorer also passed its unit test
and a boundary check using the actual tokenizer.

The [selectivity follow-up](../results/atu_v3_specificity_20261020/FINDINGS.md)
compares ordinary refusal, selective refusal, fixed NPO and adaptive retries on
three reserved authors with two seeds (24 final cases). It uses independent
utility questions, per-answer untuned-base controls, direct and wrapped prompts,
forced completions and a separately declared assisted-fact audit. All arms have
a 40-update ceiling; fixed methods can use 40 on one attempt while adaptive can
use two fresh 20-update attempts. These are balanced-priority author requests,
so the study does not validate routing across different request types.
The completed adaptive arm suppressed 57/64 calibrated responses (89.1%), but
passed 0/6 primary conjunctions. All six winners were the refusal attempt;
the NPO retries did not supply a winning alternative. Its selected checkpoints
received 20 updates, versus up to 40 for fixed methods, so differences cannot be
attributed to algorithm switching alone. Direct suppression is not sufficient
evidence of forgetting.
The separately declared assisted-fact audit recovered full fact strings in
19/22 calibrated adaptive continuations, plus one partial match. Its supplied
original-answer prefixes exclude the tested fact but can include other facts;
these are assisted checks, not blind recall. The audit preserves all original
primary scores and success labels. See the linked findings for its controls,
raw responses and the distinction between full and partial recovery.

The [earlier local comparison](../results/atu_v3_calibration_20261020/FINDINGS.md)
contains 18 runs: three reserved authors, two seeds and three policy versions.
Updated v3 suppressed all tested final answers, versus 45.8% for v2 and 34.7%
for previous v3. Only 2/6 updated runs met all measured checks together, both
for one author; unrelated refusals occurred in the other four runs. All updated
winners used refusal preference training. This is a small response-suppression
result, not proof of complete deletion or a validated router for all request types.
Those figures are historical and use different cohorts and checks from the
selectivity follow-up. The version remains experimental. Source and evidence
were frozen before each study's final testing; further tuning requires a new
evaluation cohort.
