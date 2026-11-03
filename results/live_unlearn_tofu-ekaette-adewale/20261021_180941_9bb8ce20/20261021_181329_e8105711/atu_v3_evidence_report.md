# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Ekaette Adewale_1792588386`  
**Timestamp:** `2026-10-21T18:43:06.922129`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-ekaette-adewale\20261021_180941_9bb8ce20\20261021_181329_e8105711\trial_2` (Trial #2)  
**Total Compute Duration:** `1777.3s` across `3` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `0.0%` (0/5 eligible targets; 5 requested)
- **Final Avg Log-Probability:** `-0.0694`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `3.1962`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `37.5%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `5`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0079` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 | `atu_npo` | 60.0% | 0.0000 | 100.0% | YES | **0.6700** |
| #2 ⭐ (Winner) | `rmu` | 0.0% | 0.0079 | 100.0% | YES | **0.3465** |
| #3 | `graddiff` | 20.0% | 0.0000 | 100.0% | YES | **0.4900** |
