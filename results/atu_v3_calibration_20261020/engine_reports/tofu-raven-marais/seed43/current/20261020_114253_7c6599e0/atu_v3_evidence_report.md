# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Raven Marais_1792477131`  
**Timestamp:** `2026-10-20T11:48:51.924593`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-raven-marais\seed43\current\20261020_114253_7c6599e0\trial_1` (Trial #1)  
**Total Compute Duration:** `358.64s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `5.0%` (1/20 targets)
- **Final Avg Log-Probability:** `-2.0586`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `1.1041`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `19`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0278` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `dpo_refusal` | 5.0% | 0.0278 | 100.0% | YES | **0.2411** |
| #2 | `atu_npo` | 0.0% | 0.0000 | 100.0% | YES | **0.3750** |
