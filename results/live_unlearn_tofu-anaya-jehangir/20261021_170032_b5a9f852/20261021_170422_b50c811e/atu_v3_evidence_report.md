# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Anaya Jehangir_1792583517`  
**Timestamp:** `2026-10-21T17:21:57.373570`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-anaya-jehangir\20261021_170032_b5a9f852\20261021_170422_b50c811e\trial_1` (Trial #1)  
**Total Compute Duration:** `1055.28s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `0.0%` (0/5 eligible targets; 5 requested)
- **Final Avg Log-Probability:** `-0.7393`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `2.2607`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `80.0%`
- **Active Probes Tested:** `5`
- **Stubborn Targets Remaining:** `5`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0003` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 0.0% | 0.0003 | 100.0% | YES | **0.3677** |
| #2 | `rmu` | 0.0% | 0.0009 | 100.0% | YES | **0.3424** |
