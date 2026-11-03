# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Giorgi Meladze_1793116611`  
**Timestamp:** `2026-10-27T21:26:51.659669`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\feedback_validation_20261027\runs\tofu-giorgi-meladze\v3\20261027_211142_349ee465\checkpoints\20261027_211142_0d7c8139\trial_3` (Trial #3)  
**Total Compute Duration:** `909.5s` across `3` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `0.0%` (0/5 eligible targets; 5 requested)
- **Requested Suppression Target:** `100.0%` of eligible targets
- **Final Avg Log-Probability:** `-1.6375`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `1.4906`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `60.0%`
- **Active Probes Tested:** `10`
- **Stubborn Targets Remaining:** `5`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0005` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Retain Answer Quality:** Original mean ROUGE-L `0.9921344537815127`; selected `0.9921344537815127`; relative decline `0.0` (limit `0.02`); `25` fixed answers, `48` token cap; passed `True`. This is a sampled answer-overlap metric, not all knowledge.
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 | `atu_npo` | 0.0% | 0.0000 | 100.0% | YES | **0.3500** |
| #2 | `graddiff` | 0.0% | 0.0000 | 100.0% | YES | **0.3500** |
| #3 ⭐ (Winner) | `rmu` | 0.0% | 0.0005 | 100.0% | YES | **0.3857** |
