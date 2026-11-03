# PPT Words and Questions in Simple English

## The main project words

### Selective knowledge erasure

Trying to reduce access to chosen facts while keeping other answers useful. The project tests this goal; it does not prove complete removal.

### Large language model or LLM

A model that learns patterns in text and predicts the next text pieces to produce answers.

### Machine unlearning

Further training intended to reduce the model’s ability to give selected information it learned earlier.

### ATU

Adaptive Targeted Unlearning. The system changes its training effort using measured progress.

### TOFU and benchmark

TOFU means Task of Fictitious Unlearning. A benchmark is a shared dataset and testing task. TOFU provides fictional author questions and known answers.

### Qwen and backbone

Qwen is the chosen language-model family. Backbone means the underlying model shared by the different trained adapters.

### Dataset QA pair and reference answer

A dataset is a collection of examples. A QA pair contains one question and its answer. A reference answer is the expected answer used for comparison.

### Base model

Qwen before this project’s TOFU training. It is not a model retrained only on the retained TOFU data.

### Original target model

The model after TOFU training and before unlearning. It is the starting point used for comparison.

### Changed or unlearned model

The model using the adapter saved after an unlearning attempt. Its name alone does not mean that forgetting succeeded.

### Exposure leakage and recovery

Exposure or leakage means the model reveals a chosen fact. Recovery means getting that fact back through a test question.

### Suppression

The chosen information is less likely or does not appear under the tested conditions. It does not prove that the information is gone everywhere.

## Words about training

### Fine tuning and memorization

Fine-tuning trains an existing model on more examples for a task. Memorization means the model learned details from training and can repeat or reveal them.

### Model weights and frozen weights

Model weights are learned numbers used to produce answers. Frozen weights stay unchanged during that training step.

### LoRA adapter and matrix

LoRA means Low-Rank Adaptation. An adapter adds small trainable matrices to model layers. A matrix is a table of numbers. This lets us train fewer numbers.

### Rank and alpha

Rank controls the size of the LoRA matrices. Alpha controls how strongly their update is scaled. The saved values are 32 and 64.

### Forget examples and retain examples

Forget examples contain the selected answers to train against. Retain examples are answers we train on or check because we want to keep them useful.

### NPO

Negative Preference Optimization. It reduces the score of a target answer compared with that answer’s score under the original target model.

### GradDiff and gradient ascent

GradDiff combines training against target answers with training toward retain answers. Gradient ascent increases loss on target answers so the model is less likely to give them.

### RMU and internal representation

Representation Misdirection for Unlearning. It changes patterns of internal numbers produced when the model processes selected examples.

### DPO preference and refusal

DPO means Direct Preference Optimization. Preference training favors one answer over another. A refusal says the model will not provide the requested information.

### Fact weight and forgetting pressure

A fact weight is the importance given to an example in the training loss. More pressure means more training effort against that example. It is different from a model weight.

### Loss gradient and optimizer update

Loss is a training error score. A gradient describes how that score changes when model numbers change. The optimizer uses it to make an update: one actual training step.

### Attempt trial and checkpoint

An attempt or trial is one candidate training run. A checkpoint is a saved set of adapter or model weights.

### Safety guard backtracking and rollback

The guard checks allowed harm to unrelated answers. Backtracking tries a smaller recent change. Restore or rollback means returning to saved model numbers. Safety covers only measured examples.

### Seed

A starting number used for random choices in an experiment. It helps repeat those choices, but does not by itself guarantee the same result on every setup.

## Words about checking results

### DEV and final questions

DEV means development. These questions guide progress and retries. Separate final questions test the chosen result after selection.

### Likelihood and log probability

These score a specified reference answer. Log probability uses another number scale: more negative means less likely. It does not measure whether the answer is true.

### Token mean token score and nat

A token is a text piece, such as a word or part of a word. Mean means average. A nat is a unit used for log-probability. Per token means per text piece.

### Floor and threshold

A threshold is a cutoff used for a decision. The floor is the chosen answer-score cutoff. Live V3 normally compares against the untuned base answer score plus a small allowance.

### Stubborn limit

A score used to mark an answer as still needing stronger forgetting effort. The controller uses this rule to decide how much training importance to give the fact.

### Control and calibration

A control is a comparison used to interpret a test. Calibration here checks that the original target reveals the fact and the base does not before judging the changed result.

### Inconclusive

The evidence is unclear or does not support a valid comparison. An inconclusive check does not count as demonstrated suppression.

### Metric and ROUGE L

A metric is a numerical measurement. ROUGE-L compares shared word sequences between a generated answer and a reference. It is not a complete meaning or truth test.

### Overlap and mean

Overlap describes how much the answers share matching text. Mean means average. A mean can hide different results on individual questions.

### Sample utility and preservation

A sample is a limited set of examples. Utility means useful model behavior. Preservation means keeping that behavior within the checks used.

### Relative decline

A drop measured as a share of the original score. If the original is 0.90, a 2 percent relative drop gives 0.882, not 0.88.

### Training budget and wall time

The budget limits time in the training loop. Wall time is the whole elapsed job time, including loading and testing. They are different measurements.

### Heuristic and automatic routing

A heuristic is an explicit practical rule. Routing chooses the next method using those rules and progress. The selector is not a trained model predicting the best method.

## Words about the app and research papers

### Frontend and backend

The frontend is what the user sees and clicks. The backend handles requests, training processes, and saved results.

### Worker process and GPU

A worker is a separate running program that does the experiment. A GPU is a processor that performs many training calculations in parallel.

### Architecture and data flow diagram

Architecture shows the main system parts. A data-flow diagram, or DFD, shows how information moves between processes and stored data.

### Pseudocode

A readable outline of an algorithm. It explains the steps without showing every detail required by the real program.

### Functional and non functional requirements

Functional requirements state what the app must do. Non-functional requirements describe qualities such as reliability, resource control, and usability.

### HTTP JSON and saved records

HTTP carries web requests and responses. JSON stores structured text such as settings and results. Saved records link an outcome to its run and settings.

### React TypeScript and Vite

React builds the screens. TypeScript adds checks on data types in frontend code. Vite runs the development interface and builds the app files.

### PyTorch Transformers and PEFT

PyTorch performs model calculations and training. Transformers loads language models and tokenizers. PEFT supports training and using small adapters.

### CUDA Datasets Accelerate and Safetensors

CUDA lets supported NVIDIA GPUs run calculations. Datasets loads data. Accelerate supports model execution. Safetensors stores model or adapter numbers.

### Catastrophic collapse

Training damages model behavior severely, for example causing nonsense or poor answers across many questions.

### Relearning attack and extraction

A relearning attack uses later training to bring information back. Extraction tries to obtain memorized training content through model outputs.

### ReLearn RWKU WMDP and SAM

ReLearn is another unlearning approach. RWKU tests real-world knowledge, and WMDP tests hazardous knowledge. SAM is a training technique discussed in the relearning paper. These names do not mean all four are implemented here.

### Literature survey and references

A literature survey explains relevant earlier research. References identify the sources so others can find and check them.

### IEEE DOI arXiv and et al

IEEE is an organization; its numbered reference style is used here. A DOI is a lasting publication identifier. arXiv hosts research papers. Et al means and other authors.

### COLM ICML NeurIPS EMNLP ACL and USENIX Security

These are research conference names. On the paper slides they identify where the cited work appeared. You do not need to recite every full name during the speech.

## The ten answers to learn first

### What does your project do

It tries to make selected facts harder to get from a trained model. It also checks other answers and saves the results so we can see what changed.

### What does ATU stand for

ATU stands for Adaptive Targeted Unlearning. Adaptive means that the system changes its training effort using the progress it measures.

### What did you contribute

I brought the steps into one working system: checking exposed facts, controlling training, checking other answers, and saving final results. The main training methods come from earlier research.

### Have you completely removed the fact

The fact stopped appearing in the tested prompts. Those tests do not prove that every possible question will fail to recover it.

### Why is the new answer wrong

Training reduced the chosen award response, but it did not teach a truthful replacement. I therefore report both results: the target is absent in the test, and the new award is false.

### What does two out of two mean

It means that two checked prompts stopped revealing the selected award. Both prompts test the same fact. It does not mean two different facts.

### What does the ninety eight point eight percent score mean

It is the average ROUGE-L score on 25 unrelated answers. The score was the same before and after in the follow-up. It does not measure all model knowledge.

### Why is the quality result from another run

The original October 26 run did not record that paired quality comparison. The October 27 follow-up did. The slide labels it as a separate run.

### Why show three model versions

The original target shows that the model knew the fact after TOFU training. The base gives a comparison before that training. The changed adapter shows what happened after unlearning.

### Why does the main example run only once

I manually selected ATU-NPO in that request. A manual request runs the chosen method once. Automatic mode can try other allowed attempts.

## How the training works

### What is LoRA

LoRA adds small trainable tables of numbers inside model layers. This lets us change fewer numbers instead of training all the base weights, making local training more practical.

### What do rank thirty two and alpha sixty four mean

Rank controls the size of the LoRA tables of numbers. Alpha scales their update. These are saved settings for this project; I have not shown that they are the best possible settings.

### How does NPO work

NPO lowers preference for a target answer compared with the original model. Training on retain examples helps protect answers we want to keep.

### How are the other methods different

GA trains against target answers. GradDiff also trains toward retain answers. RMU changes internal patterns. Refusal training favors a refusal instead of the target answer.

### What makes ATU adaptive

ATU-NPO gives more importance to facts still found by progress tests. The outer system can also change settings or try another method when automatic mode and the limits allow it.

### How does the system choose the next method

It follows rules and a method order, then uses progress results. It is not a trained AI model that knows the best method for every fact.

### Why start every attempt from the original adapter

This gives each method a clean starting point. A new attempt does not continue from the changes or damage caused by the previous method.

### What happens when other answers get worse

The guard checks their scores against the original model. If the allowed drop is exceeded, it tries a smaller change or restores safe weights and stops that attempt.

### Does the safety guard use ROUGE L

The step guard checks changes in reference-answer likelihood. The system checks generated-answer ROUGE-L separately during evaluation. These measure different effects.

### When does training stop

It can stop when its required progress and safety checks pass, when a safety check fails, or when the allowed time, updates, or attempts are used up.

## How to explain the numbers

### Are three updates enough

They show that training really changed the adapter in this example. The answer tests show its effect. Three updates alone cannot prove that a fact has been removed.

### Why is training twenty two seconds but the job four minutes twenty

The 22 seconds covers the training loop. The full job also starts the worker, loads models, tests answers, and saves results.

### Why did a six hundred second request stop earlier

Six hundred seconds is an upper allowance for training, not a required duration. This attempt stopped when its recorded checks passed.

### Can the full job take longer than its training budget

Yes. Loading and final testing add time. The training checks also cannot interrupt a single calculation already running, so a check may finish beyond a time boundary.

### What is ROUGE L in simple words

It checks how much of the word sequence in a reference answer also appears in the model answer. A high score does not guarantee that the answer is fully correct.

### What is the two percent quality limit

It allows up to a 2 percent drop compared with the original mean ROUGE-L on the same sample. For an original score of 0.90, the allowed minimum is 0.882.

### What does the zero point zero three limit mean

It limits the average drop in reference-answer log-probability, measured in nats per token. It is separate from the 2 percent generated-answer quality limit.

### Did you compare three different language models

The table compares three trained adapters on the same Qwen model. They use NPO, RMU, and GradDiff. They are different trained versions, not three different base architectures.

### Which method is best

In that saved table, NPO repeats less of the target answers and RMU preserves more unrelated-answer overlap. The best choice depends on both goals and the actual responses.

### What do the software test counts prove

The October 27 record shows 319 Python tests and 27 frontend tests passing. They check the software. They are not 319 successful forgetting experiments or a new test of today’s code.

## Questions about limits and next steps

### Can another question bring the fact back

Yes, that is possible. We test separate final prompts, but they cannot cover every possible question. Stronger recovery tests are a next step.

### Did you protect other facts about the same author

That has not been established. The retain checks use unrelated examples. I would add tests on the same author’s unselected facts before making that claim.

### Are you using the final questions to improve training

No. Progress questions guide training and retries. Separately worded final questions run after selection. They still concern the same selected facts, so that is the limit of the separation.

### Does refusal mean the information is gone

No. A refusal shows how the model answered that prompt. Another prompt may still reveal the information, so recovery tests remain necessary.

### Why use fictional data and this model

Fictional data gives us known answers for a controlled test without using real private biographies. The chosen Qwen model and LoRA setup make local experiments practical.

### Does one successful Anaya example prove the method always works

No. It is a selected example for explaining the implementation. Harder saved experiments still reveal information. A broader result needs more authors and repeated runs.

### Are all the methods in the literature survey implemented

No. The project includes the listed live methods and fixed baselines. ReLearn, relearning-resistant SAM, RWKU testing, and Carlini’s extraction pipeline are background or future work.

### Is the base the same as retraining without the forgotten data

No. It is the model before TOFU training. This project has not shown that the changed model behaves exactly like a model retrained only on retained examples.

### What would you improve next

I would test more authors and repeat runs with different seeds. I would add stronger recovery questions and check unselected facts about the same author, using the same fixed comparison rules.

### What should you say if you do not know the answer

I have not tested that yet. What I can show from this run is the selected fact, the model responses, and the measured result. A broader answer would need a separate test.
