# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Raven Marais_1793159547`  
**Timestamp:** `2026-10-28T09:22:27.456469`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-raven-marais\20261028_084546_bfa18a92\20261028_084801_1e7ecc8d\trial_2` (Trial #2)  
**Total Compute Duration:** `2065.56s` across `3` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `60.0%` (3/5 eligible targets; 5 requested)
- **Requested Suppression Target:** `100.0%` of eligible targets
- **Final Avg Log-Probability:** `-4.1656`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-0.4313`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `60.0%`
- **Active Probes Tested:** `10`
- **Stubborn Targets Remaining:** `2`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0048` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Retain Answer Quality:** Original mean ROUGE-L `0.988`; selected `0.9704957264957266`; relative decline `0.017716876016471067` (limit `0.02`); `25` fixed answers, `96` token cap; passed `True`. This is a sampled answer-overlap metric, not all knowledge.
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 | `atu_npo` | 0.0% | 0.0000 | 100.0% | YES | **0.3500** |
| #2 ⭐ (Winner) | `graddiff` | 60.0% | 0.0048 | 100.0% | YES | **0.6201** |
| #3 | `rmu` | 0.0% | 0.0100 | 100.0% | YES | **0.2871** |
