# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Ricardo Gabriel Sandoval_1792479827`  
**Timestamp:** `2026-10-20T12:33:47.358040`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-ricardo-gabriel-sandoval\seed43\previous\20261020_122649_c841b311\trial_1` (Trial #1)  
**Total Compute Duration:** `417.65s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `5.0%` (1/20 targets)
- **Final Avg Log-Probability:** `-1.5979`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `1.5647`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `75.0%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `19`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0265` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 5.0% | 0.0265 | 100.0% | YES | **0.1766** |
| #2 | `atu_npo` | 5.0% | 0.0225 | 100.0% | YES | **0.1854** |
