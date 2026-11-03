# Seven presentation requirements and ten-paper literature plan

Prepared 24 October 2026. This is proposed slide content and a defense guide. It does not modify the PowerPoint or application. Exactly seven presentation requirements consolidate the larger implementation specification; their numbering is local to this presentation.

## Seven functional requirements for the PPT

Use two requirement slides if needed for readability: FR-01 through FR-04, then FR-05 through FR-07. Put the detailed code/test mapping in backup material.

| ID | Functional requirement | Description for the slide |
|---|---|---|
| FR-01 | Target Selection and Experiment Configuration | The system shall allow the researcher to select an author and specific facts, configure the experiment profile, method and training budget, and validate the request before execution. |
| FR-02 | Privacy Leakage Discovery | The system shall probe the original target model for the selected candidate facts, classify observed exposure, and display the prompts, generated responses and supporting evidence. |
| FR-03 | Adaptive Unlearning Execution | The system shall execute the selected method or use heuristic automatic planning, retry alternative methods when permitted, and record each attempt within configured training limits. |
| FR-04 | Retain Monitoring and Safe Stopping | The system shall periodically measure sampled unrelated knowledge against its original baseline, restore safe weights and stop an attempt when configured retain limits are exceeded. |
| FR-05 | Controlled Recovery Verification | The system shall evaluate the final model using recovery probes and original-target/base-model controls, reporting suppression, residual recovery and inconclusive checks separately. |
| FR-06 | Experiment Monitoring and Cancellation | The system shall show execution stages, progress, elapsed time and logs, allow cancellation, and distinguish completed, failed and stopped jobs. |
| FR-07 | Experiment Records and Reporting | The system shall preserve experiment history, display before-and-after evidence, compare saved runs, and export results with settings and checkpoint provenance. |

Implementation status: all seven correspond to existing source paths. Implementation does not guarantee that every scientific experiment succeeds. A particular saved run need not exercise every branch, such as retries or retain rollback.

## Code and demonstration map

### FR-01: Target Selection and Experiment Configuration

- Demonstration: open New experiment, search an author, clear the default fact selection and select one fact. Change Quick/Full, method and budget. Show the disabled launch with an empty selection and the selected settings before submitting.
- Frontend: `frontend/app/src/components/StudioWorkspace.tsx:35` (`LiveWorkspace`), `TargetPicker.tsx` (`DatasetAuthorPanel`), `ExperimentControls.tsx:21` (`launchOptions`).
- Backend: `src/live_requests.py:16` (`validate_options`), `:66` (`select_fact_indices`), `:78` (`normalize_launch`). The live runner uses selected original indices at `src/orchestrator/live_runner.py:228` onward.
- Test evidence: `tests/test_live_workspace.py:17` and `:30`, `tests/test_routing_budget_regressions.py:31` and `:49`.
- Explain: selections scope the experiment. The visible QA answers come from TOFU; they do not prove model recall. Quick accepts 1–5 facts, Full 1–20.

### FR-02: Privacy Leakage Discovery

- Demonstration: open the saved Anaya Full result, Privacy discovery. Expand the award finding, switch the saved probe and expand its classification explanation. Show the model response separately from the reference value.
- Frontend: `frontend/app/src/components/PrivacyDiscovery.tsx:9` (`PrivacyDiscovery`) and `:27` (`DiscoveryFinding`).
- Backend: `src/discovery/engine.py:49` (`discover_leakage`), `:122` (`_execute_probe`), `:167` (`_aggregate_fact_evidence`).
- Test evidence: `tests/test_discovery.py:110`, `:172`, `:196`, `:212`.
- Explain: this discovers observed exposure among selected candidate facts. It does not enumerate every secret in model memory. The scorer is deterministic and heuristic.

### FR-03: Adaptive Unlearning Execution

- Demonstration: show Manual and Automatic settings. In an actual saved run, open Attempts and Run details to show the executed method, selection rationale, real optimizer updates and budget. Use code/tests for branches absent from that run.
- Planning: `src/atu/v3/analyzer.py:15` (`RequestAnalyzer.analyze`). Manual selection takes precedence over routing; automatic routing uses priority and budget rules.
- Execution: `src/atu/v3/budget_engine.py:81` (`run_budget_loop`), `:288` (`_execute_method`), `:367` (`_adapt_strategy`). Each trial reloads the original target adapter. Inner adaptive NPO state/weights are in `src/atu/controller.py` and `src/atu/trainer.py`.
- Test evidence: `tests/test_routing_budget_regressions.py:152` (manual once), `:96` and `:139` (shared budget), `tests/test_v3_integration.py:220` (fresh retry). The fresh-retry test mocks method execution and evaluation to verify orchestration. These controlled tests are not GPU benchmark results.
- Explain: Balanced automatic starts with ATU-NPO. Quick has one attempt; Full permits up to three automatic attempts by default. Manual runs one chosen method. A training allowance is not total elapsed time. Current routing is not a learned semantic best-method predictor.

### FR-04: Retain Monitoring and Safe Stopping

- Demonstration: show Retain safety settings, the saved result's retain overlap and Attempts diagnostics. Then show the guard code and controlled rollback test. The saved Anaya result did not trigger rollback.
- Backend: `src/atu/v3/safety.py:45` (`RetainGuard.__call__`), `:80` (`_individual_drop`), `:89` (`_safe`), with update-hook integration and execution diagnostics in `src/atu/v3/budget_engine.py`.
- Test evidence: `tests/test_v3_integration.py:144` (restore last safe state on a small synthetic model with controlled utility readings), `tests/test_v3_specificity.py:15` (individual damage hidden by average), `tests/test_training_update_regressions.py:155` (unsafe changes still trigger rollback).
- Explain: training uses average/individual likelihood guard limits. The result's retain answer overlap is a different measurement on a limited generated-answer sample. Current retain cohorts exclude the target author, so this does not establish preservation of that author's unselected facts.

### FR-05: Controlled Recovery Verification

- Demonstration: open Recovery tests and Inspect controls. Compare the same prompt on original target, untuned base and selected unlearned checkpoint. Show a suppressed example and a residual/inconclusive example from another saved record.
- Backend: `src/orchestrator/live_runner.py:760` onward pairs original/base/unlearned responses. The conditional around `:784` requires original-target recovery and a clean base control. Summary counts follow at `:814`. `final_audit_status` begins at `:61`.
- Separate final test after selection: `src/atu/v3/engine.py:134` onward. Quick has the calibrated live audit; Full adds the engine's held-out test.
- Test evidence: `tests/test_v3_integration.py:299` (final test after search), `tests/test_live_pipeline_regressions.py:19` (selected-fact probe coverage), `:59` (final outcome requires coverage).
- Explain: an inconclusive control does not count as successful suppression. Missing recovery in tested prompts is not proof of complete deletion or factual answer quality. The untuned base is not a retain-only retrained gold standard.

### FR-06: Experiment Monitoring and Cancellation

- Demonstration: use the real job monitor during an optional genuine run, or show an explicitly identified UI test fixture for the stop/failure path. Show stage, log, elapsed time and Stop experiment. Do not launch an expensive GPU job solely to exercise an error path during a short presentation.
- Frontend: `frontend/app/src/components/LiveExecutionModal.tsx:10`, `frontend/app/src/hooks/useLiveJob.ts`, `frontend/app/src/services/pipeline.ts:64` and `:76`.
- Backend: `src/live_jobs.py:83` (`launch`), `:191` (`cancel`), `:231` (`status`). Cancellation holds the GPU slot until the owned worker exits.
- Test evidence: `tests/test_live_workspace.py:85` (cancellation and GPU slot), `:101` (failed execution), `:179` (discovery survives cancellation).
- Explain: 100% means execution reached its terminal point. The scientific result is a separate status. A stopped run does not claim completed unlearning.

### FR-07: Experiment Records and Reporting

- Demonstration: open Run history, load a saved result, switch its response selector, compare two saved runs and export the complete JSON. Explain mismatch notices if facts, profiles or coverage differ.
- Frontend: `frontend/app/src/components/LiveResults.tsx:15`, `StudioWorkspace.tsx:56` (`StudioHistory`), `RunComparison.tsx:12`, `frontend/app/src/services/research.ts:91` (`downloadJson`).
- Backend: `src/live_jobs.py:68` (`_save`), `:245` (`history`), `src/atu/v3/reporter.py:29` (`compile_report`).
- Test evidence: `tests/test_live_workspace.py:67`, `tests/test_atu_v3.py:154`, `frontend/scripts/pipeline.test.mjs` for comparison, history and export payload behavior.
- Explain: the provenance identifies how the run was produced. Different saved settings yield descriptive comparisons, not a controlled claim that one algorithm is superior.

## Saved evidence to keep ready

The Anaya Full run `job_1792649059798_c1cde415` demonstrates selected-fact input, discovery, genuine optimization, retain measurement and final controlled reporting. It used manual ATU-NPO, recorded 3 updates, 2/2 calibrated suppressed checks, 1/1 selected-fact coverage and 98.8% retain answer overlap on 25 examples. It had one attempt and `rolled_back=false`; it cannot demonstrate that automatic fallback or rollback occurred.

The Bezabih Quick run `job_1792671478177_b31f93f1` records 3/5 validated checks suppressed, 2 residual checks, 1 inconclusive check and 4/5 fact coverage. It used one automatic ATU-NPO attempt and `rolled_back=false`. Use it to show honest partial outcomes rather than as evidence of a fallback.

For retries and rollback, show the implementation and focused controlled tests. Clearly identify test fixtures. If the panel requires a genuine GPU example of either branch, produce and inspect that record before claiming it as a live scientific demonstration.

## Ten research papers

Keep ten paper slots. The strongest simple revision replaces three indirect vision studies with foundations used by the actual implementation.

| Final slot | Paper | Connection and how to position it |
|---|---|---|
|1|[TOFU: A Task of Fictitious Unlearning for LLMs](https://arxiv.org/abs/2401.06121)|Direct foundation for fictional-author data, forget/retain evaluation and the benchmark.|
|2|[Negative Preference Optimization: From Catastrophic Collapse to Effective Unlearning](https://arxiv.org/abs/2404.05868)|Direct objective foundation for fixed NPO and ATU-NPO. The controller is the project's addition around that existing loss.|
|3|[The WMDP Benchmark: Measuring and Reducing Malicious Use with Unlearning](https://proceedings.mlr.press/v235/li24bc.html)|Introduces RMU, which is an implemented candidate. The current project does not evaluate on WMDP.|
|4|[Robust Privacy Unlearning for LLM Services via Adversarially Augmented Preference Optimization](https://ieeexplore.ieee.org/abstract/document/11670112/)|Closely related TOFU/preference/adversarial-probe work. Distinguish its augmentation from ATU's controller and bounded orchestration.|
|5|[Proof of Unlearning for Semantic Knowledge Bases in Large Language Models-Enabled Semantic Communication](https://ieeexplore.ieee.org/document/11397316/)|Relevant related work on LoRA and verifiability. ATU does not implement that proof framework.|
|6|[When Machine Unlearning Meets Retrieval-Augmented Generation: Keep Secret or Forget Knowledge?](https://arxiv.org/abs/2410.15267)|Alternative behavioral approach using retrieval. Useful to explain why the current adapter experiment is a different setting; RAG is not implemented.|
|7|[Learning to Unlearn While Retaining: Combating Gradient Conflicts in Machine Unlearning](https://openaccess.thecvf.com/content/ICCV2025/papers/Patel_Learning_to_Unlearn_while_Retaining_Combating_Gradient_Conflicts_in_Machine_ICCV_2025_paper.pdf)|Conceptual background on conflicting forget/retain updates. Its implicit regularizer is not implemented in ATU.|
|8|[ULTRA: A Standardized Certification Metric for Machine Unlearning](https://ieeexplore.ieee.org/abstract/document/11501543)|Motivation for multiple evaluation dimensions and failures hidden by averages. The project does not implement ULTRA or claim certification.|
|9|[Unrolling SGD: Understanding Factors Influencing Machine Unlearning](https://arxiv.org/abs/2109.13398)|Theoretical background for approximate unlearning and comparison to retraining. Current response tests do not establish retraining equivalence.|
|10|[Auditing Approximate Machine Unlearning for Differentially Private Models](https://arxiv.org/abs/2508.18671)|Indirect privacy-auditing background. Explain that differential privacy and membership-inference auditing remain outside the current implementation.|

Suggested replacements in the original deck: replace Dimensional Alignment, Fast Yet Effective Machine Unlearning and Boundary Unlearning. They are legitimate related research, but less directly connected to factual LLM unlearning in the implemented system. The retained DP auditing paper is also indirect; keep its role explicit rather than claiming its mechanisms are implemented.

Each paper slide should have: verified title/authors/year/venue, problem, method, limitation, and one precise connection to the project. A literature reference is not a functional requirement. Discussing RAG, proof systems, differential privacy or ULTRA does not mean the project implements them.

The current A²PO author list still needs a publisher PDF/BibTeX cross-check because the official ICWS program differs from the supplied slide. TOFU can safely be cited as its 2024 arXiv paper; do not invent an ICLR main-track venue. NPO is COLM 2024 and WMDP is ICML 2024.

## Optional additional project function

No new feature is required to support the seven requirements above. The most useful scientific addition would be a same-author collateral-effect check.

Example: the researcher targets an author's award. Before and after unlearning, the system also tests a small, fixed set of that author's unselected facts, such as genre or birthplace. Those audit facts must not enter forget training or feedback used to select a checkpoint. Only originally recovered facts can support a preservation comparison. If every available fact was selected, report this audit as not applicable because no unselected facts remain. Report paired responses and retained, lost or inconclusive counts separately from unrelated-author retain metrics.

This would help answer: “You removed the award, but did you also damage the author's other facts?” Current unrelated-author retain checks do not answer that question. It requires additional inference and evaluation integration, but no new unlearning objective or new dataset. Merely using a small audit sample would still not prove preservation of every unselected fact.

Until implemented and tested, label this as future work. If added later, expand FR-04/FR-05 rather than introduce an eighth requirement into this seven-requirement presentation.
