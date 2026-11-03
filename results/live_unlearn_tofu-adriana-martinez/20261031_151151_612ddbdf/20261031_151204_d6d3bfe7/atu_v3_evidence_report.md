# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Adriana Martinez_1793439783`  
**Timestamp:** `2026-10-31T15:13:03.015501`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-adriana-martinez\20261031_151151_612ddbdf\20261031_151204_d6d3bfe7\trial_1` (Trial #1)  
**Total Compute Duration:** `59.0s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (2/2 eligible targets; 2 requested)
- **Requested Suppression Target:** `100.0%` of eligible targets
- **Final Avg Log-Probability:** `-6.9272`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-3.6301`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `50.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0148` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Retain Answer Quality:** Original mean ROUGE-L `0.9`; selected `0.9`; relative decline `0.0` (limit `0.02`); `3` fixed answers, `48` token cap; passed `True`. This is a sampled answer-overlap metric, not all knowledge.
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0148 | 100.0% | YES | **0.7264** |
