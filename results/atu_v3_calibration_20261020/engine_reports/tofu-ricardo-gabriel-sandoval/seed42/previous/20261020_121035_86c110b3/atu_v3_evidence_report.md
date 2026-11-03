# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Ricardo Gabriel Sandoval_1792478738`  
**Timestamp:** `2026-10-20T12:15:38.306785`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-ricardo-gabriel-sandoval\seed42\previous\20261020_121035_86c110b3\trial_1` (Trial #1)  
**Total Compute Duration:** `302.44s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `70.0%` (14/20 targets)
- **Final Avg Log-Probability:** `-4.3312`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `-1.1686`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `87.5%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `6`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0212` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 70.0% | 0.0212 | 100.0% | YES | **0.5005** |
| #2 | `rmu` | 0.0% | 0.0000 | 100.0% | YES | **0.3500** |
