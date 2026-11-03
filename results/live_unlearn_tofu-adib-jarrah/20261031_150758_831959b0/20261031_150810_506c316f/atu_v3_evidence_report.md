# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Adib Jarrah_1793439547`  
**Timestamp:** `2026-10-31T15:09:07.873276`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-adib-jarrah\20261031_150758_831959b0\20261031_150810_506c316f\trial_1` (Trial #1)  
**Total Compute Duration:** `57.5s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (1/1 eligible targets; 1 requested)
- **Requested Suppression Target:** `100.0%` of eligible targets
- **Final Avg Log-Probability:** `-14.0238`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-10.7644`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `100.0%`
- **Active Probes Tested:** `1`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0099` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Retain Answer Quality:** Original mean ROUGE-L `0.9`; selected `0.9`; relative decline `0.0` (limit `0.02`); `3` fixed answers, `48` token cap; passed `True`. This is a sampled answer-overlap metric, not all knowledge.
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0099 | 100.0% | YES | **0.7179** |
