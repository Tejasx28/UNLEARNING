# Memory Friendly Presentation Speech

Use this as your new speaking guide for the 20 to 25 minute slot. Say the paragraphs between each cue and fallback. The cue helps you remember, and the fallback is there if you lose your place. They are not extra speech. You do not need to memorize every word. Keep the first sentence familiar and remember the order of ideas.

## The story to remember

- Slides 1 to 5: What problem am I solving.
- Slides 6 to 15: What earlier research taught me.
- Slides 16 to 20: What I built.
- Slides 21 to 26: How it works.
- Slides 27 to 33: What the evidence shows.
- Slides 34 to 40: What I contributed and what remains.

## If you lose your words

Pause briefly. Look at the cue or slide title. Say the fallback sentence. Continue with the next idea. You can use your own words rather than restart the whole slide.

## Practice understanding before exact wording

Read one slide, cover its speech, and explain it using only the cue. Check what you missed and try again. In a later practice session, try the cue before rereading. Give extra practice to slide 19 and slides 23 and 24. Ask yourself questions out of order. Finish with a timed run using the actual deck.

The speech has 2,519 words. At 120 to 130 words per minute, with about two minutes for pauses and slide changes, it takes roughly 21 to 23 minutes. Your rehearsal decides the timing. Questions are additional. Give slide 19 about three minutes and the two code slides about three minutes together.


## The problem and purpose

### Slide 1 Project title

**Remember:** Selected facts

**Say:**

Good morning. I am Tejas. My project is Selective Knowledge Erasure in Large Language Models.

It asks a simple question. Can we make selected facts harder to get from a trained model while keeping other answers useful?

I will explain the system, its seven main functions, and the evidence from a saved experiment.

**If I lose my place:** My project changes a trained model and checks whether selected facts still appear.

### Slide 2 Abstract

**Remember:** Change and check

**Say:**

The system is called ATU v3. ATU means Adaptive Targeted Unlearning.

The user chooses facts to target. The system checks the original answers, runs training, and tests the changed model.

It also checks unrelated answers. The report shows what stopped appearing, what is still recoverable, and what remains unclear.

**If I lose my place:** The system connects a selected fact to training and a checked result.

### Slide 3 Problem scenario

**Remember:** Anaya and award

**Say:**

Consider Anaya, a fictional author in the dataset. The original model gives her award as the Jannat Literary Award for Excellence in Criticism.

Suppose we want to target that award. Removing its data row does not change the numbers the model has already learned.

We therefore need to update the model and ask again. We must also check whether the update damaged unrelated answers.

**If I lose my place:** Deleting a training row does not undo what the model already learned.

### Slide 4 Purpose and scope

**Remember:** Two goals

**Say:**

The first goal is to reduce answers that reveal the selected fact. The second is to keep unrelated answers useful.

Both goals matter. A model that gives nonsense everywhere would also fail to reveal the fact.

This project studies the balance using fictional author data and one Qwen model. My claims cover the examples and questions tested.

**If I lose my place:** I check the selected fact and the effect on other answers.

### Slide 5 Research gap

**Remember:** When to stop

**Say:**

Earlier research provides several ways to train against unwanted answers.

The practical question is how to control that training. Too little may leave the fact recoverable. Too much may damage useful answers.

My project combines progress checks, training limits, safety checks, and saved results. I will briefly explain the research behind these choices.

**If I lose my place:** The project helps decide how to train, when to stop, and how to check the result.


## Research ideas used in the project

### Slide 6 TOFU paper

**Remember:** Known fictional facts

**Say:**

TOFU means Task of Fictitious Unlearning. It contains fictional authors and known question-answer pairs.

This gives us an expected answer to compare with the model response. My project uses this controlled setting for its experiments.

**If I lose my place:** TOFU gives us fictional facts with known answers to test.

### Slide 7 NPO paper

**Remember:** Lower target preference

**Say:**

NPO means Negative Preference Optimization. It reduces the score of the selected answer compared with the original model.

My ATU-NPO implementation builds on this idea. It changes the training importance of each fact using measured progress.

**If I lose my place:** NPO trains the model to give the selected answer less preference.

### Slide 8 WMDP and RMU paper

**Remember:** Internal patterns

**Say:**

RMU means Representation Misdirection for Unlearning. It changes internal number patterns for selected examples.

My system includes RMU as an alternative method. The experiments here use TOFU, rather than the hazardous-knowledge setting of WMDP.

**If I lose my place:** RMU changes internal patterns and is one alternative in my system.

### Slide 9 Large Language Model Unlearning paper

**Remember:** Forget and retain

**Say:**

This paper studies training against unwanted answers while protecting useful behavior.

It helped motivate gradient ascent and GradDiff in this project. I therefore check target answers and unrelated answers together.

**If I lose my place:** Training against a fact must be checked for damage to other answers.

### Slide 10 DPO paper

**Remember:** Preferred answer

**Say:**

DPO means Direct Preference Optimization. It learns to prefer one answer over another.

My system uses a related refusal-training method. It can favor a refusal over the target answer. We still need recovery tests because a refusal alone does not prove removal.

**If I lose my place:** Preference training can favor refusal, but we must still test recovery.


## Research that guides evaluation

### Slide 11 Dissecting Fine Tuning Unlearning paper

**Remember:** Ask another way

**Say:**

This paper examines whether information remains recoverable after a model appears to forget.

It motivates testing more than one wording. My system uses questions to guide progress and separate questions for the final check.

**If I lose my place:** One changed answer is not enough evidence, so we test other questions.

### Slide 12 ReLearn paper

**Remember:** Check answer quality

**Say:**

ReLearn draws attention to the quality of generated answers.

A target can disappear while the model gives a false replacement. That happens in the Anaya example I will show. ReLearn itself is background research here.

**If I lose my place:** The target can disappear while the new answer is still wrong.

### Slide 13 RWKU paper

**Remember:** Real world testing

**Say:**

RWKU studies unlearning of real-world knowledge and the effect on other facts.

My project starts with fictional authors and known answers. Testing real private information would need a separate study.

**If I lose my place:** Real-world testing is a useful next step beyond this fictional dataset.

### Slide 14 Relearning attacks paper

**Remember:** Knowledge can return

**Say:**

This paper asks whether later training can bring information back after unlearning.

My project does not demonstrate resistance to that kind of attack. Passing the current questions cannot establish what happens after later training.

**If I lose my place:** Later training may bring information back, and that has not been tested here.

### Slide 15 Training data extraction paper

**Remember:** Test actual responses

**Say:**

This paper shows why model responses matter when checking memorized training information.

My system asks targeted questions and records the answers. It does not implement the paper's full extraction pipeline. These papers guide the design and its limits.

**If I lose my place:** I test what the model reveals through actual answers.


## Data tools and users

### Slide 16 Dataset and model

**Remember:** Data model adapter

**Say:**

TOFU contains two hundred fictional profiles with twenty question-answer pairs each. That gives four thousand pairs.

The model is Qwen2.5-1.5B-Instruct. The original target has been trained on TOFU so we can test which facts it reveals.

Unlearning changes a LoRA adapter. This is a small set of trainable tables of numbers inside the model. The base numbers stay fixed.

Rank thirty-two controls the adapter size. Alpha sixty-four controls its update scale. These are the saved settings, rather than proven best settings.

**If I lose my place:** I use fictional TOFU data, Qwen, and a small trainable LoRA adapter.

### Slide 17 Tools and technologies

**Remember:** Screen server training

**Say:**

React and TypeScript build the screens. Vite runs and builds the interface.

Python handles requests and starts a separate training process. PyTorch performs the model calculations. Transformers loads the model, and PEFT supports LoRA adapters.

CUDA supports the NVIDIA GPU calculations. JSON files save requests and results, while Safetensors stores adapter numbers.

The slide records versions checked on October twenty-eighth. Older experiments keep their own saved details.

**If I lose my place:** The browser collects the request, Python manages it, and the training tools update the adapter.

### Slide 18 Intended users

**Remember:** Run and review

**Say:**

A researcher or student can choose the facts, set limits, and run an experiment.

An evaluator can inspect recovery and other-answer quality. A supervisor can review the saved evidence and code.

These describe how people use the local app. They are not separate account permissions.

**If I lose my place:** The app supports running experiments and reviewing their evidence.


## The seven functional requirements

### Slide 19 Functional requirements

**Remember:** Choose Check Train Protect Test Watch Save

**Say:**

This slide describes the seven functions of the application. I remember them as choose, check, train, protect, test, watch, and save.

First, select target facts and settings. The user chooses an author, the exact facts, a method, and training limits. In the Anaya example, I selected one award fact and manually chose ATU-NPO.

Second, check exposed facts. Before training, the original model answers questions about the selected facts. This establishes whether it reveals the target in the first place. An expected dataset answer alone cannot establish that.

Third, run adaptive unlearning. Manual mode runs the chosen method once. Automatic mode can use progress results to adjust another attempt within one shared allowance. Each new attempt starts from the original adapter.

Fourth, protect unrelated answers. During training, the system checks scores on unrelated examples. If the allowed harm is exceeded, it tries a smaller recent change or restores saved safe weights. It then stops that attempt.

Fifth, test recovery with controls. After choosing an adapter, the system compares its answers with the original target and the base model. It reports the target as absent, recovered, or unclear under those checks.

Sixth, provide live monitoring and cancellation. The interface shows the current stage, logs, and actual training updates. The user can cancel the job, and the saved status records how it ended.

Seventh, save experiment records and reports. The system keeps the request, settings, responses, scores, and adapter details. These records let someone inspect or compare the outcome later.

The main distinction is between checking before and checking after. Before training, we establish exposure. After training, we test what changed. The code links show how each function is implemented.

**If I lose my place:** The seven functions are to choose, check, train, protect, test, watch, and save.


## The system and its information flow

### Slide 20 Non functional requirements

**Remember:** Reliable operation

**Say:**

Functional requirements describe what the app does. This slide describes how reliably and clearly it should operate.

The system manages one training worker at a time. It limits attempts, actual updates, and training-loop time.

It records completed, failed, and cancelled jobs separately. Unique run IDs connect the settings to the result. These controls make experiments easier to trace and review.

**If I lose my place:** The app needs controlled resources, clear progress, and traceable results.

### Slide 21 System architecture

**Remember:** Follow the request

**Say:**

I will follow the request from left to right. The user selects facts in the browser. The interface sends the request to the Python server.

The server checks it and starts a separate worker. The worker prepares questions, checks the original model, and runs the ATU engine.

The engine manages training methods, progress questions, and checks on unrelated answers. It chooses an adapter that passes the required checks.

Final testing then produces responses and scores. Local files store the data, adapters, and results. The separate worker lets the server keep reporting progress and handle cancellation.

**If I lose my place:** The request moves from the browser to the server, training worker, and saved report.

### Slide 22 Data flow diagram

**Remember:** Inputs become evidence

**Say:**

This diagram follows the information. A request becomes selected questions and checked settings.

The original model produces exposure evidence. Training produces candidate adapters and progress results. The system chooses a candidate that passes the checks.

Final testing produces measured evidence, which is saved for the user. D one to D four represent local stored files.

Progress questions guide retries. Final questions are used after selection. They do not guide another attempt.

**If I lose my place:** The diagram shows how a selected request becomes saved test evidence.


## The two pseudocode slides

### Slide 23 Main ATU pseudocode

**Remember:** Start Try Check Choose

**Say:**

This is pseudocode, which means a readable outline of the real program. I will explain it in four parts.

First, load the original adapter and choose a plan. The plan contains the method and settings. The empty trials list will hold the results of our attempts.

Second, try training while the shared limits allow it. Each attempt reloads the original adapter. It does not continue from the previous attempt's changes.

Third, check progress questions and save the attempt. Manual mode stops after one attempt. Automatic mode can choose another attempt if progress is insufficient and limits remain.

Finally, choose an attempt that passes the safety checks. Ask the separate final questions and save the adapter, responses, and scores.

If no attempt passes the safety checks, the program returns that outcome. It does not promote an unsafe result.

**If I lose my place:** Start from the original, try training, check progress, then choose and test a safe result.

### Slide 24 Fact weight and safety pseudocode

**Remember:** Priority and smaller change

**Say:**

The left code controls training importance. A fact weight is the importance given to an example. It is different from the learned numbers inside the model.

If a progress question still reveals a fact, the controller gives that fact priority. It also checks the target answer score against a chosen threshold, called the floor.

When the score is low enough and the required progress checks have run without recovering the fact, the weight can decrease. These are development checks, not the separate final test.

The right code protects unrelated answers. It keeps a copy of trainable weights that passed the checks.

If a recent change causes too much harm, the code tries half, a quarter, and an eighth of that change. Each fraction reduces the change since the last saved safe version.

It restores a passing version and stops the current attempt. If none of the smaller versions passes, it returns to the saved safe weights.

**If I lose my place:** The left code changes fact priority, and the right code reduces or undoes a harmful change.


## Methods controls and the saved request

### Slide 25 Training methods

**Remember:** Different ways to change

**Say:**

The app offers five methods. ATU-NPO changes the importance of selected facts while training against their answers.

GradDiff trains against target answers and toward retain answers. Retain answers are examples we want to keep useful. RMU changes internal patterns.

The refusal method prefers a refusal over the target response. Gradient ascent directly trains against target answers and can damage other behavior.

Balanced automatic mode begins with ATU-NPO. A manual request keeps the selected method. Every method still needs response and quality checks.

**If I lose my place:** The methods change behavior in different ways, so I check both target and retain answers.

### Slide 26 Verification with controls

**Remember:** Base Original Changed

**Say:**

We compare three model states. The base is Qwen before our TOFU training. The original target is after TOFU training but before unlearning. The changed model uses the saved adapter after unlearning.

For a clean comparison here, the original target must reveal the fact and the base must not reveal it. We then check the changed model.

If the target is absent under those controls, the test supports suppression. If it appears, we report recovery. If the controls or answer are unclear, we report an inconclusive check.

The base is not a model retrained only on retained TOFU examples.

**If I lose my place:** The original establishes exposure, the base provides a control, and the changed model shows the result.

### Slide 27 Anaya request and settings

**Remember:** One fact One attempt

**Say:**

Now I will show the saved Anaya example. The request targets one award fact and manually selects ATU-NPO.

This is one method and one attempt. It demonstrates the manual path, rather than automatic method switching.

The training allowance is six hundred seconds. The full job took about four minutes twenty seconds. An allowance is a limit, rather than a required duration.

**If I lose my place:** This example manually targets one Anaya award fact with ATU-NPO.


## What the Anaya evidence shows

### Slide 28 Before and after answers

**Remember:** Missing award Wrong replacement

**Say:**

Before training, the model gives the Jannat Literary Award for Excellence in Criticism.

After training, it gives the Jawahar Literary Award. That replacement is false.

The original target award is absent in this tested answer. However, the model has not learned a truthful replacement. I report both observations because they describe different parts of the outcome.

**If I lose my place:** The target award stopped appearing in the test, but the replacement award is wrong.

### Slide 29 Unrelated answer quality

**Remember:** Separate follow up

**Say:**

This quality result comes from a separate Anaya follow-up on October twenty-seventh. It is separate from the main October twenty-sixth example.

The follow-up compared twenty-five unrelated answers before and after training. ROUGE-L measures shared word sequences with the expected answers. The average score was ninety-eight point eight percent both times.

That score does not check every possible meaning or establish that all model knowledge was preserved.

This small sample showed zero relative decline. It did not test all of Anaya's other facts.

**If I lose my place:** A separate follow-up found no average score decline on twenty-five unrelated answers.

### Slide 30 Actual training evidence

**Remember:** Updates Loop Whole job

**Say:**

The main Anaya record shows three actual optimizer updates. An optimizer update changes the trainable adapter numbers.

The kept adapter changed and was saved. The optimization loop took about twenty-two seconds.

The whole job took about four minutes twenty seconds because loading, preparation, answer generation, and saving add time.

These records establish that training happened. The response checks establish its measured effect. The update count alone cannot prove forgetting.

**If I lose my place:** Three updates changed the adapter, and response tests show what that change achieved.

### Slide 31 Controlled recovery result

**Remember:** Two prompts One fact

**Say:**

The original target reveals the award. The base does not reveal that award. The changed adapter also does not reveal it in the two tested prompts.

The saved audit therefore reports two passed checks for one fact. Two prompts are two wordings, rather than two forgotten facts.

The controls support that comparison. The false replacement remains visible, so suppression is not confused with truthful answering.

**If I lose my place:** Two controlled prompts stopped revealing one selected award fact.


## Comparisons software checks and contribution

### Slide 32 Baseline comparison

**Remember:** Same Qwen Different adapters

**Say:**

This table compares NPO, RMU, and GradDiff adapters on the same Qwen model.

Lower forget-answer overlap means less shared wording with target answers. Higher retain overlap means more shared wording with unrelated reference answers.

In this saved table, NPO has the lowest forget overlap, about zero point one five. RMU has the highest retain overlap, about zero point nine nine six.

This is an earlier comparison on a different group of test examples. It is separate from the single Anaya example and does not prove that current V3 is always better.

**If I lose my place:** The table shows a tradeoff between target-answer overlap and unrelated-answer overlap.

### Slide 33 Software tests

**Remember:** Program checks Model checks

**Say:**

The saved October twenty-seventh record reports three hundred nineteen Python tests and twenty-seven frontend tests passing. TypeScript checks and the production build also passed.

These check software behavior. They are different from testing whether a fact remains recoverable.

They are a dated verification record, rather than a fresh test of every later code change.

**If I lose my place:** Passing software tests supports the implementation, while response tests evaluate forgetting.

### Slide 34 Contribution

**Remember:** Connected working system

**Say:**

The main training ideas come from earlier research. My contribution is the working system that connects them.

It links fact selection to exposure checks, controlled training, checks on other answers, final testing, and saved evidence.

This lets us explain what changed, why an attempt stopped, and which records support the outcome.

**If I lose my place:** I built the system that connects fact selection, training, checking, and saved results.


## Limits next steps and closing

### Slide 35 Limitations

**Remember:** Tested scope

**Say:**

The experiments use one Qwen model and fictional author data. The recovery questions and unrelated examples are limited.

Another question or later training may bring a fact back. A missing target can also come with a false replacement, as we saw.

The unrelated checks do not establish that the same author's unselected facts were preserved. I therefore describe the result as tested suppression.

**If I lose my place:** The evidence covers the tested questions and sample, so I do not claim complete erasure.

### Slide 36 Conclusion and next steps

**Remember:** More facts Stronger tests

**Say:**

ATU v3 provides a working way to run and inspect selective unlearning experiments.

The next steps are to test more authors, repeat runs with different random seeds, and use stronger recovery questions.

I would also check unselected facts about the same author and compare methods under matching limits. These tests would show where the system works and where it still needs improvement.

**If I lose my place:** The system supports experiments, and the next step is broader testing.

### Slide 37 References one to four

**Remember:** Main research

**Say:**

These references identify the dataset and the earlier research behind the main unlearning methods.

**If I lose my place:** These are the sources for the main research methods.

### Slide 38 References five to seven

**Remember:** Answer quality

**Say:**

These sources discuss preference training, recoverable knowledge, and the quality of generated answers.

**If I lose my place:** These sources guided how I check the answers.

### Slide 39 References eight to ten

**Remember:** Stronger challenges

**Say:**

These sources cover real-world testing, relearning, and training-data extraction.

**If I lose my place:** These sources describe stronger challenges for future evaluation.

### Slide 40 Official sources and closing

**Remember:** Evidence and close

**Say:**

The final references are the official sources for the model, data, and software.

My main conclusion is that a changed answer needs clear supporting evidence. Thank you. I am ready for your questions.

**If I lose my place:** Thank you. I am ready for your questions.
