# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Adira Bintang_1793444190`  
**Timestamp:** `2026-10-31T16:26:30.809000`  
**Overall Verdict:** **SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-adira-bintang\20261031_162155_de8ee692\20261031_162210_e77c0f9c\trial_1` (Trial #1)  
**Total Compute Duration:** `260.4s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (1/1 eligible targets; 1 requested)
- **Requested Suppression Target:** `100.0%` of eligible targets
- **Final Avg Log-Probability:** `-6.8716`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-3.3042`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0014` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Retain Answer Quality:** Original mean ROUGE-L `0.988`; selected `0.988`; relative decline `0.0` (limit `0.02`); `25` fixed answers, `96` token cap; passed `True`. This is a sampled answer-overlap metric, not all knowledge.
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0014 | 100.0% | YES | **0.8882** |
