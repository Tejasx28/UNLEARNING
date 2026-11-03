# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_Basil Mahfouz Al-Kuwaiti_1792352675`  
**Timestamp:** `2026-10-19T01:14:35.465838`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\atu_v2_v3_validation_20261019\checkpoints\tofu-basil-mahfouz-al-kuwaiti\seed42\v3\20261019_011034_5d2bea08\trial_1` (Trial #1)  
**Total Compute Duration:** `240.92s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `5.0%` (1/20 targets)
- **Final Avg Log-Probability:** `-1.1962`
- **Calibrated Base Model Floor:** `-3.1627`
- **Distance to Floor:** `1.9664`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `50.0%`
- **Active Probes Tested:** `2`
- **Stubborn Targets Remaining:** `19`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0261` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PRESERVED`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 5.0% | 0.0261 | 100.0% | YES | **0.2054** |
| #2 | `atu_npo` | 0.0% | 0.0072 | 100.0% | YES | **0.3401** |
