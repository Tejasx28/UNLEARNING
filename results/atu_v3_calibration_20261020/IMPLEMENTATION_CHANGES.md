# Changes checked in this iteration

- Check retain likelihood after each optimizer update by default. On a breach, test smaller portions of the final update against the unchanged original utility limit, then stop that attempt.
- Count actual optimizer updates, including rejected updates, and support one shared update ceiling across attempts.
- Use method-specific presets for both initial plans and retries. Try a different queued method before repeating a failed strategy; each attempt reloads the original target.
- Retain the earlier safe candidates for final selection, including when a later attempt is worse.
- Correct symbol-heavy nonrepetitive gibberish scoring: uncertain output cannot count as clean suppression. Generic fluency checks also reject detected degeneracy and save their responses.
- Preserve original-target retain representations for RMU without loading a second full model. GradDiff and RMU honor requested retain protection.
- Allow eight epochs for full v3 requests by default in direct use, live execution and the command-line runner. Preserve v2 defaults and explicit lower limits.
- Record the policy revision, actual training counts, stop reasons, controller decisions, rollback evidence and the narrow scope of capability checks.

The locally calibrated balanced order is refusal preference training, adaptive NPO, GA, GradDiff, then RMU. Priority hints are heuristics, not a learned semantic request classifier. Fast and strict-privacy profiles were not established by the balanced-policy comparison.

Validation: 92 Python tests passed, including real GPU backward passes and checkpoint save/reload. The final policy regressions were rerun (42 passed). Eight frontend workflow tests and the TypeScript check passed. A separate real-GPU retry smoke verified no-op failure -> fresh refusal training -> selection of the better second checkpoint; it is excluded from performance statistics.

A passing utility guard is not proof that every unrelated answer is preserved. Suppressed responses and refusals are not proof of irreversible knowledge erasure. The independent final comparison evaluates those practical limits and remains separate from policy tuning.

## Preserved state

The prior source is in .project-checkpoints/before-v3-calibration_20261020_100543, verified against the previous study's frozen hashes. The new evaluated core is in this study's source_snapshot/ with frozen_protocol.json. Original target weights and the catalog are checked for integrity. Every comparison version writes separate checkpoint paths.
