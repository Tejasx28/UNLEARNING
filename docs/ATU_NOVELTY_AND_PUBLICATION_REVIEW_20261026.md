# ATU: novelty, publication readiness and implementation evidence

Reviewed 26 October 2026 against current source, saved checkpoints and raw results, current software checks and targeted primary-source literature. The literature search is not an exhaustive priority certificate.

## Verdict

ATU is a substantial implemented engineering system. Its present evidence does **not** establish a new unlearning objective, the first adaptive unlearning method, or a generally superior algorithm. The useful current contribution is the combination of candidate exposure discovery, generated-recovery feedback, method-specific execution, fresh retries under shared limits, retain restoration, safety-filtered ranking and traceable evaluation.

A paper can be written about this work. A credible systems/demo or carefully scoped empirical paper is plausible, subject to the chosen venue's contribution and evaluation requirements. A competitive new-method claim needs a precisely differentiated mechanism and a controlled study. Neither a polished presentation nor feature count establishes publishability or guarantees acceptance.

## What is implemented, and what is not established

| Component | Evidence in the project | Defensible interpretation |
|---|---|---|
| Request planning | `src/atu/v3/analyzer.py`, `policy.py` | Manual override and fixed priority/time rules. The router is not a trained predictor of the best method for a fact type. |
| Inner ATU-NPO controller | `src/atu/controller.py`, `src/atu/trainer.py` | Likelihood/floor and DEV recovery signals adjust sample weights. Other candidates do not all use NPO. |
| Outer adaptive trials | `src/atu/v3/budget_engine.py` | Fresh original-target reloads, method/settings adaptation and shared limits are real. Their causal benefit over strong alternatives is not established by one switched run. |
| Retain protection | `src/atu/v3/safety.py` | Periodic sampled checks, backtracking/restoration and stopping. This is not a guarantee for every unrelated fact. |
| Checkpoint selection | `src/atu/v3/selector.py` | Safety filtering followed by lexicographic ranking. The class name does not imply a learned policy or an explicit Pareto-frontier optimizer. |
| Final verification | `src/atu/v3/engine.py`, `src/orchestrator/live_runner.py` | Separate Full final prompts and target/base controls. Quick remains preliminary screening. No irreversible-deletion or retraining-equivalence certificate. |
| Fact selectivity | `src/atu/v3/data.py` | The target author is excluded from retain cohorts. Preservation of that author's unselected facts is a current evaluation gap. |
| Model scope | 65 saved adapter configurations | One Qwen2.5-1.5B-Instruct backbone with multiple real method/seed variants. |

## Why the broad novelty claim is weak

Several close prior works already study adaptive allocation, feedback control or automated unlearning search. The following comparisons are interpretations of the primary sources; they do not imply ATU implements their methods.

| Prior work | Overlap | What ATU must distinguish experimentally |
|---|---|---|
| [SimNPO](https://arxiv.org/abs/2410.07163), NeurIPS 2025 | Difficulty-dependent allocation of optimization pressure and NPO reference bias | Whether generated recovery feedback adds value beyond confidence/objective effects. |
| [GUARD](https://arxiv.org/abs/2506.10946), current preprint | Adaptive nonuniform weighting informed by forget/retain attribution | Whether ATU's likelihood/recovery rules provide a useful different signal. |
| [AdaPop](https://arxiv.org/abs/2608.14229), preprint 2026 | Per-fact pressure and feedback-controlled retain balancing | A distinct mechanism and its joint forgetting/utility benefit. |
| [RADNPO](https://arxiv.org/abs/2609.34251), preprint 2026 | State-aware forgetting strength | Value beyond another confidence-aware objective. |
| [EvoMU](https://arxiv.org/abs/2602.02139), preprint 2026 | Automated train/evaluate/select search under budgets | Benefit of ATU's particular portfolio/controller over fixed, random and simple ordered portfolios. |
| [Normalized gradient difference](https://aclanthology.org/2025.naacl-long.563/), NAACL 2025 | Adaptive optimization of forgetting and retention | ATU's plain GradDiff candidate is not a reproduction of this normalized optimizer. |
| [OpenUnlearning](https://arxiv.org/abs/2506.12618), framework preprint | Unified methods, metrics and reproducible evaluation | A dashboard and algorithm portfolio alone are insufficient differentiation. |
| [PTP-U](https://arxiv.org/abs/2610.11915), preprint 2026 | Utility drift and recovery under forgetting constraints | A specific measured preservation/selection insight. |

The earlier report `docs/ATU_RESEARCH_REPORT.md` should not be copied into a manuscript without correction. In particular, prior methods are not all static/uniform, ROUGE overlap is not a percentage of all knowledge preserved, and blanket prevention of catastrophic damage is unsupported. Only actual human authors and contributions should appear in a submission; follow the target venue's disclosure policy for tools used.

## What the empirical evidence says

The latest inspected Full adaptive case, `job_1792684950818_0c9b3a85`, genuinely executed ATU-NPO, GradDiff and RMU, including restoration/backtracking. It selected GradDiff. Its final calibrated audit suppressed **2/5** validated checks, left **3** residual recoveries, and had **1** additional inconclusive check. **4/5** selected facts had valid controls. This proves working orchestration and safety branches, not universal forgetting or general GradDiff superiority.

The focused Anaya case, `job_1792649059798_c1cde415`, suppressed **2/2** calibrated checks for **one** selected award fact. Its replacement award is fabricated. Target suppression and truthful answering must therefore be reported separately.

The frozen 20 October specificity study is important negative evidence: 57/64 calibrated responses were suppressed, but 0/6 adaptive cases passed its joint primary criteria. All selected adaptive checkpoints used refusal training. In the separate assisted audit, 19 full and one partial recovery occurred in 22 calibrated checks. These historical results do not validate the latest routing policy, and a paper must not hide them while advertising only the 89.1% suppression figure.

Sources: `results/live_jobs/job_1792684950818_0c9b3a85/result.json`, `results/live_jobs/job_1792649059798_c1cde415/result.json`, and `results/atu_v3_specificity_20261020/FINDINGS.md`.

## Three practical paper routes

### 1. Lowest new-training cost: an empirical audit

Use existing frozen checkpoints to measure the gap between apparent suppression and robust recoverability. A possible research question is: *How often do confidence/response-based success labels survive calibrated recovery, truthful-answer and same-author collateral checks?* This requires a new, reproducible insight beyond rediscovering known failure modes.

Validate the leak scorer on a blinded, human-labelled sample with aliases, partial matches, prompt-supplied facts and degenerate outputs. Report per-class precision/recall/F1 and disagreement. Add answer-free paraphrases, independently designed attack families and same-author checks; label prefix-assisted tests separately. Preserve original scores and identify any new rescoring as a separate analysis. Novelty must still be checked against audits such as [Dissecting Fine-Tuning Unlearning](https://aclanthology.org/2024.emnlp-main.228/) and OpenUnlearning.

### 2. Stronger controller study

Test the narrow hypothesis: *Generated-recovery feedback plus per-fact calibration improves joint forgetting/utility success per declared resource budget compared with confidence-only control.* This is a hypothesis, not a current result.

Compare strong fixed methods (including a relevant modern baseline such as SimNPO), the current fixed-order V3, random/simple portfolio order and the proposed policy. Ablate generated-recovery feedback, adaptive sample weights, per-fact calibration and backtracking separately. Tune on development requests and freeze the policy before final authors/probes. Count preparation, guard/evaluation cost, unsuccessful trials and safe restarts; do not equalize only retained updates while hiding discarded work.

### 3. Same-author selective preservation

Target selected facts while measuring and protecting other facts about the same author. The current retain construction leaves this unmeasured. A possible contribution combines curated same-author constraints with a specific new control/selection mechanism.

Check for target clauses inside retained answers, otherwise retain training can teach the secret back. Compare with a simple same-author-retain baseline using identical data; merely adding that data is not automatically a new method. Related collateral-damage work, including [PreUnlearn](https://arxiv.org/abs/2606.18473), must be considered before claiming originality.

## A staged path to submission

1. Choose **one** research question and draft its claim, closest competing method and falsification criterion.
2. Freeze code, target adapters, dataset/probe revisions, scoring and budgets. The current workspace is not a Git repository; preserve a reproducible snapshot/hashes before the next study.
3. Use a small development pilot to test whether the proposed signal/mechanism helps. Stop expanding a study if the pilot does not support the hypothesis.
4. Run a predeclared final study on multiple held-out authors and seeds. More than one backbone or dataset strengthens generalization claims, but a narrowly scoped single-backbone paper must state that scope. There is no universal experiment count that guarantees acceptance.
5. Report joint forgetting-and-utility success, raw responses, residual/inconclusive counts, same-author and cross-author preservation, output truthfulness, costs and uncertainty. Cluster analysis by independent author/request rather than treating correlated prompt templates as independent trials.
6. Include ablations, failed cases and comparison with the closest strong methods. Distinguish your controller's benefit from extra computation, different data or unequal optimizer settings.
7. Write a transparent systems/demo, empirical or methods manuscript matching the evidence and venue scope. Recheck current submission rules and related work before choosing a venue. Submission and acceptance are separate.

## Metric corrections needed for publication

`src/metrics.py::compute_truth_ratio` implements a mean sigmoid contrast between length-normalized true and perturbed-answer likelihoods. The presentation calls it the **project truth-preference proxy**, not canonical TOFU Truth Ratio or a retraining-based forgetting-quality test. Validate against the official benchmark protocol before claiming equivalence.

`exp(avg_log_probability)` is a geometric mean token-conditional probability, not the probability of the complete answer. The untuned base control is not a model retrained on retain-only data. ROUGE-L is sampled answer overlap, not proof that a corresponding fraction of all knowledge survived.

## Faculty review requirements and evidence

The user confirmed that unlearning-method variants satisfy the faculty's “2–3 models” requirement. The comparison therefore uses real saved GA, NPO, RMU and GradDiff adapters on the same Qwen backbone, and labels them as variants.

| Requirement | Evidence included | Boundary |
|---|---|---|
| Module pseudocode | Request/discovery, ATU-NPO weighting/retain guard, outer trial/selection/audit pseudocode | Explanatory pseudocode linked to actual modules. |
| Implementation screenshots | Real browser captures of settings/empty selection, discovery responses, trials and controls | Actual running UI; no generated mockups. |
| Functional demonstration | Author selection, explicit method behavior, input validation, saved history/results, trial and control views | No new GPU job launched during this review. |
| Workflow | ATU-only architecture and existing DFD/activity views | Inner ATU-NPO control is separate from outer V3 routing. |
| Actual working evidence | Saved run IDs, optimizer updates, kept/restored weights, raw responses and control labels | Real cases include partial/failure outcomes. |
| Model testing / 2–3 variants | Saved matched GA/NPO/RMU/GradDiff evaluations and existing checkpoint files | Historical GPU measurements, not newly rerun inference or three distinct LLM backbones. |
| Metrics and comparison | ROUGE-1/2/L, paraphrase overlap, per-token log-probability, custom preference proxy, train/evaluation time and VRAM; current calibrated recovery/utility | Complete raw metrics are linked. The historical table does not establish current V3 superiority. |
| UI/software testing | 230 unique backend cases, 22 frontend logic tests, TypeScript checking and real browser walkthrough | Backend counts combine initial pass and environment-specific rechecks. Full GPU/model/tokenizer suites were excluded. Mocked frontend tests are distinct from browser checks. |

Fresh test logs are in `frontend/presentations/build/implementation_review_20261026/testing/`. Initial Windows Temp atomic-rename errors and long-path failures passed after using suitable writable short test paths; no application-code fix was made. Real UI captures are in the sibling `screenshots/` folder. The test suite verifies implemented behavior; it does not establish scientific unlearning success across authors.

## Recommended decision

For the immediate review, present the implemented controller and honest empirical evidence, using the method-variant comparison accepted by faculty. For a paper, begin with the lower-cost audit of saved checkpoints, then invest in a new controller mechanism only if a carefully controlled development experiment identifies a reproducible benefit. Additional UI features or another standard unlearning algorithm alone will not establish research novelty.
