# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Moshe Ben-David_1792355627`  
**Timestamp:** `2026-10-19T02:03:47.201379`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-moshe-ben-david\seed43\v3\20261019_020013_75ad84a5\trial_2` (Trial #2)  
**Total Compute Duration:** `213.4s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `5.0%` (1/20 targets)
- **Final Avg Log-Probability:** `-1.6469`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `1.5158`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `50.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `19`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0215` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 | `atu_npo` | 0.0% | 0.0255 | 100.0% | YES | **0.1377** |
| #2 ⭐ (Winner) | `atu_npo` | 5.0% | 0.0215 | 100.0% | YES | **0.2433** |
