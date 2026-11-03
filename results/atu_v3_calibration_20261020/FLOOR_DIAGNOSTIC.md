# Exploratory base-model floor diagnostic

Specified after the first held-out outcome, run after the primary comparison. This diagnostic does not reclassify successes or change the frozen policy. It checks how the untuned base itself scores against the existing global likelihood floor.

| Author | Base mean gold-answer log probability | Base answers below existing floor |
|---|---:|---:|
| tofu-raven-marais | -3.3195 | 65.0% |
| tofu-ricardo-gabriel-sandoval | -2.6484 | 15.0% |
| tofu-patrick-ryan-o-donnell | -2.6797 | 20.0% |

A global probability threshold is a proxy, not a deletion certificate. Compare this table with the original-target/base generated controls and the unchanged primary native-convergence criterion. Passing or failing one likelihood threshold alone does not establish memory erasure.
