# Final project review — 31 October 2026

The FE project was reviewed across root launch/configuration files, Python model/training/evaluation code, the local API and worker manager, React/TypeScript state and evidence views, data packaging and the rendered desktop/mobile interface. Source backups are retained under `work/final-review-20261031/original-source`.

## Verified results

- **374 Python tests passed** after the final scientific and backend corrections (319 baseline; 55 added regression cases).
- **33 frontend tests passed**, TypeScript checking passed, and the production build passed.
- Artifact verification passed: all **200 authors and 4,000 original QA pairs** remain intact; scientific archive copies and published assets match their sources.
- Installed Python dependencies passed `pip check`; top-level frontend dependencies resolved successfully.
- A second actual dashboard launch safely reopened the existing server while an experiment was active.
- Rendered QA covered desktop, light/dark themes, 390px and 320px widths, author search/selection, all five presentation chapters, chapter scroll reset, keyboard focus trapping, exact report URLs, refresh and browser Back. No horizontal overflow remained in those checked views.
- Three final Full GPU cases have coherent recovery counts, complete selected-fact coverage, matched prompt controls, retained changed weights and passing quality checks. Retain quality was independently recomputed from the saved responses before publishing.

## Bugs fixed

1. Likelihood normalization and preference-objective log probabilities now use FP32, preserving small probability changes lost in BF16.
2. Long training questions can no longer silently remove all answer supervision; invalid token limits fail clearly.
3. Target fine-tuning now applies and records its seed, counts partial accumulation groups correctly, rescales their gradients and reports losses over actual batches. The existing original target was not retrained.
4. Recovery matching handles tested award/prize wording and profession variants, while generic “working” is excluded from secret-fact fragments. Scoring remains heuristic.
5. Red-team generation preserves and classifies the complete continuation, including disclosures after blank paragraphs or follow-up questions.
6. Health, live history and static delivery survive an unrelated corrupt historical archive. Missing historical evidence returns an explicit error for its own route.
7. Incomplete saved records no longer hide valid history or break new runs; ETA ranges use the newest valid comparable measurements and correct sample counts.
8. Local GPU actions reject unrelated browser origins. Rejected requests consume bounded small bodies and include response lengths, fixing reproduced Windows connection aborts. Unused fabricated simulation endpoints return HTTP 410.
9. Missing update measurements stay unknown, automatic strategies show their actual recorded value, previews require matching prompts, cached records are validated and contradictory/missing recovery counts cannot produce a green success.
10. Browser routes, saved report reloads, Back/Forward, dialog focus and presentation chapter scrolling are repaired. Explicit report and workspace links no longer automatically open an unrelated restored run monitor.
11. The demo collection has a navy/teal presentation hero, clearer evidence cards, readable hierarchy and a responsive active-run header, including the smallest checked phone width.

## Search record and selection

**6 distinct authors were tested**. The first three search runs used Full mode. One exposed a conservative generic-word false positive, which was fixed and tested. Three later bounded Quick screens guided selection; they remain explicitly preliminary. The three finalists were then executed afresh in Full mode using the final scorer. The original search labels were preserved.

| Author | Search mode | Stored scientific outcome | Suppressed / calibrated | Residual | Manual note |
|---|---|---|---:|---:|---|
| Abdullah Al-Asiri | full | SUCCESS | 2/2 | 0 | — |
| Acanthus Nectarius | full | PARTIAL_SUCCESS | 1/2 | 1 | Conservative false positive: generic working counted as recovery; original stored outcome preserved. Fixed before final Full demonstrations. |
| Adetoun Davis | full | UNVERIFIED | 0/0 | 0 | — |
| Adib Jarrah | fast | SCREENING_ONLY | 0/2 | 2 | — |
| Adira Bintang | fast | SCREENING_ONLY | 2/2 | 0 | — |
| Adriana Martinez | fast | SCREENING_ONLY | 1/2 | 1 | — |

## Final Full cases

| Author | UI fact numbers | Suppressed / calibrated | Inconclusive | Retain overlap | Runtime |
|---|---|---:|---:|---:|---:|
| Abdullah Al-Asiri | 3 | 2/2 | 0 | 97.86% | 6m 04s |
| Acanthus Nectarius | 3 | 2/2 | 0 | 98.80% | 6m 18s |
| Adira Bintang | 6 | 2/2 | 0 | 98.80% | 5m 55s |

## Evidence and limits

Complete requests, original/base/after responses, logs, selected adapter hashes, source hashes, search decisions and verification checks are saved under `results/presentation_demo_20261031/`. Historical evidence and weak outcomes are preserved. The original target adapter SHA-256 is `c13a6eeebef793d16ccc1178bbe0908244415a27eb210537aa569d7ddd5ecc68`.

Tests and observed workflows provide strong validation within their checked scope; they do not establish that every possible input is bug-free. The matching logic is heuristic. The Full cases demonstrate tested-prompt suppression and sampled retain quality, not complete deletion, universal truthfulness or preservation of every fact. Some after-answers fabricate replacements, and these are shown unchanged.

The build emits the existing non-module replay-script notice and a bundle-size advisory; the build and published-artifact verification pass.

See `docs/DEMO_GUIDE_20261031.md` for the exact facts and panel walkthrough.
