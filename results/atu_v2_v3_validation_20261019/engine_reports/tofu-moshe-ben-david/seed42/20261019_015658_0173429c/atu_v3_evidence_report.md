# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Moshe Ben-David_1792355413`  
**Timestamp:** `2026-10-19T02:00:13.714333`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-moshe-ben-david\seed42\v3\20261019_015658_0173429c\trial_1` (Trial #1)  
**Total Compute Duration:** `194.88s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (20/20 targets)
- **Final Avg Log-Probability:** `-5.6688`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `-2.5061`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0279` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0279 | 100.0% | YES | **0.6679** |
