# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Anaya Jehangir_1792647188`  
**Timestamp:** `2026-10-22T11:03:08.043849`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-anaya-jehangir\20261022_104450_a93ebf9f\20261022_104652_cb0f3ffc\trial_1` (Trial #1)  
**Total Compute Duration:** `975.11s` across `3` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (5/5 eligible targets; 5 requested)
- **Final Avg Log-Probability:** `-12.8812`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-9.8812`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `40.0%`
- **Active Probes Tested:** `5`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0049` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0049 | 100.0% | YES | **0.8190** |
| #2 | `graddiff` | 60.0% | 0.0007 | 100.0% | YES | **0.6540** |
| #3 | `rmu` | 0.0% | 0.0120 | 100.0% | YES | **0.2698** |
