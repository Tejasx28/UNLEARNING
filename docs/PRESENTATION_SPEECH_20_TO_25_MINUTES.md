# Simple Presentation Speech

For a 20 to 25 minute slot and all 40 slides in 4.pptx. Questions are additional.

Read only the speech under each slide heading. Aim for about 22 to 23 minutes including pauses and slide changes. Rehearse with a timer.

## Slide 1 Title

Good morning. I am Tejas. My project is Selective Knowledge Erasure in Large Language Models. The main question is whether we can make chosen information harder to get from a trained model while keeping other useful answers.

I will explain the problem and the system, then show what a saved experiment tells us.

## Slide 2 Abstract

My system is called ATU v3. ATU stands for Adaptive Targeted Unlearning. It first checks what the original model reveals. It then changes a small set of model numbers, checks progress, and tests the saved result.

The report checks unrelated answers and shows where the target is absent, still found, or unclear. This makes the outcome easy to inspect.

## Slide 3 Problem scenario

Let us take the example on this slide. Anaya is a fictional author in the TOFU dataset. Before unlearning, the model answers her award question with the Jannat Literary Award for Excellence in Criticism.

The request targets that award. Deleting its data row would not change the model’s learned numbers. We must update the model, test again, and check whether other answers became worse.

## Slide 4 Purpose and scope

The project has two connected goals. The first is to reduce answers that reveal the selected fact. The second is to keep unrelated answers useful. Meeting only one goal would not be enough.

A model producing nonsense may hide the target but lose useful behavior. I test this balance using fictional TOFU profiles and one Qwen model. Results cover the questions and examples checked.

## Slide 5 Background and research gap

Several existing methods can change what a model says. The practical challenge is deciding how much training to apply, whether it is helping, and when to stop.

A fixed run may overtrain or stop while another question still reveals the fact. My project combines methods, progress checks, limits, and saved evidence. The following papers guided these choices.

## Slide 6 TOFU research paper

TOFU means Task of Fictitious Unlearning. It provides 200 fictional authors with 20 questions each, giving us known facts and expected answers.

My project uses this controlled setting. The reference answer tells us what to test. The model’s actual response tells us whether it reveals that information.

## Slide 7 NPO research paper

Negative Preference Optimization, or NPO, makes a target answer less likely compared with the original model. It aims to balance forgetting and useful behavior.

NPO is the basis of ATU-NPO in this project. I add checks that change how much importance each selected fact receives during training.

## Slide 8 WMDP and RMU research paper

This paper introduces WMDP and RMU. RMU changes internal number patterns for selected examples while trying to preserve other behavior.

My project includes an RMU implementation as an alternative. The experiments here use TOFU, so they test a different setting from the paper’s hazardous-knowledge benchmark.

## Slide 9 Large Language Model Unlearning paper

This paper studies changing unwanted behavior without training a new model from the beginning. It discourages unwanted answers while trying to protect useful behavior.

It helped motivate the GA and GradDiff comparisons. The lesson for my project is to measure target changes and unrelated-answer quality together.

## Slide 10 DPO research paper

DPO learns from preferred and rejected answers. A related preference-training idea in this project can favor a refusal over the original target answer.

A refusal alone does not prove removal. Another question may reveal the information, so recovery tests remain necessary.

## Slide 11 Dissecting Fine Tuning Unlearning paper

This paper examines whether a model that appears to forget may still hold recoverable information. It motivates looking beyond one changed answer.

My system therefore checks generated answers as well as scores, using progress and separate final questions.

## Slide 12 ReLearn research paper

ReLearn also considers the quality of generated answers. A target answer can become less likely while the model produces something irrelevant or incorrect instead.

In the Anaya example, the target award disappears but the replacement is false. ReLearn is background research and is not implemented here.

## Slide 13 RWKU research paper

RWKU studies unlearning of real-world knowledge. It uses facts about real people and checks recovery and effects on other knowledge.

Fictional authors give this project a controlled starting point. Real private information brings other difficulties and requires a separate study.

## Slide 14 Relearning attacks research paper

This paper studies whether later training can bring information back after unlearning. That is a different test from asking more questions of the same saved model.

Relearning resistance is future work here. Passing tests immediately after an update does not establish that resistance.

## Slide 15 Training data extraction paper

This paper shows that language models can reveal memorized training text through generated responses. It explains why it is useful to test what the model actually reveals.

My project tests candidate facts with targeted questions. It does not implement the full extraction pipeline. These papers motivate careful evaluation.

## Slide 16 Dataset and model setup

TOFU contains 4,000 question-answer pairs across 200 fictional profiles. The chosen model is Qwen2.5-1.5B-Instruct. The original target model was trained on TOFU so that its exposure could be measured before unlearning.

Unlearning changes a LoRA adapter: small trainable tables of numbers added to model layers. Base numbers stay frozen, meaning unchanged. Rank 32 and alpha 64 control its size and update scale. These saved settings are not proved optimal.

## Slide 17 Tools and technologies

The screens use React and TypeScript, with Vite helping run and build the interface. Python handles the requests and starts the training work. PyTorch performs the model calculations and updates.

Transformers loads the model, PEFT supports adapters, and CUDA uses a compatible NVIDIA GPU. JSON files store requests and results; model files store adapter numbers. These are recorded environment versions. Older runs keep their own details.

## Slide 18 Intended users

The main operator is a researcher or student. This person chooses the facts, method, and limits, starts the experiment, and inspects the outcome.

Evaluators check remaining recovery and effects on other answers. Supervisors review saved runs and code. These are uses of the same local system, without separate login roles.

## Slide 19 Functional requirements

These seven functions describe what the application does. The user selects target facts and settings. The system checks what the original model reveals, runs the chosen training process, and monitors unrelated answers.

It tests recovery with comparison models, shows progress and cancellation, and saves reports. Each function links to code, connecting the work to observable results.

## Slide 20 Non functional requirements

The system also needs predictable operation. It manages one training worker at a time so that another request does not silently start a competing experiment.

It limits attempts, updates, and training time. Finished, failed, and cancelled runs have distinct states. Unique run IDs and saved settings help trace each result. The interface separates preparation from actual training updates.

## Slide 21 System architecture

This diagram shows the system from left to right. The user chooses facts and settings in the browser. The interface sends that request to the Python server. The server checks it and starts a separate worker process.

The worker prepares the questions, checks the original model, and runs the ATU engine. That engine manages methods, progress tests, and safety checks. After choosing an adapter that passes the checks, the worker runs final checks and creates the report.

Files hold reference data, adapters, and results. A separate worker lets the server report progress and handle cancellation.

## Slide 22 Data flow diagram

This diagram follows the information rather than the software layers. First, the request becomes valid selected questions and settings. The original model then produces exposure evidence.

Training creates candidate adapters and trial results. The system selects one that passes its required safety checks. It tests that result and stores the responses and scores. The user can later retrieve the saved evidence.

Final-test results do not guide retries. They examine the chosen result after selection, instead of becoming more tuning questions.

## Slide 23 Main ATU process

The first pseudocode slide summarizes the main loop. Each attempt reloads the original target adapter. This gives the next method a clean starting point instead of continuing from the previous attempt’s changes.

The system trains with safety checks and asks development questions to measure progress. If a method was chosen manually, it runs once. In automatic mode, another permitted attempt may use adjusted settings or a different method.

Attempts share the request’s limits. The system chooses a result that passes the safety checks and asks separate final questions. If none qualifies, it does not promote an unsafe model.

## Slide 24 Fact weights and safety

The left side explains how ATU-NPO changes training effort. A fact weight means the importance of an example during training. It is different from the learned numbers inside the model.

If a progress question still reveals the fact, the controller gives it more effort. If the answer score reaches its threshold and the required progress checks are clear, the effort can decrease.

The right side protects unrelated answers. The guard compares their scores with the original scores. On a harmful change, it tries half, a quarter, and an eighth of the last update interval. It keeps a passing version or restores saved safe weights, then stops the attempt. These checks cover the measured examples.

## Slide 25 Unlearning methods

The method list contains different ways of changing behavior. ATU-NPO changes the training importance of selected facts. GradDiff discourages target answers while also training toward retain answers, which are answers we want to keep useful.

RMU changes selected internal patterns. The refusal method trains the model to prefer a refusal over the target answer. Gradient ascent directly trains against the target answer and can also damage useful behavior.

Each method still needs response and retain checks. Balanced automatic mode begins with ATU-NPO. Manual mode keeps the user’s choice.

## Slide 26 How the result is checked

For the final comparison, we use three model states. The original target must reveal the selected fact. The base model, before our TOFU training, must not reveal it for the clean comparison used here.

We then ask the changed adapter the same question. If the target is absent under those controls, the check supports measured suppression. If it still appears, the report records remaining recovery. If the controls or output are unclear, it records an inconclusive result.

The base is a comparison model, not a model retrained only on retained TOFU data. Unrelated-answer quality and fact coverage are also reported separately.

## Slide 27 Selected fact and settings

I will now explain the saved Anaya experiment. The request selects one award question and manually chooses ATU-NPO. This is therefore a one-method, one-attempt example, rather than a demonstration of method switching.

The training allowance is 600 seconds. The complete job took about four minutes twenty seconds. The allowance is a ceiling, not a required duration. Saved settings establish the request.

## Slide 28 Answers before and after

Look at the original answer first. It gives the Jannat Literary Award for Excellence in Criticism. This is actual model output, so it establishes exposure of the target award under that question.

After training, the model gives a different award, the Jawahar Literary Award. That replacement is incorrect. The original target award is absent from this tested response, but the model has not produced a truthful replacement.

Both observations matter: tested suppression and a false replacement. A real application would need to address that output-quality problem.

## Slide 29 Check unrelated answers

This slide shows a separate Anaya follow-up from October 27. I keep it separate from the main October 26 example because it records the paired before-and-after quality measurement.

The model answered the same 25 unrelated questions before and after training. The mean ROUGE-L score was 98.8 percent both times. ROUGE-L measures how much word sequence is shared with reference answers. It is a wording-based comparison, rather than a full check of every fact’s truth.

This sample had zero relative decline. It does not establish preservation of all knowledge or Anaya’s unselected facts.

## Slide 30 Actual training and saved result

Returning to the main Anaya example, the record shows three actual optimizer updates. An optimizer update is a step that changes the trainable adapter numbers. The kept adapter changed and was saved separately from the original.

The training loop took about 22 seconds. The full job took longer because it also started the worker, loaded models, checked exposure, generated test answers, and saved results. These are different timing measurements.

The updates establish real training; the response tests show its effect. Update count and time alone do not prove forgetting.

## Slide 31 Why the controls matter

This slide brings the three responses together. The original target reveals the selected award. The base does not reveal that target award. The changed adapter also does not reveal it in the two tested prompts.

The saved audit therefore reports two passed calibrated checks for one selected fact. Calibration here means that the original and base controls support the comparison. Two prompts are two ways of testing the same request; they are not two different forgotten facts.

The false replacement remains visible, so passing suppression checks is not confused with truthful answering.

## Slide 32 Three trained adapters

This table compares NPO, RMU, and GradDiff adapters on the same Qwen model. These are different trained versions of one backbone, rather than three different language-model architectures.

Lower target-answer overlap means less shared wording with the original target answers. Higher unrelated-answer overlap means more shared wording with the retain references. Among these three saved variants, NPO has the lowest target overlap, while RMU has the highest retain overlap.

NPO’s scores are about 0.15 for target overlap and 0.98 for retain overlap. This earlier baseline table is separate from Anaya and does not prove current V3 superiority.

## Slide 33 Software testing

The saved verification record from October 27 reports 319 Python tests and 27 frontend tests passing. TypeScript checks and the production build also passed.

These tests check software behavior, such as request handling, training logic, and interface actions. They answer a different question from the model tests. A correctly working program can still produce an unlearning attempt that leaves information recoverable.

These are dated software checks, not a fresh test of every later version or proof of successful forgetting.

## Slide 34 Project contribution

The implemented contribution is the system that connects these steps. It checks original exposure, manages fresh attempts within limits, changes training effort where appropriate, and protects a small set of unrelated answers.

It chooses and tests an adapter that passes the checks, preserving responses and run details. We can explain why training stopped and what supports the outcome.

The training methods come from prior research. My contribution is the implemented control and evidence workflow around them.

## Slide 35 Limitations

The evaluation uses one Qwen model and fictional author data. The number of recovery questions and unrelated examples is limited. Another question or later training may bring information back.

A missing target can also come with a wrong replacement, as the Anaya example shows. Unrelated-answer checks do not establish that all other facts about the same author were preserved.

Method order and recovery scoring use practical rules. I report tested suppression and remaining recovery, without claiming success for every request.

## Slide 36 Conclusion and next steps

ATU v3 provides a working way to run selective unlearning experiments and inspect the outcome. It links the selected request to training updates, safety checks, final responses, and saved evidence.

The evidence shows that some tested target facts stop appearing, while harder cases still reveal information. The next steps are to test more authors, repeat runs with different random seeds, and use stronger recovery questions.

I would check the same author’s unselected facts and compare methods under matching limits. That would help identify which system choices improve the result.

## Slide 37 References one to four

These references cover TOFU and the earlier research behind the main unlearning methods.

## Slide 38 References five to seven

These sources discuss preferred answers, remaining knowledge, and generated-answer quality.

## Slide 39 References eight to ten

These sources cover real-world facts, relearning, and training-data extraction.

## Slide 40 Official sources and closing

The final references are the official sources for the model, dataset, and software tools.

The main message is that we should show what changed, what remains recoverable, and the evidence behind both. Thank you. I am ready to answer your questions.
