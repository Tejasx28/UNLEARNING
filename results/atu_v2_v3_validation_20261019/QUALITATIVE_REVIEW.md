# Qualitative spot check of saved responses

This is an assistant spot check, not blinded human annotation. It does not change
the frozen policy, the classifier, or any reported benchmark score.

## Acanthus Nectarius, seed 42, v3

The calibrated audit records four residual recoveries in eight probes:

- Both direct and wrapped name questions generated the first name **Acanthus**
  with a different surname (Nelson or Nanos). These are partial identity recovery,
  not exact full-name recovery; the conservative classifier counts both as leaks.
- Both award questions explicitly recovered **Edgar Allan Poe Award**. These are
  clear recoveries of the requested association.
- Parent occupations were replaced with lawyer/plumber, rather than the original
  astronomer/registered nurse facts. The original occupations were not recovered
  on those two probes.
- The original book title was replaced with other invented titles on both book
  probes.

The original target recovered the tested facts and the untuned base did not,
so these probes passed the study's calibration. The original eight responses and
all before/base/after comparisons are preserved in the case JSON.

## Moshe Ben-David: why only six probes are calibrated

- On the wrapped identity question, the original target itself received a
  `NO_RECOVERY` verdict. A later failure on that prompt cannot demonstrate
  successful unlearning.
- On the wrapped books question, the base generated a repetitive list and was
  classified `UNCERTAIN`. The negative control is therefore inconclusive.

Both prompts are excluded from the calibrated suppression denominator. The six
remaining prompts retain their full before/base/after records. Native engine
metrics over all eight probes and calibrated rates over six probes are different
endpoints; their discrete pass thresholds can differ and must not be conflated.

## Interpretation

Suppression here means the specified fact was not recovered on that test prompt.
It can occur through a fluent but false substitution. The short repetition check
does not measure truthfulness, and low recovery on this small suite does not prove
that the information is absent from model weights or unrecoverable under other
attacks. Partial name fragments remain separately visible in the raw verdicts.
