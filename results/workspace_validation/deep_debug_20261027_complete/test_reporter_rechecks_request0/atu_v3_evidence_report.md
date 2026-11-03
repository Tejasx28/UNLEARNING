# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_custom_1793073600`  
**Timestamp:** `2026-10-27T09:30:00.425422`  
**Overall Verdict:** **PARTIAL_SUCCESS**  
**Selected Best Checkpoint:** `unused` (Trial #1)  
**Total Compute Duration:** `1.0s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `80.0%` (4/5 eligible targets; 5 requested)
- **Requested Suppression Target:** `100.0%` of eligible targets
- **Final Avg Log-Probability:** `-4.0`
- **Likelihood Reference:** `legacy_global_floor`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-1.0`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `0`
- **Stubborn Targets Remaining:** `1`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 80.0% | 0.0000 | 100.0% | YES | **0.9000** |
