# ATU v3 execution and verification

Live dashboard requests now use v3 by default. The HTTP request can explicitly set
`engine_version` to `v2` for the legacy path. Saved replay experiments remain v2.

V3 uses a heuristic candidate order and priority hints, not a learned request
classifier or a validated best-method prediction. The current policy revision is
`feedback-quality-20261027`. With `method="auto"`, Balanced requests
start with ATU-NPO, then can try GradDiff, RMU, DPO refusal and gradient ascent
within the configured trial and shared training budgets. Strict-privacy requests
move refusal training to the end; utility-priority requests start with refusal
training. Fast automatic requests, or automatic budgets below 90 seconds, start
with a short NPO attempt. Refusal alone and any method's objective do not establish
knowledge deletion.

The live method selector accepts `auto`, `atu_npo`, `rmu`, `graddiff`,
`dpo_refusal`, and `ga`. An explicit method takes precedence over priority and
short-budget routing and runs exactly once, without silent fallback to a different
algorithm. Automatic mode retains adaptive retries. Unsupported methods and V2
method overrides are rejected before model execution. Global adapter dampening
is not exposed as a live method choice; it modifies the entire adapter.

Quick runs are preliminary: up to five selected facts, one attempt, at most eight
optimizer updates and up to four epochs, with a default 60-second shared
training-loop budget. Full runs support up to twenty selected facts and eight
epochs per trial, with a default 600-second shared budget and up to three attempts
in automatic mode. Explicit methods remain single-attempt in either profile.
Epoch, optimizer-step and cooperative time limits can stop training earlier.

After each attempt, the loop records a development-only `feedback_decision`.
Promising NPO results that lower answer likelihood but still recover fragments
can receive one clean-start settings retry: lower learning rate/beta, stronger
retain regularization and higher priority for leaking probes. This is bounded
to one such retry, requires measured progress and real optimizer updates, and
reserves a slot for a distinct method. Quality breaches, collapse and weak
progress move to an alternative. Explicit method choices remain one attempt.
The total attempt, time and optimizer-update limits remain unchanged.

Full live development checks include the canonical question and a separate
answer-free memory prompt for every selected fact. They use the configured
generation window and keep complete responses, including later paragraphs.
Final prompts use distinct wording and remain untouched during routing.

Live V3 adds `retain_quality_max_drop=0.02`, separate from the 0.03 likelihood
guard. It compares mean ROUGE-L against reference answers on a fixed unrelated
cohort before and after training. The limit is a **relative decline**:
`max(0, (original_score - current_score) / original_score) <= 0.02`.
For example, an original score of 0.90 allows at least 0.882; it is not a
two-percentage-point allowance or a percentage of all knowledge preserved.
Missing, zero, nonfinite or mismatched original measurements cannot establish
this check. The fixed validation sample constrains selection; it is not an
independent retain-generalization benchmark. Existing likelihood/individual
retain guards still apply. A failed fresh final quality audit cannot be green.

Live requests require all eligible selected answers to reach their calibrated
likelihood floors (`required_forget_suppression_ratio=1.0`) and allow no observed
development/final recovery (`max_probe_leak_rate=0.0`) for success. Incomplete
forgetting continues to another allowed automatic attempt, subject to the shared
budget and retain guards. Discovery does not silently remove uncertain selected
facts from training or development checks. These requirements do not guarantee
that every request can finish successfully within its safety and resource limits.

The DPO refusal preset keeps `retain_refusal_weight=2`: unrelated training
questions prefer their real answer over generic refusals. Setting that weight to
zero selects the ordinary refusal objective. These are candidate settings;
independent recovery and utility checks determine the observed outcome.

## Direct Python use

Construct `UnlearningRequest` with:

- `forget_data`: nonempty question/answer examples.
- `target_author`: the actual author name, when known.
- `method`: `auto` by default, or one of the explicit methods above. Automatic
  mode uses `max_trials`; an explicit method executes one attempt regardless of
  a larger configured trial limit.
- `priority`: an automatic-routing hint (`balanced`, `fast`, `preserve_utility`,
  `strict_privacy`); it cannot replace an explicitly requested method. Direct
  Python requests use the `UnlearningPriority` enum; HTTP requests use its string
  values.
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
- `retain_quality_max_drop`: optional relative mean ROUGE-L decline limit against
  the original model. Direct Python requests default to `None` for compatibility;
  dashboard V3 requests default to 0.02. The same cohort and token cap are used
  throughout an execution, with raw before/after responses exported. The V2 HTTP
  path rejects this option rather than claiming a training guard it does not use.
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
- `required_forget_suppression_ratio`: required share of originally elevated
  answers at or below their likelihood floor (default 1.0). Explicitly setting
  0.8 supports older research protocols; it is not the live dashboard default.

Call `ATUv3Engine(...).execute(request)`. Each execution creates a unique folder;
each trial reloads the original target as a trainable adapter. Retain baselines
are measured before the first training update. The guard snapshots trainable
weights to CPU at configured update boundaries (`guard_every_steps=2` by default),
with additional end-of-round/final checks where needed. Repeated successful
checks on an explicitly unchanged optimizer revision are skipped; each new
revision invalidates that cache.
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

## Shared training budget and diagnostics

`max_time_sec` is one shared training-loop allowance across attempts, never a
new allowance per method. Remaining time is divided among the remaining allowed
attempts; an early-finished attempt leaves unused time available to later ones.
There are no hidden 180/360-second minimums or automatic extensions after the
shared allowance is exhausted.

Model loading, the original-target baseline, NPO/RMU reference preparation and
initial controller probing occur before the allocated method timer starts.
The timed method loop includes its in-loop safety/controller work. Final trial
evaluation, independent final testing, saving and process startup contribute to
wall-clock time separately. Limits remain cooperative: an already-running GPU
operation or check may finish after a boundary, but no further method receives a
fresh budget after the shared allowance has been consumed. The time budget is
not a hard process deadline.

Each new trial exports its actual optimizer-update count, allocated/requested
budget, preparation and optimization-loop durations, cumulative budget use and
kept-parameter change measurements after rollback. Update diagnostics distinguish
`NO_OPTIMIZER_UPDATES`, `UPDATES_ROLLED_BACK_OR_NO_EFFECT`, and
`UPDATED_WEIGHTS_KEPT`. The number of mini-batches is not the number of optimizer
updates; partial accumulation groups are flushed and scaled at epoch/round ends.
The monitor reports preparation, optimizer updates and evaluation as they happen.
The Attempts view shows updates, training time and measured metrics; the complete
JSON export includes the detailed timing and kept-weight deltas. A completed job
with no optimizer updates cannot claim successful training.

The leakage matcher uses token boundaries, excludes target content already given
in the prompt and ignores generic biographical boilerplate as a partial match.
Distinctive non-prompt values can still count as partial recovery. This remains a
deterministic heuristic with limited aliases; inspect actual generated answers,
controls and coverage. Reverse/assisted prompts cannot substitute for valid
forward-fact coverage. Rechecking saved responses can correct labels but cannot
produce missing model measurements, and such records remain explicitly marked
as rechecked and incomplete.

In the frontend, mixed calibrated outcomes are shown as partial suppression with
counts. A residual leak remains visible even if other checks improved; passing
retain guards does not imply successful forgetting.

Experiment settings persist while moving between authors, sources and reports
within the dashboard session. Quick reports explain their one-attempt/eight-update
limit and offer **Configure Full experiment**. That action opens setup without
submitting GPU work. Increasing a Quick time budget does not remove its step or
trial limits.

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

Historical frozen-policy validation completed with 110 Python tests, 8 frontend
tests and a TypeScript check. Those counts describe the archived policy, rather
than the current 22 October 2026 implementation. That historical validation
included real GPU model save/reload and method smoke tests. The separate auxiliary fragment scorer also passed its unit test
and a boundary check using the actual tokenizer.

Current regression coverage also includes `tests/test_routing_budget_regressions.py`,
`tests/test_training_update_regressions.py`, `tests/test_leak_scoring_regressions.py`
and `tests/test_live_pipeline_regressions.py` for method propagation, shared budgets,
real optimizer updates, retained checkpoints and response-scoring boundaries.

## Historical empirical studies

The studies below evaluated frozen 20 October 2026 code and are preserved without
rescoring their original artifacts. They do not validate the current heuristic
routing order or changed runtime behavior.

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
