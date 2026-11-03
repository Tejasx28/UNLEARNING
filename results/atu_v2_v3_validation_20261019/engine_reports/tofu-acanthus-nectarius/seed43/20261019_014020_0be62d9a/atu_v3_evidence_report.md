# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Acanthus Nectarius_1792354419`  
**Timestamp:** `2026-10-19T01:43:39.255637`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-acanthus-nectarius\seed43\v3\20261019_014020_0be62d9a\trial_1` (Trial #1)  
**Total Compute Duration:** `198.5s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `50.0%` (10/20 targets)
- **Final Avg Log-Probability:** `-3.0748`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `0.0878`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `50.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `10`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0275` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 50.0% | 0.0275 | 100.0% | YES | **0.3959** |
| #2 | `rmu` | 0.0% | 0.0097 | 100.0% | YES | **0.2691** |
