# Selective Knowledge Erasure Presentation Speech and Answers

For 4.pptx  |  40 slides  |  10 to 12 minutes

Read the speech on pages 2 to 6. The answer bank is for preparation and questions only. You do not need to memorize this whole document.

## Remember the route

CHECK what the model reveals. CHANGE the selected adapter. CHECK other answers. TEST the chosen result. SHOW the evidence.

If you remember only one sentence: The project tries to make chosen facts harder to recover, checks sampled unrelated answers, and shows the measured evidence.

## How to use the script

Learn the opening and closing. For each other slide, remember the cue and explain its main idea. Exact wording is optional.

Read each literature slide in one short sentence. Do not read author lists, the full abstract, code lines, or every table value aloud.

Pause after the main point. Look at the panel, then use the next cue. A short pause is allowed.

Rehearse once with a timer. Aim to finish around 11 minutes, leaving room for slower slide changes. If interrupted, resume at the next cue.

## If your mind goes blank

Pause and look at the slide title. Say: “The main point here is…” Then give just the cue in one sentence. Move on when that point is clear.

If a question is unclear: “Are you asking about the training method or how I verified the result?” If you need a moment: “Let me separate those two parts.”

## Keep these distinctions clear

One selected fact has two final checks. The 98.8 percent result describes 25 answers in a separate follow-up. A missing target with a false replacement is suppression, not a truthful answer. The three comparison adapters share one Qwen backbone.

Prepared 1 November 2026. Slide numbers follow the uploaded file. Your PPT is unchanged.

## Speech part 1 The problem and first papers

Target time 0 to 2 minutes

Read only the spoken paragraphs. Cues are reminders for you.

### Slide 1 Title

Cue: Problem and goal

Good morning. I am Tejas. My project is Selective Knowledge Erasure in Large Language Models. It studies how to make chosen facts harder to recover while checking that unrelated answers remain useful.

### Slide 2 Abstract

Cue: Check then change then test

The system is called ATU v3. It checks what the original model reveals, updates a small adapter, and tests the result. The report shows whether the target was absent in answers, remained recoverable, or could not be judged.

### Slide 3 Problem scenario

Cue: Anaya and the award

Here, Anaya is a fictional author. Her model response reveals a particular literary award. The request targets that award fact. Removing the source data alone does not undo what the model has already learned.

### Slide 4 Purpose and scope

Cue: Selected facts and measured scope

The goal is selective change with checks on other answers. This project tests fictional TOFU profiles using one Qwen model. Its conclusions apply to the selected facts and the tests performed.

### Slide 5 Background and research gap

Cue: Training needs control

Existing methods can reduce target answers, but they may damage useful behavior or leave information recoverable. My project combines these methods with progress checks, safety limits, and inspectable results.

### Slide 6 TOFU paper

TOFU provides fictional profiles with known answers, making controlled forgetting experiments possible.

### Slide 7 NPO paper

NPO reduces preference for target answers relative to the original model. It underlies ATU-NPO.

### Slide 8 WMDP and RMU paper

RMU changes internal model representations. I implement this alternative and test it on TOFU.

### Slide 9 Large Language Model Unlearning paper

This work motivates training against unwanted answers while protecting useful behavior.

### Slide 10 DPO paper

DPO motivates preference-based training. In this project, a preference-style objective can favor refusal answers.

## Speech part 2 Background and setup

Target time 2 to 4 minutes

Literature slides stay brief. Explain relevance instead of reciting publication details.

### Slide 11 Dissecting Fine Tuning Unlearning paper

This study motivates a key precaution: apparent forgetting can still leave information recoverable.

### Slide 12 ReLearn paper

ReLearn highlights generated-answer quality. It is background research and is not implemented here.

### Slide 13 RWKU paper

RWKU tests real-world facts. It motivates broader evaluation beyond this fictional-author setup.

### Slide 14 Relearning attacks paper

This work shows why later training needs separate testing. Relearning resistance is future work here.

### Slide 15 Training data extraction paper

The extraction study motivates checking what models actually reveal. Its extraction pipeline is not implemented.

### Slide 16 Dataset and model setup

Cue: 200 times 20

TOFU contains 200 fictional profiles with 20 questions each, giving 4,000 reference pairs. I use Qwen2.5-1.5B-Instruct. During unlearning, small LoRA adapter weights change while the base weights stay frozen.

### Slide 17 Tools and technologies

Cue: Interface Python GPU files

React and TypeScript provide the interface. Python manages requests and training processes. PyTorch performs optimization, and Transformers with PEFT load the model and adapters. JSON files and adapter files preserve the results.

### Slide 18 Intended users

Cue: Researcher and reviewer

A researcher runs experiments. Evaluators and supervisors inspect the responses, settings, and saved evidence. These are intended user groups. Separate login roles are not implemented.

### Slide 19 Functional requirements

Cue: Request through report

The seven functions cover selecting facts, checking exposure, running unlearning, protecting unrelated answers, testing recovery, monitoring execution, and saving reports. Each function links to its implementation.

### Slide 20 Non functional requirements

Cue: Limits and traceability

The system manages one training worker at a time. It limits work, records how each run ends, and saves unique run details so the result can be traced.

## Speech part 3 How the system works

Target time 4 to 6 minutes 30 seconds

### Slide 21 System architecture

Cue: Left to right

Read this diagram from left to right. The user submits a request through the interface. The Python backend starts a separate worker. That worker runs discovery, checked training, and final evaluation. Local files store the data, adapters, and reports.

### Slide 22 Data flow diagram

Cue: Request to saved evidence

This diagram follows the data. A validated request becomes selected questions and settings. Training produces candidate adapters. The chosen adapter is tested, and the results are saved for review. Final-test results do not guide retries.

### Slide 23 Main ATU pseudocode

Cue: Fresh attempt and separate final test

Each attempt starts from the original adapter. The system trains with safety checks and measures progress. Manual mode runs one method once. Automatic mode may adjust settings or switch methods within shared limits. It then selects a safe result and runs separate final questions.

### Slide 24 Fact weights and safety pseudocode

Cue: More pressure and safe restoration

ATU-NPO gives more pressure to facts still recovered by progress questions. It reduces pressure when the required checks pass. The safety guard checks unrelated answers. If an update causes too much measured harm, it tries smaller changes, restores safe weights, and stops that attempt.

### Slide 25 Unlearning methods

Cue: Different ways to change behavior

The methods use different mechanisms. ATU-NPO adjusts target pressure. GradDiff also trains toward unrelated answers. RMU changes internal representations. Refusal training favors refusal, and gradient ascent makes target answers less likely. Every candidate still needs evaluation.

### Slide 26 How the result is checked

Cue: Original base changed

The original target must reveal the fact. The untuned base must not reveal it for this calibrated comparison. We then ask the changed adapter the same question. Unclear controls remain inconclusive. Other-answer quality is measured separately.

## Speech part 4 The evidence

Target time 6 minutes 30 seconds to 9 minutes 30 seconds

Use the embedded screenshots. Opening extra windows is optional and adds time.

### Slide 27 Selected fact and settings

Cue: One fact and one chosen method

This saved Anaya example targets one award fact using manually selected ATU-NPO. It runs once. The training limit is 600 seconds, while the complete recorded job took about four minutes twenty seconds.

### Slide 28 Answers before and after

Cue: Jannat absent and replacement wrong

Before training, the model gives the Jannat award. After training, it gives a different, incorrect award. The target is absent in this response. The replacement is still wrong, so suppression and truthful answering are separate findings.

### Slide 29 Unrelated answer quality

Cue: Separate run and 25 answers

This slide uses a separate Anaya follow-up. On the same 25 unrelated questions, mean ROUGE-L was 98.8 percent before and after. That measures reference-answer overlap on this sample, rather than the percentage of all knowledge preserved.

### Slide 30 Actual training and saved result

Cue: Three updates and 22 seconds

Returning to the main example, three optimizer updates changed the adapter. Training took about 22 seconds. The complete job also included startup, model loading, and testing. The original adapter remains separate.

### Slide 31 Why the controls matter

Cue: Two checks of one fact

The original reveals the selected award, the base does not, and the changed adapter does not reveal it in the tested prompts. The saved audit has two calibrated checks for one fact. This establishes measured suppression within that scope.

### Slide 32 Three trained adapters

Cue: One backbone and three variants

These are three trained adapters on one Qwen backbone. In the saved comparison, NPO has lower target overlap, while RMU has higher unrelated-answer overlap. The methods show different tradeoffs. This historical table does not establish that current ATU v3 is universally better.

### Slide 33 Software testing

Cue: Code checks and model checks differ

The dated verification record reports 319 Python tests and 27 frontend tests passing, plus the production build. These check implementation behavior. Response tests separately assess forgetting.

## Speech part 5 Contribution and close

Target finish about 11 minutes

### Slide 34 Project contribution

Cue: The integrated control workflow

My contribution is the implemented control and evidence workflow around established methods. It connects exposure checks, bounded fresh attempts, safety, selection, and saved final evidence. NPO and RMU come from prior research.

### Slide 35 Limitations

Cue: State the boundary clearly

Evaluation uses one model and fictional data. It covers limited recovery prompts and sampled unrelated answers. The system does not establish complete deletion. Stronger prompts or later training may recover information.

### Slide 36 Conclusion and next steps

Cue: What changed and what remains

ATU v3 makes selective unlearning experiments easier to run and inspect. Some tested facts stop appearing, while harder cases retain recoverable information. Next steps are more authors and repeated runs, stronger recovery tests, and checks on unselected facts about the same author.

### Slide 37 References 1 to 4

These references support the dataset and unlearning methods.

### Slide 38 References 5 to 7

These cover preference training, recoverability, and answer quality.

### Slide 39 References 8 to 10

These cover real-world facts, relearning, and extraction.

### Slide 40 Official sources and close

Cue: Finish and pause

The final references document the model, dataset, and tools. Thank you. I am ready for your questions.

### Optional invitations to prepared questions

Use at most one, and only if time remains. You can guide attention honestly, but cannot control which question the panel chooses.

At slide 31: “The difference between two checks and one fact is important here.” Be ready to explain that both prompts test the same selected QA entry.

At slide 29: “The 98.8 percent score has a specific meaning.” Be ready to explain reference overlap on 25 unrelated answers, from a separate follow-up.

### If time is running short

Keep the Anaya example, its wrong replacement, the separate quality check, and the conclusion. Summarize remaining background in one sentence. Do not rush the limitations or read the references aloud.

### Private evidence reminders

Main Anaya: run suffix fa0d0688, 26 October. Quality follow-up: 42838b54, 27 October. Main facts: one QA, two checks, three updates, about 22 seconds training, about 4 minutes 20 seconds whole job.

## Prepared questions essential answers

Start with these ten. Answer directly in two or three sentences, then stop. Show the record if they want evidence. No list can predict every question.

### What does your project do

It attempts to make selected learned facts harder to recover, checks sampled unrelated answers, and saves the original and changed-model evidence.

### What did you contribute if NPO and RMU already exist

The implemented contribution is the control workflow: exposure checks, adaptive pressure, fresh bounded attempts, utility protection, selection, and traceable final reporting. I do not claim a new base objective.

### Have you completely deleted the fact

The tested prompts show suppression of the selected fact. Complete deletion would require stronger evidence than these finite response tests provide.

### Why is a wrong replacement answer called success

The saved success label means the configured suppression and safety checks passed. The replacement is still false. Truthfulness needs a separate criterion, so I report both observations.

### What does two out of two mean

Two calibrated recovery prompts tested one selected QA entry. Both stopped revealing its target award. It does not mean two facts or universal success.

### Does ninety eight point eight percent mean all knowledge was preserved

It is mean ROUGE-L against references on 25 unrelated questions. The follow-up had the same score before and after. It is a sample-based overlap measurement.

### Why is the quality slide from another run

The main October 26 record lacks the paired generated-quality baseline. The October 27 follow-up records before-and-after quality. I keep those runs separate.

### Why do you need the base model as well as the original target

The target shows exposure after TOFU training. A clean untuned-base response supports that comparison. The unlearned response then shows what changed under the same question.

### Why only one attempt in the example

The request explicitly chose ATU-NPO. Manual selection runs that method once. Automatic Full mode can use permitted retries or alternatives under shared limits.

### Is your method selector itself an AI model

It uses explicit heuristic rules and a candidate order. Development measurements judge the attempts. It is not a trained predictor of the best method.

## Prepared questions training and implementation

### What does ATU stand for

Adaptive Targeted Unlearning. It adjusts forgetting pressure using target likelihood and development recovery. V3 adds the outer execution and selection workflow.

### What is the difference between base target and changed model

The base is Qwen before TOFU adaptation. The target attaches the original TOFU adapter. The changed model attaches a modified adapter produced by unlearning.

### Why LoRA and what do rank 32 and alpha 64 mean

LoRA trains small additional matrices to reduce training cost. Rank controls their size, and alpha scales the update. These saved settings are not claimed to be optimal.

### Explain NPO simply

NPO reduces preference for a target answer relative to its original-target likelihood. Retain training anchors unrelated answers. ATU-NPO also changes pressure using target state and progress probes.

### How are the methods different

GA trains against target answers. GradDiff also trains toward retain answers. NPO uses an original reference. RMU steers hidden representations. Refusal preference favors a refusal over the target answer.

### Is your refusal method exactly original DPO

It is a reference-free DPO or SimPO-style preference implementation. It favors refusal and includes retain terms. I use the DPO name as the project method label, with that distinction.

### What makes ATU adaptive

Inside ATU-NPO, target likelihood and development recovery adjust fact weights. The V3 outer loop can also change settings or methods using development results and remaining limits.

### What are the score and floor

The score is mean token log-probability of the reference answer. The floor is a threshold, normally based on that answer under the untuned base plus tolerance in live V3.

### How do retries work

Every attempt reloads the original target with a fresh optimizer. A promising NPO attempt may get one settings retry while reserving an alternative. All attempts share the request limits.

### How does the safety guard work

It compares sampled retain likelihood with a fixed original baseline. On a breach, it tests smaller fractions of the last change, restores safe weights, and stops the attempt.

### Why half a quarter and an eighth

They are fixed backtracking choices for the last update interval. Each must pass the same original safety limits. They are engineering choices, not proven optimal fractions.

## Prepared questions measurements and difficult follow ups

### What is ROUGE L

It measures word-sequence overlap between a generated answer and a reference, using the longest common subsequence. It is useful for comparison but does not establish complete semantic accuracy.

### Does the training guard use ROUGE L

The step guard checks mean and individual retain likelihood decline. Generated-answer ROUGE-L is a separate trial/final quality check. The two checks measure different things.

### What does the two percent quality allowance mean

It is relative decline from original mean ROUGE-L on the same cohort. Starting at 0.90, a two percent allowance permits 0.882. It is separate from likelihood limits.

### What does the zero point zero three retain limit measure

It limits average reference-answer log-probability decline in nats per token. It is a likelihood limit, separate from the two percent generated-answer quality allowance.

### Why are three updates enough

They show that this adapter really changed. The response tests determine the observed effect. The update count alone cannot establish forgetting, and harder requests can need more work.

### Why 22 seconds of training but about four minutes twenty total

Those are different scopes. The main job also includes process startup, loading, discovery, evaluation, and saving. A training budget is not a whole-job deadline.

### Why can a 600 second budget be exceeded in wall time

The allowance is shared across training loops. Preparation and final audits add time. Checks are cooperative, so an operation already running can cross a boundary.

### Are NPO RMU and GradDiff three different LLMs

They are three separately trained adapter variants on the same Qwen backbone. This is a method comparison on one model family.

### Which method is best in slide 32

NPO has lower target overlap among those three; RMU preserves more unrelated overlap. Best depends on the joint criteria, raw responses, and protocol. The table alone gives no universal winner.

### Could another prompt still recover the fact

Yes, that remains possible. We test separate final questions, but finite tests cannot cover every attack. Stronger recovery and relearning tests are further work.

### Are other facts about the same author preserved

That is not established here. The author is excluded from the unrelated retain cohort. Explicit same-author collateral checks are an important next evaluation.

### How reliable is the recovery classifier

It uses deterministic content matching, boundaries, and limited aliases, with uncertain outputs reported separately. Broader human-labeled precision and recall evaluation would strengthen confidence.

## Prepared questions scope research and practical questions

### How do you avoid testing on the questions used for adaptation

Development prompts guide the loop; separately worded final prompts run after selection and never choose retries. They still test the same requested facts, so independence has that limit.

### Can retain validation certify generalization

It constrains checkpoint selection, so it is validation rather than an independent broad capability benchmark. The report states the sample and metric.

### Why choose TOFU and this Qwen model

TOFU provides known fictional targets without using real private biographies. This Qwen model with LoRA fits the local experimental scope. Generalization to other models remains untested.

### Why show a single successful example

It gives a clear implementation walkthrough. It is not a random benchmark. Harder saved multi-fact cases retain recoveries, so I do not infer overall success from this example.

### Is V3 proven better than V2

No general superiority is established. The matched study improves some measured suppression counts but remains partial. Multiple authors, seeds, strong baselines, and ablations are needed.

### Does your project equal retraining without the forget data

That equivalence has not been shown. The untuned base is a control before TOFU adaptation, not a model retrained only on retained TOFU examples.

### Why not just block the question or remove the data

Blocking controls an interface and can miss rewordings. Removing source data leaves learned parameters unchanged. This project updates adapter parameters and then measures recoverability.

### What happens if every attempt is unsafe

The engine does not promote a checkpoint that fails its safety requirements. It records the failure or keeps eligible restored behavior rather than presenting damage as successful forgetting.

### How do you prove it actually trained

The record includes optimizer updates, kept-parameter changes, saved adapter identity, and raw responses. Updates plus a changed kept adapter establish real training, while the tests establish its observed effect.

### Can the original model or data be recovered from this project

The original adapter and dataset remain available for research comparison. This experiment tests one changed checkpoint; it is not a secure erasure process for all copies or saved artifacts.

## Prepared questions extra questions if the panel goes deeper

### What happens on cancellation or backend restart

The manager terminates its owned worker and records cancellation after exit. An interrupted active job is marked failed on restart. Training does not automatically resume.

### Can it process arbitrary personal information

The custom builder accepts candidate facts, but the model must first show exposure for calibrated forgetting evidence. The workflow does not teach those new facts before trying to unlearn them.

### Can this run on CPU and what hardware did you use

The project supports CPU paths, though full experiments can be slow. Historical training used an RTX 4060 Laptop GPU. Peak memory depends on method, batch, and evaluation workload.

### What do the 319 tests prove

They are the saved October 27 software verification count. They check code behavior under those cases. They are not 319 successful forgetting experiments or a fresh run of today's code.

### What is the next experiment you would run

Freeze the policy, use multiple held-out authors and seeds, test stronger recovery prompts and same-author facts, and compare joint forgetting and utility against matched fixed methods.

### What if you do not know an exact number or an untested result

I have not established that result in this evaluation. The saved record can confirm the exact measurement. To answer the broader question, I would need the corresponding controlled experiment.
