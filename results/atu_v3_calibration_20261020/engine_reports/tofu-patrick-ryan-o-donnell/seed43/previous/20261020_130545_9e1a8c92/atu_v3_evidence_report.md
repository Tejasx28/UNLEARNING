# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Patrick Ryan O'Donnell_1792482070`  
**Timestamp:** `2026-10-20T13:11:10.388386`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v3_calibration_20261020\checkpoints\tofu-patrick-ryan-o-donnell\seed43\previous\20261020_130545_9e1a8c92\trial_1` (Trial #1)  
**Total Compute Duration:** `324.44s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `25.0%` (5/20 targets)
- **Final Avg Log-Probability:** `-2.7232`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `0.4394`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `62.5%`
- **Active Probes Tested:** `8`
- **Stubborn Targets Remaining:** `15`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0086` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 25.0% | 0.0086 | 100.0% | YES | **0.4286** |
| #2 | `rmu` | 0.0% | 0.0000 | 100.0% | YES | **0.3500** |
