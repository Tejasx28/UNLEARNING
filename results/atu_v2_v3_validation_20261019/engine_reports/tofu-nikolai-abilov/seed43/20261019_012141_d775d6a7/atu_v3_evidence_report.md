# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Nikolai Abilov_1792353330`  
**Timestamp:** `2026-10-19T01:25:30.045418`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-nikolai-abilov\seed43\v3\20261019_012141_d775d6a7\trial_1` (Trial #1)  
**Total Compute Duration:** `228.9s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `70.0%` (14/20 targets)
- **Final Avg Log-Probability:** `-3.5672`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `-0.4045`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `6`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0204` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 70.0% | 0.0204 | 100.0% | YES | **0.5951** |
| #2 | `rmu` | 0.0% | 0.0106 | 100.0% | YES | **0.2613** |
