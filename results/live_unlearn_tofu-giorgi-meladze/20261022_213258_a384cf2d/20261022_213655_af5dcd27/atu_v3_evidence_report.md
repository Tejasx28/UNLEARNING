# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Giorgi Meladze_1792686863`  
**Timestamp:** `2026-10-22T22:04:23.085897`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-giorgi-meladze\20261022_213258_a384cf2d\20261022_213655_af5dcd27\trial_2` (Trial #2)  
**Total Compute Duration:** `1647.77s` across `3` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `60.0%` (3/5 eligible targets; 5 requested)
- **Final Avg Log-Probability:** `-4.1437`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-1.0156`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `80.0%`
- **Active Probes Tested:** `5`
- **Stubborn Targets Remaining:** `2`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 | `atu_npo` | 0.0% | 0.0000 | 100.0% | YES | **0.3500** |
| #2 ⭐ (Winner) | `graddiff` | 60.0% | 0.0000 | 100.0% | YES | **0.6400** |
| #3 | `rmu` | 0.0% | 0.0058 | 100.0% | YES | **0.3020** |
