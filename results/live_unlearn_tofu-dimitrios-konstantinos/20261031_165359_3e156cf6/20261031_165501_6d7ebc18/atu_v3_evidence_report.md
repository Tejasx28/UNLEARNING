# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Dimitrios Konstantinos_1793446276`  
**Timestamp:** `2026-10-31T17:01:16.648281`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-dimitrios-konstantinos\20261031_165359_3e156cf6\20261031_165501_6d7ebc18\trial_1` (Trial #1)  
**Total Compute Duration:** `375.18s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (5/5 eligible targets; 5 requested)
- **Requested Suppression Target:** `100.0%` of eligible targets
- **Final Avg Log-Probability:** `-10.1613`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-5.6745`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `60.0%`
- **Active Probes Tested:** `5`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0038` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Retain Answer Quality:** Original mean ROUGE-L `0.9`; selected `0.9`; relative decline `0.0` (limit `0.02`); `3` fixed answers, `48` token cap; passed `True`. This is a sampled answer-overlap metric, not all knowledge.
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0038 | 100.0% | YES | **0.8081** |
