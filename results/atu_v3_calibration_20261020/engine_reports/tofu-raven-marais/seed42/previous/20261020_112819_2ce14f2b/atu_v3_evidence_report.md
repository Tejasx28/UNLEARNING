# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Raven Marais_1792476361`  
**Timestamp:** `2026-10-20T11:36:01.641150`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-raven-marais\seed42\previous\20261020_112819_2ce14f2b\trial_1` (Trial #1)  
**Total Compute Duration:** `461.66s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `20.0%` (4/20 targets)
- **Final Avg Log-Probability:** `-2.0586`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `1.1041`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `62.5%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `16`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0225` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 20.0% | 0.0225 | 100.0% | YES | **0.2903** |
| #2 | `atu_npo` | 0.0% | 0.0037 | 100.0% | YES | **0.3444** |
