# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_custom_1792566117`  
**Timestamp:** `2026-10-21T12:31:57.413699`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\workspace_validation\pytest_final\test_balanced_engine_executes_0\models\20261021_123157_d3b420dd\trial_1` (Trial #1)  
**Total Compute Duration:** `0.19s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (1/1 eligible targets; 1 requested)
- **Final Avg Log-Probability:** `-3.4657`
- **Likelihood Reference:** `legacy_global_floor`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-0.3031`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `1`
- **Stubborn Targets Remaining:** `0`

## 3. Affected Capabilities & Quality
- **Retain Log-Prob Drop:** `0.0` (Limit: `<= 0.03`)
- **Retain Utility Preserved:** `YES`
- **Fluency & Coherence Score:** `100.0%`
- **Capability Status:** `PASSED_CONFIGURED_CHECKS`

---

## Trials Comparison Matrix
| Trial | Method | Forget Suppressed | Retain Drop | Fluency | Safe? | Composite Score |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| #1 ⭐ (Winner) | `atu_npo` | 100.0% | 0.0000 | 100.0% | YES | **0.9000** |
