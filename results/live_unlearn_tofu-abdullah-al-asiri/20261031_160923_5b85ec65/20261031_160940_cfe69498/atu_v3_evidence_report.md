# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Abdullah Al-Asiri_1793443430`  
**Timestamp:** `2026-10-31T16:13:50.656552`  
**Overall Verdict:** **SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-abdullah-al-asiri\20261031_160923_5b85ec65\20261031_160940_cfe69498\trial_1` (Trial #1)  
**Total Compute Duration:** `250.57s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (1/1 eligible targets; 1 requested)
- **Requested Suppression Target:** `100.0%` of eligible targets
- **Final Avg Log-Probability:** `-9.9836`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-6.3895`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Retain Answer Quality:** Original mean ROUGE-L `0.988`; selected `0.9785882352941176`; relative decline `0.009526077637532734` (limit `0.02`); `25` fixed answers, `96` token cap; passed `True`. This is a sampled answer-overlap metric, not all knowledge.
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0000 | 100.0% | YES | **0.9000** |
