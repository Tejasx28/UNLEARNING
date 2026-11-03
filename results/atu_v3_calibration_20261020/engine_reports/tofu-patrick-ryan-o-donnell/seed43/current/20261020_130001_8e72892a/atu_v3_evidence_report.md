# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Patrick Ryan O'Donnell_1792481683`  
**Timestamp:** `2026-10-20T13:04:43.019918`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-patrick-ryan-o-donnell\seed43\current\20261020_130001_8e72892a\trial_1` (Trial #1)  
**Total Compute Duration:** `281.96s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `95.0%` (19/20 targets)
- **Final Avg Log-Probability:** `-5.8102`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `-2.6475`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `1`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0027` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `dpo_refusal` | 95.0% | 0.0027 | 100.0% | YES | **0.8549** |
