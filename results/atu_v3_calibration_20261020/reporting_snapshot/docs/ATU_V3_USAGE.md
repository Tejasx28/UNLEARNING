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

## Direct Python use

Construct `UnlearningRequest` with:

- `forget_data`: nonempty question/answer examples.
- `target_author`: the actual author name, when known.
- `retain_data`: unrelated training examples.
- `retain_validation_data`: independent utility examples; omitted validation data
  is deterministically split off the retain pool before training.
- `dev_probes`: prompts with `target_facts`, `answer`, or `expected_keyword`.
- `test_probes`: independent prompts used only after checkpoint selection.
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

Validation completed with 92 Python tests, 8 frontend tests, a TypeScript check,
and a real GPU retry check. The final policy regressions were rerun after the
candidate ordering was frozen (42 tests).

The [completed local comparison](../results/atu_v3_calibration_20261020/FINDINGS.md)
contains 18 runs: three reserved authors, two seeds and three policy versions.
Updated v3 suppressed all tested final answers, versus 45.8% for v2 and 34.7%
for previous v3. Only 2/6 updated runs met all measured checks together, both
for one author; unrelated refusals occurred in the other four runs. All updated
winners used refusal preference training. This is a small response-suppression
result, not proof of complete deletion or a validated router for all request types.
The version remains experimental. Source and evidence were frozen before final
testing; further tuning requires a new evaluation cohort.
