# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Ricardo Gabriel Sandoval_1792479355`  
**Timestamp:** `2026-10-20T12:25:55.789445`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-ricardo-gabriel-sandoval\seed43\current\20261020_122142_17fe4c3f\trial_1` (Trial #1)  
**Total Compute Duration:** `253.7s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `30.0%` (6/20 targets)
- **Final Avg Log-Probability:** `-2.9016`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `0.2611`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `14`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0064` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `dpo_refusal` | 30.0% | 0.0064 | 100.0% | YES | **0.5313** |
