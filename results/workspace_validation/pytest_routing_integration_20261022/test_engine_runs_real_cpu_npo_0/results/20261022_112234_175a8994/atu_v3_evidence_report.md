# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_custom_1792648354`  
**Timestamp:** `2026-10-22T11:22:34.578077`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\workspace_validation\pytest_routing_integration_20261022\test_engine_runs_real_cpu_npo_0\checkpoints\20261022_112234_175a8994\trial_1` (Trial #1)  
**Total Compute Duration:** `0.16s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `0.0%` (0/1 eligible targets; 1 requested)
- **Final Avg Log-Probability:** `-3.4658`
- **Likelihood Reference:** `legacy_global_floor`
- **Legacy Global Floor (reference only):** `-10.2532`
- **Distance to Floor:** `6.7875`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `1`
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
| #1 ⭐ (Winner) | `atu_npo` | 0.0% | 0.0000 | 100.0% | YES | **0.4500** |
