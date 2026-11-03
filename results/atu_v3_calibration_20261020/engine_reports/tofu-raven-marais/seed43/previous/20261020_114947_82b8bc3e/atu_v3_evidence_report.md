# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Raven Marais_1792477521`  
**Timestamp:** `2026-10-20T11:55:21.962931`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-raven-marais\seed43\previous\20261020_114947_82b8bc3e\trial_1` (Trial #1)  
**Total Compute Duration:** `334.1s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `65.0%` (13/20 targets)
- **Final Avg Log-Probability:** `-4.65`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `-1.4874`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `25.0%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `7`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0053` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 65.0% | 0.0053 | 100.0% | YES | **0.6737** |
| #2 | `rmu` | 0.0% | 0.0000 | 100.0% | YES | **0.3750** |
