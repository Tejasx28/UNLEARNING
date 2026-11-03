# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Acanthus Nectarius_1792355020`  
**Timestamp:** `2026-10-19T01:53:40.891450`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-acanthus-nectarius\seed44\v3\20261019_014930_60862ca2\trial_1` (Trial #1)  
**Total Compute Duration:** `250.44s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `10.0%` (2/20 targets)
- **Final Avg Log-Probability:** `-1.7891`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `1.3735`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `50.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `18`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0142` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 10.0% | 0.0142 | 100.0% | YES | **0.3263** |
| #2 | `atu_npo` | 0.0% | 0.0068 | 100.0% | YES | **0.3435** |
