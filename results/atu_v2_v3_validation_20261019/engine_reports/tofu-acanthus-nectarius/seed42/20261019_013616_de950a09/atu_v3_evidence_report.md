# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Acanthus Nectarius_1792354220`  
**Timestamp:** `2026-10-19T01:40:20.664853`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-acanthus-nectarius\seed42\v3\20261019_013616_de950a09\trial_1` (Trial #1)  
**Total Compute Duration:** `244.16s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `20.0%` (4/20 targets)
- **Final Avg Log-Probability:** `-1.7796`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `1.3831`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `50.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `16`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0158` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 20.0% | 0.0158 | 100.0% | YES | **0.3581** |
| #2 | `atu_npo` | 10.0% | 0.0057 | 100.0% | YES | **0.3976** |
