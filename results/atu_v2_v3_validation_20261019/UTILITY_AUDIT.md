# Exploratory response-level utility audit

This secondary audit was specified after observing early primary results. It does not select methods, tune settings, or change the registered primary outcomes. Four new retain authors were selected by a fixed random seed, excluding all forget, retain-training, and retain-validation authors. Two generic keyword checks are only examples, not a general capability benchmark.

| Version | Fresh retain ROUGE-L | Name inclusion across four responses | Two-question keyword accuracy |
|---|---:|---:|---:|
| Original target | 1.0000 | 100.0% | 100.0% |
| v2, mean of nine checkpoints | 0.7450 | 97.2% | 94.4% |
| v3, mean of nine checkpoints | 0.8037 | 97.2% | 100.0% |

A failure of the primary log-probability drift guard should not be equated with loss of factual answers. Conversely, preserving four answers and two generic examples cannot establish preservation of every unrelated capability. Full response text is saved in the adjacent JSON files.


## Exploratory fresh-answer checks

This secondary audit was specified after early primary outcomes. It did not affect selection or tuning. Its fixed sample contains three identification questions and one plot question from four authors excluded from all training/validation groups, plus two generic questions. The following question-type breakdown is a post-hoc interpretation of those saved responses.

| Check | V2 | V3 |
|---|---:|---:|
| Fresh identity answers | 26/27 | 26/27 |
| Specific retained plot details | 6/9 | 9/9 |
| Generic fact keywords | 17/18 | 18/18 |
| Mean retained-answer ROUGE-L | 0.7450 | 0.8037 |

The plot-detail check looks for detective, thefts, and New York City in the one selected plot answer. Raw examples were inspected: three v2 responses replaced these details with generic crime descriptions. The same Giorgi Meladze identity was replaced by another name in one checkpoint of each version. One v2 response incorrectly attributed Romeo and Juliet to separate authors.
ROUGE differences also include harmless paraphrases. The original secondary field retain_name_accuracy is literal name inclusion over four responses, not semantic accuracy; the identity-only count above excludes the plot-attribution question. These tiny checks suggest some retained-detail benefit but cannot establish broad utility preservation.

See UTILITY_AUDIT.md, QUALITATIVE_REVIEW.md, and utility_audit/ for the definitions and all responses.
