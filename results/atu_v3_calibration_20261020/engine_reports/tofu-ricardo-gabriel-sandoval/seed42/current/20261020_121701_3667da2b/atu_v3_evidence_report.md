# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Ricardo Gabriel Sandoval_1792479051`  
**Timestamp:** `2026-10-20T12:20:51.094100`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-ricardo-gabriel-sandoval\seed42\current\20261020_121701_3667da2b\trial_1` (Trial #1)  
**Total Compute Duration:** `229.12s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `5.0%` (1/20 targets)
- **Final Avg Log-Probability:** `-1.6641`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `1.4986`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `19`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0133` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `dpo_refusal` | 5.0% | 0.0133 | 100.0% | YES | **0.3614** |
