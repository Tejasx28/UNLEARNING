# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Nikolai Abilov_1792353101`  
**Timestamp:** `2026-10-19T01:21:41.058281`  
**Overall Verdict:** **SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-nikolai-abilov\seed42\v3\20261019_011838_d2315390\trial_1` (Trial #1)  
**Total Compute Duration:** `182.17s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `80.0%` (16/20 targets)
- **Final Avg Log-Probability:** `-3.8863`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `-0.7237`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `4`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0234` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 80.0% | 0.0234 | 100.0% | YES | **0.6150** |
