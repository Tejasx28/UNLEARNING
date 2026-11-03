# Multi-fact unlearning debugging — 27 October 2026

The reported `2/6` or `3/6` is the number of calibrated recovery checks suppressed,
not a count of missing result pages. Five selected facts produce six live checks
because the first fact receives an additional prompt. A completed process can
still leave information recoverable.

## Confirmed findings and fixes

1. **Settings reset silently.** Changing authors remounted a panel that owned its
   settings. Full/manual method/custom budget reverted to Quick/auto/defaults.
   Settings now belong to the app session and survive author changes and return
   navigation from results. Fact selection remains specific to the author.
2. **Quick could be mistaken for a longer Full run.** Increasing its time allowance
   did not lift the eight-update or one-attempt caps. Setup and result pages now
   explain this and provide a Full configuration action without starting training.
3. **Mixed discovery omitted selected targets.** If one selected fact was exposed
   and another uncertain, only the exposed fact reached training/development.
   A failing integration test reproduced this omission. All selected QA entries
   now reach both; discovery remains evidence rather than a hidden selection filter.
4. **The controller's taper canceled itself.** Dividing by the sum of all target
   weights normalized a weight of 0.2 back to a full-strength gradient. Regression
   tests reproduced the error. The denominator now keeps sub-unit attenuation
   effective and preserves the existing relative scaling for boosted targets.
5. **The stopping threshold allowed incomplete likelihood suppression.** The
   evaluator hardcoded 80%, and the generic request could tolerate 15% probe
   recovery. The suppression requirement is now explicit and defaults to 100%.
   Live requests also require zero tolerated recovery. The reporter independently
   rechecks these requirements, including when given a stale converged verdict.
   Explicit 80% remains available for reproducing older research settings.
6. **Unmeasured probes appeared as measured leaks.** Pending development checks
   now keep their targets active without inventing `LEAKING` evidence.
7. **Comparison warnings missed important differences.** Seed, recovery protocol,
   retain limit and retain weight now participate in input-comparability warnings.
8. **Explicit CPU loading was overridden on GPU machines.** `device_map=None`
   and explicit CPU requests now remain on CPU; automatic loading still uses CUDA
   when available. The live flow also handles indexed devices such as `cuda:0`
   consistently. Device-selection regressions cover these paths.
9. **The reusable controlled-audit helper accepted missing controls.** It now
   requires matching prompts/targets and a clean base control for verified
   suppression, keeps uncertain outputs inconclusive, and measures retain loss
   only where the original model recovered the fact. Thirteen regressions cover
   these boundaries; twelve failed before the fix. This helper is separate from
   the live runner's already stricter calibration and did not cause Maria's score.
10. **Likelihood suppression wording obscured residual recovery.** Future selection
    explanations explicitly distinguish likelihood suppression from development
    recovery. The Attempts view explains that a low answer likelihood can still
    leave the fact recoverable. Stored model measurements remain unchanged.

## Observed failing run

`job_1793069520833_5c7fb553` selected Maria Lucia Sousa's first five QA entries.
It was Quick/automatic with a 300-second allowance, still capped at eight updates
and one attempt. Retain protection rejected a later state and kept a backtracked
safe checkpoint. Its final audit reported 2/6 suppressions and four real residual
recoveries. All five facts were confirmed in this particular discovery, so the
mixed-discovery omission is a separate reproduced bug, not its direct cause.

The raw answers still disclose Brazil and/or 1957. The old measurements are
preserved. Weakening the matcher or relabeling these responses would not fix
their recovery.

## Validation

- Final combined Python suite: **273 tests passed** after all functional fixes.
  Machine-readable results: `results/deep_debug_20261027/python-tests.xml`.
- Frontend: **23 tests passed**, TypeScript passed and production build published.
- Browser verified Full + RMU + five-minute settings across author changes and
  result navigation, and the Quick-to-Full configuration action. No browser
  action submitted a training job during these checks.
- A fresh Full GPU validation on Maria's same five selected facts completed as
  `job_1793072372603_ee6a0f59`, archived under
  `results/deep_debug_20261027/maria_full`. ATU-NPO, GradDiff and RMU performed
  8, 16 and 8 optimizer updates respectively. The selected safe ATU-NPO checkpoint
  suppressed **4/6** calibrated checks, with **two residual recoveries**, zero
  inconclusive checks and 5/5 selected facts covered. Retain answer overlap was
  **98.36% on 25 examples**. Both the engine and live audit report `PARTIAL_SUCCESS`.
  The run took about 7m36s including worker startup; pipeline computation was
  444.05 seconds. The original target's full SHA-256 before and after matches.
- The earlier Quick run suppressed 2/6 checks. The fresh validation uses a
  different profile, so this is not an isolated causal estimate of each code
  change. The remaining biography responses still reveal Brazil and/or 1957.
  The likelihood floor passing for all answers did not erase those fragments.

## Limits

Full automatic mode can try up to three fresh attempts within one shared training
allowance. Retain guards, epoch limits and remaining time can still prevent
complete suppression. A partial measured result must remain partial. Passing
tested prompts does not establish universal knowledge deletion, and target
suppression can generate incorrect replacement answers. Retain answer overlap
measures a limited unrelated sample, not every fact in the model.
