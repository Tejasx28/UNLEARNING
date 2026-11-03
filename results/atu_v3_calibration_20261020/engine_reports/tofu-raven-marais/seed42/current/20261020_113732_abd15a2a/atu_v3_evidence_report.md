# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Raven Marais_1792476717`  
**Timestamp:** `2026-10-20T11:41:57.774628`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-raven-marais\seed42\current\20261020_113732_abd15a2a\trial_1` (Trial #1)  
**Total Compute Duration:** `265.63s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `20.0%` (4/20 targets)
- **Final Avg Log-Probability:** `-2.9496`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `0.213`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `16`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0255` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `dpo_refusal` | 20.0% | 0.0255 | 100.0% | YES | **0.3278** |
