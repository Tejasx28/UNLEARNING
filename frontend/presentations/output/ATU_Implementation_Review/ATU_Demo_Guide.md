# ATU v3 demo guide

Use ATU_Demo_Ready.pptx. This revision has 40 slides. The pseudocode section is slides 23–24, the five screenshot pages are 27–31, model testing is 32 and software testing is 33.

## 12-minute route

| Time | Slides | What to explain |
|---|---|---|
| 0–2 min | 3, 21 | The award-fact example and the four system layers. |
| 2–3 min | 23–24 | Main ATU loop, changing fact weights and the safety check. |
| 3–8 min | 27–31 | Selected request, before/after answers, separate quality check, real training and model controls. |
| 8–10 min | 32 | Open NPO and RMU responses. Open GradDiff if time allows. |
| 10–12 min | 34, 36 | State the implemented contribution and next steps. Leave time for questions. |

The full deck includes the academic background and references. Do not rush through all 40 slides in a 10–15 minute slot.

## Opening the evidence

Slide 32 has offline links to NPO, RMU and GradDiff response examples in evidence/model_testing.html. Keep the project folder in its current location so file links resolve. These are three separately trained adapters on one Qwen model.

The Anaya application links on slides 27 and 31 need the local project server and run history. The embedded screenshots remain usable without the server. Source links expect VS Code.

## Words you should know

| Term | Plain meaning |
|---|---|
| Unlearning | Training intended to make selected facts harder to recover. |
| TOFU | A benchmark with fictional authors and question-answer pairs. |
| Base model | Qwen before the project's TOFU training. |
| Original target | The TOFU-trained model before unlearning. |
| LoRA adapter | A small set of trainable weights attached to the model. |
| Checkpoint | A saved set of model or adapter weights. |
| DEV / progress questions | Questions used while deciding training attempts. |
| Final questions | Separate questions used after choosing the result. |
| Retain examples | Unrelated examples we want to keep useful. |
| Loss | A training error score. A larger increase on unrelated examples can signal harm. |
| ROUGE-L | Word-sequence overlap with a reference answer, from 0 to 1. |
| Optimizer update | One actual step that changes trainable weights. |
| Hash | A file identity value used to detect changes. |

## The pseudocode in your own words

**Main ATU process:** Choose a method and settings. Start each attempt from the original target. Train with safety checks and test progress. Stop if the measured goals pass, or use progress evidence to choose another allowed attempt. Pick a safe result and run separate final tests. Save the changed adapter and results.

**Fact weighting:** Give more forgetting pressure to facts that progress questions still recover. Reduce pressure only when the target score is low enough and the required tests have finished.

**Safety check:** Compare the loss on unrelated examples with the original model. Keep safe weights. If an update causes too much harm, try smaller parts of it, restore a safe version and stop that attempt. The original loss baseline stays fixed.

The pseudocode summarizes the implemented stages. The source hyperlinks open the actual modules.

## Questions likely to come up

**What did you implement?** The ATU control workflow: exposure tests, limited training attempts, fact weights, safety, result selection and saved evidence. NPO, RMU and DPO come from earlier research.

**Why keep the original adapter?** It gives a comparison point and a clean starting point for each new attempt.

**Why use separate progress and final questions?** Progress questions guide training decisions. Final questions check the chosen result without changing those decisions.

**What is ATU-NPO?** It uses NPO training and changes how strongly each selected fact is targeted, using progress evidence and answer scores.

**What is the answer score and floor?** The score is the average log-probability of the reference answer. A lower score means that answer is less likely. The floor is the selected threshold; the code supports using the base-model answer score when setting it. The exact policy comes from the saved run settings. A low score alone cannot prove that every question fails to recover the fact.

**Why try 0.5, 0.25 and 0.125?** They are half, a quarter and an eighth of the last update interval. Every candidate must pass the same original safety limits.

**Why LoRA rank 32 and alpha 64?** They are saved configuration choices. Rank controls the size of the adapter update, and alpha scales it. This presentation does not claim those values are optimal.

**What do the other methods do?** GradDiff trains against target answers and toward unrelated answers. RMU changes selected internal features. DPO can prefer a refusal answer. Gradient ascent makes target answers less likely but can also harm other answers.

**Why does the main example run only once?** Its request explicitly chose ATU-NPO. Automatic mode can use retries or other methods when progress evidence and limits allow them.

**Are three updates enough?** Three updates prove that training changed weights in this example. The response tests determine what changed. The count alone cannot establish complete removal.

**Why is training 22 seconds but the run about 4 minutes 20 seconds?** The complete run also loads models, checks exposure, generates answers and saves results.

**Is the new award answer correct?** No. The selected Jannat award is absent in that tested answer, but the Jawahar replacement is wrong. Target suppression and answer correctness are different findings.

**Why show the base model?** The original must reveal the target, while the base must not reveal it for this checked comparison. If the controls are unclear, the test remains unclear.

**Does 98.8% mean all knowledge was preserved?** It is mean ROUGE-L on 25 sampled unrelated questions. It describes that sample and metric. It is not the percentage of all knowledge or exact factual accuracy.

**Does the safety guard use ROUGE-L?** The training guard checks loss changes on unrelated examples. Generated-answer quality is measured separately during evaluation.

**Why is the quality slide a different run?** The old 26 October example lacks a before/after quality measurement. A separate Anaya follow-up on 27 October records that comparison. The slides label this explicitly.

**Are NPO, RMU and GradDiff three base models?** They are three separately trained adapters on the same Qwen2.5-1.5B-Instruct model.

**Which method is best?** The saved results show different trade-offs. We inspect target responses and unrelated-answer quality together. A low overlap score alone can also mean a wrong answer.

**Can another question recover the fact?** Possibly. Results cover the tested questions. More recovery tests and repeated runs are needed.

**Do the software tests prove forgetting?** They check implementation behavior. Model response tests provide separate evidence about the selected facts.

## Run identities

- Main Anaya request, responses, training and controls: job_1793032377801_fa0d0688, 26 October 2026.
- Separate Anaya quality follow-up: job_1793088345703_42838b54, 27 October 2026.
- Historical adapter tests: results/npo_eval.json, results/rmu_eval.json and results/graddiff_eval.json.

## Closing sentence

“ATU v3 lets us run selective unlearning, inspect what changed, check unrelated answers and show the saved evidence behind the result.”
