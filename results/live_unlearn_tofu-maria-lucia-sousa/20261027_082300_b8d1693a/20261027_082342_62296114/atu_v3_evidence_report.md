# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Maria Lucia Sousa_1793069828`  
**Timestamp:** `2026-10-27T08:27:08.491137`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-maria-lucia-sousa\20261027_082300_b8d1693a\20261027_082342_62296114\trial_1` (Trial #1)  
**Total Compute Duration:** `206.48s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `80.0%` (4/5 eligible targets; 5 requested)
- **Final Avg Log-Probability:** `-6.0156`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-2.7812`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `60.0%`
- **Active Probes Tested:** `5`
- **Stubborn Targets Remaining:** `1`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0177` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 80.0% | 0.0177 | 100.0% | YES | **0.6022** |
