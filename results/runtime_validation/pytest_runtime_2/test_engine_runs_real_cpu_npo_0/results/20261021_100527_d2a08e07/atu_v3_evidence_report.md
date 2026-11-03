# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_custom_1792557327`  
**Timestamp:** `2026-10-21T10:05:27.573676`  
**Overall Verdict:** **UNVERIFIED**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\runtime_validation\pytest_runtime_2\test_engine_runs_real_cpu_npo_0\checkpoints\20261021_100527_d2a08e07\trial_1` (Trial #1)  
**Total Compute Duration:** `0.12s` across `1` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `0.0%` (0/1 eligible targets; 1 requested)
- **Final Avg Log-Probability:** `-3.4658`
- **Likelihood Reference:** `legacy_global_floor`
- **Legacy Global Floor (reference only):** `-10.2532`
- **Distance to Floor:** `6.7875`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `100.0%`
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
| #1 ⭐ (Winner) | `atu_npo` | 0.0% | 0.0000 | 100.0% | YES | **0.3500** |
