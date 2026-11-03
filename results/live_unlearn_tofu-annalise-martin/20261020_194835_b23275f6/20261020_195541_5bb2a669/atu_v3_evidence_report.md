# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Annalise Martin_1792507587`  
**Timestamp:** `2026-10-20T20:16:27.683959`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\checkpoints\live_unlearn_tofu-annalise-martin\20261020_194835_b23275f6\20261020_195541_5bb2a669\trial_1` (Trial #1)  
**Total Compute Duration:** `1246.54s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `55.0%` (11/20 eligible targets; 20 requested)
- **Final Avg Log-Probability:** `-3.1904`
- **Likelihood Reference:** `per_answer_untuned_base`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-0.3482`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `62.5%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `9`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0059` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 55.0% | 0.0059 | 100.0% | YES | **0.5857** |
