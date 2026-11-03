# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Nikolai Abilov_1792353822`  
**Timestamp:** `2026-10-19T01:33:42.249277`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-nikolai-abilov\seed44\v3\20261019_012944_f3f57398\trial_1` (Trial #1)  
**Total Compute Duration:** `237.59s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `75.0%` (15/20 targets)
- **Final Avg Log-Probability:** `-4.0457`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `-0.8831`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `5`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0207` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 75.0% | 0.0207 | 100.0% | YES | **0.6150** |
| #2 | `rmu` | 0.0% | 0.0100 | 100.0% | YES | **0.2666** |
