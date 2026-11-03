# ATU v3 Unlearning Evidence Audit Report

**Request ID:** `atu_v3_custom_1792649727`  
**Timestamp:** `2026-10-22T11:45:27.825186`  
**Overall Verdict:** **SUCCESS**  
**Selected Best Checkpoint:** `C:\Users\tejas\OneDrive\Documents\UNLEARNING\results\workspace_validation\pytest_debug_final_safeguards\test_final_test_is_only_evalua0\checkpoints\20261022_114527_cebc4cb6\trial_1` (Trial #1)  
**Total Compute Duration:** `0.31s` across `2` trial(s)

---

## 1. What Was Forgotten
- **Suppression Rate:** `100.0%` (1/1 eligible targets; 1 requested)
- **Final Avg Log-Probability:** `-4.0`
- **Likelihood Reference:** `legacy_global_floor`
- **Legacy Global Floor (reference only):** `-3.1627`
- **Distance to Floor:** `-1.0`

## 2. What Remains Recoverable
- **Adversarial Probe Leak Rate:** `0.0%`
- **Active Probes Tested:** `0`
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
| #2 | `graddiff` | 100.0% | 0.0000 | 100.0% | YES | **0.9000** |
