# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Finton Kavanagh_1792585915`  
**Timestamp:** `2026-10-21T18:01:55.912101`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-finton-kavanagh\20261021_175323_8c81a177\20261021_175507_c719a066\trial_1` (Trial #1)  
**Total Compute Duration:** `408.7s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `0.0%` (0/5 eligible targets; 5 requested)
- **Final Avg Log-Probability:** `-0.6344`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `2.6875`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `100.0%`
- **Active Probes Tested:** `5`
- **Stubborn Targets Remaining:** `5`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0001` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 0.0% | 0.0001 | 100.0% | YES | **0.3489** |
