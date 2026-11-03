# Current presentation review and defense preparation

Reviewed 24 slides from `C:/Users/tejas/Downloads/Presentation2-Teju (1).pptx` on 24 October 2026. The original deck remains unchanged. Review included extracted slide text, rendered slide layouts, embedded diagrams, current implementation documentation, a source-code audit and primary literature checks. Renders are inspection aids, not an assertion of native PowerPoint rendering fidelity.

## Overall assessment

The deck provides an academic design-review structure, but it mostly explains the earlier ATU-NPO controller. A defense of the current implementation needs the outer ATU v3 workflow, measured results and clear evaluation boundaries. Ten individual literature slides occupy 42% of the deck, while the deck has no experiment-results section, limitations slide or clear concluding contribution. Existing institutional branding can remain.

The strongest contribution to explain is an experimental orchestration system around existing unlearning objectives: periodic feedback, heuristic routing, fresh retries within a shared budget, retain guards, safe checkpoint selection and inspection of recovery evidence. Broad claims of new loss functions, guaranteed deletion, a learned method recommender or superiority on every author are unsupported.

## Slide-by-slide decisions

| Current slide | Recommended revision |
|---|---|
| 1 Title | Keep the project title. Add a small subtitle identifying ATU v3 and the TOFU implementation. Make the title more prominent than administrative details while retaining required university branding. |
| 2 Abstract | Replace the 151-word paragraph with a short problem, approach, evaluation and scope summary. Use present tense for implemented features. Replace continuous monitoring with periodic configured checks. Describe automated fixed recovery probes rather than imply a comprehensive adaptive conversational attacker. |
| 3 Problem scenario | Use one concrete selected fact, such as an author's award. Explain the forgetting and preservation goals. Distinguish the desired goal from measured achievement. |
| 4 Purpose and scope | Specify TOFU, Qwen2.5-1.5B-Instruct, adapter updates, selected facts and local execution. State that current live evidence and older multi-seed studies concern different policy versions. |
| 5 Literature background | Replace the glossary with a comparison of the most relevant methods and their limitations. Remove the unsupported generalization that existing work mainly considers forgetting. Other papers already study retention, robustness and verification. |
| 6–15 Ten paper summaries | Condense the spoken literature section to one or two comparison slides when departmental requirements allow. Preserve the ten detailed papers in an appendix. Explain which idea the implementation uses, which is background and which is future work. Replace conversational wording such as “your project.” |
| 16 Tools | Correct FastAPI to Python HTTP/JSON server using `http.server`. Remove version guesses such as React18/19 and Vite5/6/7. Show the tested environment or omit unnecessary patch versions. Current local package metadata reports Python3.11.0, PyTorch2.6.0+cu124, Transformers5.18.0 and PEFT0.21.2. Frontend declares React19.2 and TypeScript5.9.3, with Vite7.x. |
| 17 Users | Rename to Intended users or combine with use cases. These audiences are not implemented authentication/access-control roles. The app currently supports a local researcher workflow. |
| 18 Functional requirements | Show candidate fact selection, discovery evidence, manual/automatic execution, periodic retain checks, calibrated final testing, history and export. Discovery tests supplied candidate facts. It does not enumerate all secrets in model memory. Selection occurs before the pipeline. |
| 19 Non-functional requirements | Replace broad assurances with observable behavior: one active GPU job, unique run records, interruption handling, configuration/provenance exports and separate execution/scientific statuses. Describe the training budget separately from total duration. |
| 20 Architecture | Replace the embedded ATU v2/NPO-only diagram with the current v3 system. Include the job server, discovery, outer method-selection loop, separate adapters, controls and saved evidence. Simplify the main diagram so it can be read from the back of the room. |
| 21 Process flow | Add manual versus automatic branching, a fresh original-target reload for a retry, a shared remaining budget, development evaluation, safety-constrained selection and final audit after selection. |
| 22 Pseudocode | Replace the 29-line main-slide code block with the outer v3 algorithm. Move weighted NPO details into backup. Correct the unsupported “Target knowledge fully eliminated” statement. |
| 23 References | Add the actual TOFU, NPO and RMU source papers. Split references over readable backup slides if needed. Resolve the A²PO author-list discrepancy against publisher BibTeX/PDF. |
| 24 Books/websites | Keep sources actually used. Reinforcement Learning: An Introduction is unnecessary unless the presentation explicitly uses it as background. ATU's controller is not a reinforcement-learning policy. Add a clear conclusion before references. |

## Corrections to the algorithm explanation

ATU has two levels of adaptation. The inner ATU-NPO controller changes per-example pressure based on likelihood progress and development recovery. The outer v3 engine selects among existing methods and manages attempts, guards and selection. Do not present all methods as if they use the same weighted NPO loss.

Current Balanced automatic requests begin with ATU-NPO. Other candidate methods include GradDiff, RMU, DPO refusal and gradient ascent. Priority and budget rules can change the starting method or settings. The analyzer does not learn that an award question is better handled by a particular objective. Full automatic runs allow up to three attempts, so they do not automatically test every method. Quick permits one attempt. Explicit method selection runs that chosen method once.

Each retry reloads the original target adapter. Retries do not continue from a failed method's modified weights. A single cooperative training-loop budget covers attempts. Model loading, preparation and final evaluation contribute additional elapsed time. An in-flight operation can cross a budget boundary.

Retain checks use an original-target baseline and inspect average and individual likelihood changes. If a configured guard fails, the implementation can reduce the most recent update interval through interpolation, restore safe weights and stop the attempt. Passing these limits does not prove that every unrelated fact remains intact.

Development feedback drives adaptation. The independent final evaluation follows checkpoint selection and must not supply feedback for selecting another trial. Fixed templates and shared facts still limit claims of generalization to new attack families.

The current slide22 inner-loop explanation also differs from the code:

- Development leakage takes priority over low canonical-answer likelihood.
- Default weights distinguish leaking1.8, stubborn1.4, suppressed0, and a progression weight between0.2 and1. These are configurable heuristics.
- A low likelihood or zero pressure means a configured training condition passed. It does not establish complete deletion.
- A safety breach requires describing safe-state handling, not merely breaking and returning the current weights.

### Suggested main-slide pseudocode

```text
Validate selected facts, profile, method, budget and retain settings
Measure original-model exposure and prepare controls
Build method candidates using explicit choice or heuristic rules
For each allowed candidate while budget remains:
    Reload the original target adapter
    Train with periodic feedback and retain guards
    Record development evidence, actual updates and checkpoint safety
    Stop retries when configured development criteria pass
Select an eligible safe checkpoint, or fail explicitly
Audit the selected checkpoint with separate final prompts and controls
Report suppression, residual recovery, uncertainty and utility coverage
```

This is explanatory pseudocode, not a claim that every method has identical internal training behavior.

## Evidence that should appear in the revised deck

Use one Full example and one partial result. Keep request scopes visible. Neither is an equal-condition method comparison.

| Measurement | Anaya Full example | Bezabih Quick example |
|---|---|---|
| Saved run | `job_1792649059798_c1cde415` | `job_1792671478177_b31f93f1` |
| Selected facts | 1 award fact | 5 facts |
| Validated suppression | 2/2 checks | 3/5 checks |
| Residual recovery | 0 | 2 |
| Inconclusive checks | 0 | 1 |
| Fact-level validated coverage | 1/1 | 4/5 |
| Retain answer overlap | 98.8% on25 examples | 90.0% on3 examples |
| Total elapsed duration | 8m2s | 7m53s |

In the Full example, the after-response invents another award. The target award is no longer recovered in the tested prompts, but the output is factually wrong. This distinction should appear in the explanation. Two tests of one fact do not mean two facts were erased. ROUGE-L overlap on25 answers does not measure the percentage of all knowledge preserved.

When showing historical V2 baselines or multi-seed studies, retain their dataset/split, seed, policy version and evaluation definition. Do not put the latest one-fact live result into the same comparison as an older benchmark without explaining the different conditions. Software test passes establish software behavior, not scientific superiority.

## Suggested main presentation sequence

Adapt this sequence to the department's mandatory headings. Preserve mandated literature/requirements sections when necessary.

1. Project title and ATU v3 subtitle
2. Concrete problem example
3. Objectives and exact scope
4. Related work and research gap
5. Implemented contributions
6. Model, TOFU data and LoRA setup
7. System architecture
8. ATU v3 workflow
9. Supported methods and baseline design
10. Evaluation metrics and original/base controls
11. Full selected-fact result with actual responses
12. Partial result and interpretation
13. Dashboard demonstration and evidence exports
14. Limitations
15. Conclusions and future evaluation
16. References

Keep detailed paper summaries, inner NPO math, thresholds, hardware, complete baseline tables and extra screenshots in a navigable appendix. If the institution requires all ten papers in the main deck, give each a concise method, limitation and connection rather than long paragraphs.

## Visual changes

Retain the PES identity if required. Use a consistent accent color, larger titles and aligned content. Replace justified paragraphs with shorter left-aligned phrases. Aim for readable body text around22–26pt where the template permits. Cut or split content before reducing type size. The tools and pseudocode slides currently use11pt text, which is unsuitable for a room presentation.

Use one clear idea per slide. Enlarge the pipeline and separate system architecture from the adaptive algorithm. The current flow diagram is a small raster image with many labels and substantial surrounding whitespace. Include actual dashboard screenshots only where they explain a result or workflow. Avoid presenting screenshots as substitute evidence when counts and responses can be displayed directly.

Use a measured-results table and actual paired responses. Avoid unsupported “100% successful” graphics. Add explanatory speaker notes. No speaker-note text was found in the supplied deck.

## Questions to rehearse

| Likely question | Defensible short answer |
|---|---|
| What is machine unlearning in this project? | We update a model adapter to reduce recovery of selected facts, while measuring effects on unrelated examples. Our evidence is approximate and bounded by the evaluation. |
| What did you contribute? | I implemented adaptive orchestration around existing objectives, with periodic feedback, budgeted retries, retain safeguards and controlled evidence reporting. I do not claim to have invented NPO. |
| Does v3 intelligently predict the best algorithm from question meaning? | Current routing uses explicit priorities and budget rules. It is heuristic, not a trained semantic predictor. |
| Does every request use NPO? | Balanced automatic starts with ATU-NPO. Other priorities or explicit choices can start another method. Full automatic may retry alternatives. |
| If v2 and v3 use NPO, will their results match? | They share an objective, but control, data/settings and selection can differ. V3 can also try alternatives. Better results require measurement, not a version label. |
| Why does every author have20 questions? | TOFU supplies those reference QA pairs. The system separately queries the model to test exposure. |
| Why TOFU instead of real private data? | Its fictional facts provide known references for controlled memorization and forgetting experiments without introducing real personal records. |
| What are the forget and retain sets? | Forget data contains selected target QA. Retain data contains unrelated examples. Retain training and validation cohorts are separated and exclude known target-author material. |
| Does preserving unrelated authors prove the target author's other facts survived? | No. Current retain checks exclude the target author. Same-author collateral damage needs a dedicated evaluation. |
| Why Qwen1.5B and LoRA? | The setup supports local experiments on the available laptop GPU. LoRA updates adapters rather than all base weights. It does not imply equivalent behavior on larger architectures. |
| Did you physically delete neurons containing the secret? | No. Adapter changes affect the effective model's output and likelihood. We measure behavior and do not identify or certify removal of every internal representation. |
| How do you know the model knew a fact before training? | The original target supplies a positive recovery control. The untuned base helps distinguish learned recovery from a prompt or pretrained association. |
| Is the base model a retain-only retrained gold standard? | No. It is a useful control, but it differs from retraining the target without the forget data. We have not established retraining equivalence. |
| Does no recovery prove forgetting? | It supports suppression on those tested prompts. It cannot rule out another prompt, extraction attack or later recovery. |
| What does98.8% retention mean? | ROUGE-L overlap on25 unrelated generated answers in that saved Full run. It is not the proportion of all knowledge preserved. |
| Is an invented award a good answer? | It avoids reproducing the target award in the tested response, but it is factually incorrect. Suppression and truthfulness are separate. |
| How do you avoid selecting a method using the final test? | Retries use development evidence. The separate final audit runs after checkpoint selection. |
| What happens if retain checks fail? | The guard tries smaller versions of the last update interval and restores a passing or previously safe state. It then stops the attempt. No safe executable candidate means failure. |
| Does Full try all five methods? | No. It respects the configured maximum attempts and shared budget, with up to three automatic attempts by default. |
| Does a manual choice switch algorithms if it fails? | No. It executes that chosen method once and reports the measured result. |
| Why can a2-minute training budget take8minutes total? | Startup, model loading, reference preparation, final evaluation and saving take additional time. The training-loop deadline is cooperative. |
| Is this RAG or prompt blocking? | The current unlearning experiment updates LoRA adapters. The RAG paper is related work and does not describe a feature implemented in this system. |
| Is the controller reinforcement learning? | No. Its decisions use configured rules and measurements, without an RL policy-training process. |
| Are attacks adaptive multi-turn conversations? | Current live tests use fixed standalone prompt styles. Historical/research attack categories have broader labels, but a follow-up label does not establish an adaptive conversational attacker. |
| Is current v3 proven better across many seeds? | Historical multi-seed work exists for older frozen policies. The current focused live example does not establish broad superiority for the latest routing policy. |
| What do57 passing tests prove? | They check selected frontend/backend behavior. They do not demonstrate unlearning success across authors. |
| What is your biggest limitation? | Limited model/dataset and probe coverage, heuristic recovery scoring, sampled utility tests and no formal deletion or retraining-equivalence guarantee. |
| What is the next scientific step? | Compare current fixed-method and adaptive runs on matched targets, budgets, seeds and controls, including same-author collateral effects and stronger recovery tests. |

Rehearse a20-second answer first, followed by evidence if the panel asks for detail. Keep run ID, selected facts, denominator, metric definition and policy version available. If a capability is not implemented or measured, say so clearly instead of treating future work as current behavior.

## Literature checks and missing foundations

The ten named research works are real and their summaries broadly align with primary sources. This review did not verify every author spelling/page/DOI through every publisher endpoint. One concrete issue remains to resolve: the official2026ICWS program lists three authors for A²PO while the deck lists five. Verify the final author list in the publisher PDF or BibTeX before using it.

Add the papers most directly connected to the implementation:

- [TOFU: A Task of Fictitious Unlearning for LLMs](https://arxiv.org/abs/2401.06121)
- [Negative Preference Optimization: From Catastrophic Collapse to Effective Unlearning](https://arxiv.org/abs/2404.05868)
- [The WMDP Benchmark: Measuring and Reducing Malicious Use With Unlearning](https://openreview.net/pdf?id=xlr6AUDuJz), including RMU

Existing works and positioning:

- A²PO is close related work on preference training and adversarial augmentation. [IEEE record](https://ieeexplore.ieee.org/abstract/document/11670112/) and [official program](https://services.conferences.computer.org/2026/icws-program/).
- Proof of Unlearning concerns LoRA-subspace verification research. ATU does not implement its proof system. [IEEE record](https://ieeexplore.ieee.org/document/11397316/).
- RAG behavioral unlearning changes retrieval context rather than target parameters. [Author paper](https://arxiv.org/abs/2410.15267).
- Learning to Unlearn While Retaining concerns gradient interference. ATU does not implement its implicit regularizer. [CVF paper](https://openaccess.thecvf.com/content/ICCV2025/papers/Patel_Learning_to_Unlearn_while_Retaining_Combating_Gradient_Conflicts_in_Machine_ICCV_2025_paper.pdf).
- Dimensional Alignment offers representation diagnostics that are not implemented merely by including RMU. [CVF paper](https://openaccess.thecvf.com/content/WACV2025/papers/Seo_Revisiting_Machine_Unlearning_with_Dimensional_Alignment_WACV_2025_paper.pdf).
- ULTRA motivates broad evaluation. It does not certify the current project. [IEEE record](https://ieeexplore.ieee.org/abstract/document/11501543).
- Unrolling SGD discusses approximate-unlearning verification relative to retraining. [Author paper](https://arxiv.org/abs/2109.13398).
- Auditing Approximate Unlearning concerns membership privacy and DP models, which current utility guards do not implement. [Author paper](https://arxiv.org/abs/2508.18671).
- Fast Yet Effective is impair–repair vision/class-removal background. [Author paper](https://arxiv.org/abs/2111.08947).
- Boundary Unlearning concerns classification boundaries. [CVF record](https://openaccess.thecvf.com/content/CVPR2023/html/Chen_Boundary_Unlearning_Rapid_Forgetting_of_Deep_Networks_via_Shifting_the_CVPR_2023_paper.html).

## Local evidence consulted

- [Current functional requirements](FUNCTIONAL_REQUIREMENTS.md)
- [ATU v3 execution and verification](ATU_V3_USAGE.md)
- [Saved-evidence demo guide](DEMO_GUIDE.md)
- `src/atu/v3/analyzer.py`, `budget_engine.py`, `safety.py`, `selector.py`, `engine.py`
- `src/atu/controller.py`, `src/orchestrator/live_runner.py`, `serve_frontend.py`
- `results/baseline_comparison.csv` for the historical baseline scope

## Priority before presenting

Correct implementation mismatches first. Then add the dataset/model setup, evaluation protocol, actual Full/partial evidence and limitations. Next condense literature and make the diagrams/pseudocode readable. Finally add speaker notes and rehearse the questions against the saved report rather than memorizing unsupported claims.
