# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Maria Lucia Sousa_1793072701`  
**Timestamp:** `2026-10-27T09:15:01.137796`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-maria-lucia-sousa\20261027_090943_1a33b5cc\20261027_091021_618d124f\trial_1` (Trial #1)  
**Total Compute Duration:** `279.27s` across `3` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (5/5 eligible targets; 5 requested)
- **Requested Suppression Target:** `100.0%` of eligible targets
- **Final Avg Log-Probability:** `-5.825`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-2.5906`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `20.0%`
- **Active Probes Tested:** `5`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0074` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0074 | 100.0% | YES | **0.8183** |
| #2 | `graddiff` | 80.0% | 0.0106 | 100.0% | YES | **0.6417** |
| #3 | `rmu` | 0.0% | 0.0130 | 100.0% | YES | **0.2413** |
