# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Moshe Ben-David_1792356048`  
**Timestamp:** `2026-10-19T02:10:48.445250`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-moshe-ben-david\seed44\v3\20261019_020723_12f1de75\trial_1` (Trial #1)  
**Total Compute Duration:** `204.52s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (20/20 targets)
- **Final Avg Log-Probability:** `-5.5492`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `-2.3866`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `50.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.019` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0190 | 100.0% | YES | **0.6918** |
| #2 | `rmu` | 0.0% | 0.0080 | 100.0% | YES | **0.2837** |
