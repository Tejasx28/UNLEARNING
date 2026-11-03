# Functional Requirements and Slide Code Explained

Study this separately from the speech. It explains every functional requirement, the seven linked code excerpts, both pseudocode slides, and likely questions. Start with the seven actions below. Use the detailed pages when you need to explain how an action works.

## The seven functions

- FR1: Choose means select target facts and settings.
- FR2: Check before means check exposed facts.
- FR3: Train means run adaptive unlearning.
- FR4: Protect means protect unrelated answers.
- FR5: Test after means test recovery with controls.
- FR6: Watch means live monitoring and cancellation.
- FR7: Save means experiment records and reporting.

## FR1  Select target facts and settings

**What it does:** This requirement defines exactly what the experiment will target before any model training starts.

**Why it is needed:** A clear request lets us test the same selected facts before and after training. Checking the request early also avoids spending model time on invalid input.

**What happens:** The input is the author, selected facts, mode, method, and training limits. The backend checks them and produces a validated request. Quick mode supports up to five selected facts, and Full supports up to twenty.

**Example:** For the main Anaya run, select only the award question and choose manual ATU-NPO. Its saved zero-based index is 3, which means the fourth fact shown to a person.

### select_fact_indices and validate_options

rows = author.get('qa', []) reads the author's question-answer rows. If the qa entry is absent, [] supplies an empty list.

limit = 5 if mode == 'fast' else 20 chooses the permitted selection size. The backend name fast corresponds to Quick mode.

The validation rejects an empty explicit selection, wrong types, invalid indices, and duplicates. len(set(indices)) != len(indices) detects repeated numbers because a set keeps each number once.

raise ValueError(...) stops an invalid request with an error. return sorted(indices) returns the valid indices in order. validate_options also checks the supported methods, modes, and numerical settings.

**Evidence to point to:** Show the selected fact and saved request settings. A saved selection establishes what was requested, rather than proving that training succeeded.

**Limit to explain:** Selecting one fact does not establish that every unselected fact about the same author remains unchanged.

**Why validate again on the backend?** A request can reach the backend without using the screen. The backend therefore checks it too.

**Why select exact facts?** They define a precise target. I can then test the same information after training.

**What does index 3 mean?** It means the fourth fact because the code starts counting at zero.

Project source: src/live_requests.py


## FR2  Check exposed facts

**What it does:** This requirement checks whether the original target model actually reveals the selected fact before we change it.

**Why it is needed:** A dataset answer tells us the expected fact. Only an actual model response shows whether the model reveals that fact under a tested prompt.

**What happens:** The system takes candidate facts, creates test questions called probes, asks the original target model, and classifies the responses. It combines the probe results into a finding for each fact.

**Example:** Ask the original model about Anaya's award. Its Jannat award response is evidence of exposure under that question.

### Discovery probe loop and aggregation

for fact in candidate_facts visits each selected fact. generate_probes_for_fact prepares its questions.

The inner for probe in probes loop asks each question. _execute_probe generates and classifies the response.

_aggregate_fact_evidence combines the responses. exposure_score is the fraction of tested probes that recovered the fact.

The report can describe confirmed exposure, partial exposure, no observed exposure, or uncertainty. The matching logic uses explicit rules and text checks. It is not a separate trained language-model judge.

**Evidence to point to:** Show the actual question, original response, and recovery classification. These support the exposure finding more clearly than a summary label alone.

**Limit to explain:** No observed exposure means these prompts did not recover the fact. It does not prove that the model never learned it or that every other question will fail.

**Why check before training?** Otherwise, a missing answer afterward might be something the model never revealed in the first place.

**What is a probe?** It is a question or prompt used to test whether the model reveals a selected fact.

**Does discovery find every private fact?** No. It checks the supplied candidate facts using the generated probes.

Project source: src/discovery/engine.py


## FR3  Run adaptive unlearning

**What it does:** This requirement performs actual adapter training, using either one selected method or automatic attempts guided by measured progress.

**Why it is needed:** Changing a screen label or deleting a data row cannot undo the model's learned numbers. The system needs real training and evidence of the resulting behavior.

**What happens:** The engine prepares a method and settings, loads the original target adapter, trains, asks development questions, and saves the attempt. Automatic mode can adjust another attempt if the shared limits allow it. Manual mode runs once.

**Example:** The main Anaya request manually chose ATU-NPO. It ran one attempt with three real optimizer updates. It did not demonstrate automatic method switching.

### run_budget_loop and next attempt planning

current_method holds the current choice. copy.deepcopy(...) gives an attempt its own copy of settings.

fallback_queue stores alternative methods. A manual request has a trial limit of one and cannot silently switch to another method.

remaining_time = max(0.0, requested - used) subtracts time already used. Each retry does not receive a new full allowance.

_execute_method(...) performs training. The development result helps decide whether to stop or plan another attempt. Current code uses _plan_next_attempt. The retained short excerpt uses an older helper name, _adapt_strategy.

Every attempt reloads the original target and a fresh optimizer. The inner fact-priority controller applies specifically to ATU-NPO.

**Evidence to point to:** Show the selected method, attempt records, actual update count, and changed adapter. Then show response tests to explain the effect.

**Limit to explain:** Automatic routing uses practical rules, rather than a trained predictor of the best method. Training-loop time is separate from the duration of loading and final testing.

**What makes it adaptive?** It uses measured progress to change fact priority in ATU-NPO or plan another automatic attempt.

**Why restart from the original adapter?** Each attempt gets the same starting point and avoids inheriting changes from the previous attempt.

**Does automatic try all five methods?** No. It stops when conditions or limits require it. Full automatic mode normally permits up to three attempts, while Quick permits one.

Project source: src/atu/v3/budget_engine.py and src/atu/v3/engine.py


## FR4  Protect unrelated answers

**What it does:** This requirement checks whether training damages the measured unrelated answers too much, and recovers a passing set of weights when needed.

**Why it is needed:** Hiding a target by making the whole model worse would not meet the project's two goals. We need checks on behavior we want to keep.

**What happens:** The guard compares current reference-answer scores with the original scores on retain examples. It checks the average decline and the worst individual decline. Passing weights are saved. On failure, it tries smaller recent changes or restores saved safe weights, then stops that attempt.

**Example:** Suppose training hides the selected award but damages an unrelated answer. The guard can reject that change. This is an illustrative branch, not an event demonstrated by the main Anaya run.

### RetainGuard and its saved weights

measure_retain computes current reference-answer likelihood. initial_retain_lp - current measures the decline from the original baseline.

_individual_drop checks for damage that an average could hide. _safe checks the configured limits.

snapshot copies trainable adapter numbers. torch.lerp tries a fraction of the change from the saved safe numbers toward the rejected numbers.

restore copies an accepted state back. TrainingStopped ends the attempt after the guard intervenes. torch.no_grad means these copying operations do not build a gradient calculation.

**Evidence to point to:** Show guard measurements and the stopping reason. The main Anaya run kept changed weights without triggering rollback, so use it only for what its record demonstrates.

**Limit to explain:** The guard covers the measured sample. A limit of 0.03 nats per token is a log-probability allowance, not three percent accuracy loss. The generated-answer ROUGE check is a separate measurement.

**What is rollback?** It means restoring a previously saved set of weights that passed the checks.

**Why check individual examples?** A good average can hide serious damage to one answer.

**Does it protect all knowledge?** That is not established. It checks the stated sample, and it does not establish preservation of the target author's unselected facts.

Project source: src/atu/v3/safety.py


## FR5  Test recovery with controls

**What it does:** This requirement checks the selected adapter after training and uses comparison models to interpret the result.

**Why it is needed:** A missing answer can have several causes. Controls help establish that the original target revealed the fact and that the changed response represents a measured difference.

**What happens:** Ask matching recovery prompts of the original target, the untuned base, and the changed adapter. For a clean check here, the original must recover the fact and the base must not. The changed response is then classified as suppression, residual recovery, or inconclusive.

**Example:** The original reveals the Jannat award. The base does not. The changed adapter does not reveal it in the two tested prompts. That supports measured suppression of one fact. Its replacement Jawahar award is still false.

### Calibrated recovery classification

t_leaked records whether the original target fully or partly recovers the fact. b_clean records whether an available base response is classified as no recovery.

u_leaked records whether the changed model still recovers the fact. if t_leaked and b_clean checks the controls first.

With usable controls, NO_RECOVERY increments suppression and continued recovery increments residual leakage. Uncertain responses or inadequate controls increment inconclusive.

The program stores the before, base, and after responses together. Inconclusive checks do not count as demonstrated suppression. Coverage checks whether the selected facts were actually tested.

**Evidence to point to:** Show all three responses and the final prompt coverage. The main audit has two passing controlled prompts for one selected fact.

**Limit to explain:** The base is Qwen before the target TOFU training. It is not a model retrained on retain-only data. A passing suppression check proves neither complete deletion nor truthful replacement.

**How is FR5 different from FR2?** FR2 establishes exposure before training. FR5 tests the selected result after training using original and base controls.

**What is inconclusive?** The controls or response do not support a clear result. I do not count it as successful suppression.

**Why separate final questions?** Development questions influence retries. Final questions use separate wording after selection, while still testing the selected facts.

Project source: src/orchestrator/live_runner.py


## FR6  Live monitoring and cancellation

**What it does:** This requirement lets the user see what a job is doing and request that it stop.

**Why it is needed:** Model loading, checks, and training take time. The user needs useful progress and a clear execution outcome, even if the scientific goal is not achieved.

**What happens:** The worker sends structured progress events. The manager updates the stage, logs, elapsed time, and status. A cancellation request starts stopping the worker. The managed GPU slot stays occupied until the worker exits.

**Example:** The screen may show model preparation before any optimizer update occurs. Reconnecting to that screen after a refresh monitors the same backend job. It does not resume interrupted training.

### LiveJobManager progress and cancellation

ATU_EVENT marks a structured worker message. json.loads reads its data. Progress values are restricted to the range from zero to one hundred.

with self.lock protects shared job records against conflicting updates. A lock coordinates concurrent access to those records.

Cancellation sets cancel_requested and the CANCELLING status. process.terminate requests worker termination. A timer can force-stop a worker that remains running.

The slot is released after exit. The final record distinguishes completed, failed, and cancelled execution.

**Evidence to point to:** Show the stage, logs, actual update count, and recorded ending status. A complete progress bar says the process ended, rather than proving the fact was forgotten.

**Limit to explain:** Cancellation stops execution. It is not a guarantee of a usable partially trained result. The local manager permits one managed active training job at a time.

**Can I run two jobs at once?** The local manager allows one managed active training job. It avoids competing jobs in its GPU slot.

**What happens after a browser refresh?** I can reconnect to the backend job's monitoring. That differs from restarting or resuming training.

**Why separate completion from success?** A program can finish correctly while its model still reveals the target. Execution status and measured recovery answer different questions.

Project source: src/live_jobs.py


## FR7  Experiment records and reporting

**What it does:** This requirement preserves available experiment settings and evidence so the result can be reopened, compared, and exported.

**Why it is needed:** A success label alone cannot explain an experiment. A reviewer needs the facts, model identity, settings, responses, and measurements that produced the result.

**What happens:** The backend saves job and result files. The interface reads saved history, presents comparisons, and exports structured records. Each run has its own identity.

**Example:** Reopen the Anaya job and inspect the award selection, manual ATU-NPO setting, three updates, adapter, and recorded responses. Keep the separate quality follow-up clearly identified.

### _save and history with downloadJson

_save writes a job's state to job.json. history returns the available saved job records. Current code skips unreadable incomplete records while preserving their files.

JSON.stringify(value, null, 2) converts data to readable JSON text, using two spaces for indentation.

Blob prepares downloadable data. URL.createObjectURL creates a temporary browser address. A temporary link starts the download.

URL.revokeObjectURL releases that temporary address afterward. It does not delete the saved experiment.

**Evidence to point to:** Show the saved request, result, raw responses, and checkpoint identity. These establish provenance, meaning the record of how the result was produced.

**Limit to explain:** Comparisons across different facts, model checkpoints, or test coverage are descriptive. Exporting results does not deploy a changed model or guarantee identical future execution.

**Why save raw responses?** They let a reviewer inspect the evidence rather than rely only on a summary score.

**Can I compare any two runs fairly?** I must check whether targets, models, and evaluation coverage match. Different conditions can explain different scores.

**What does the export contain?** It contains the available request settings, selected facts, measurements, responses, trial details, and checkpoint identity.

Project source: src/live_jobs.py and frontend/app/src/services/research.ts


## Slide 23 Main process

```text
 1 ALGORITHM ATU(request):
 2     original = load_original_adapter()
 3     plan = choose_method_and_settings(request)
 4     trials = []
 5     WHILE shared_limits_allow_next_trial():
 6         model = reload(original)
 7         result = train_with_safety_checks(model, plan)
 8         dev = test_progress_questions(model)
 9         trials.append(save_attempt(model, dev, result))
10         IF manual_mode OR forgetting_and_safety_pass(dev):
11             BREAK
12         plan = choose_next_attempt_from_DEV(trials)
13     best = select_safe_attempt(trials)
14     IF best is missing: RETURN no_safe_result
15     final = test_separate_final_questions(best)
16     RETURN save_adapter_responses_and_scores(best, final)
```

### Lines 1 to 4 prepare the request
request contains the selected facts and settings. original is the target adapter before unlearning, after TOFU training. plan is the method and its settings. trials = [] creates an empty list for attempts.

### Lines 5 and 6 start a fresh attempt
WHILE repeats only when the shared time, update, and attempt limits permit it. reload(original) starts from the same original target. The next attempt does not inherit the previous candidate's changes.

### Lines 7 to 9 train check and record
The program trains with safety checks, asks development questions, and saves that attempt. append adds its saved record to the trials list.

### Lines 10 to 12 decide whether to repeat
OR means either condition is enough. Manual mode ends after one attempt. Automatic mode can stop when the required development conditions pass or plan another attempt if limits remain. BREAK leaves the loop.

### Lines 13 and 14 select an eligible result
The selector first needs an attempt that passes the configured safety conditions. best means the chosen result among recorded attempts, rather than the best possible model. If none qualifies, return that outcome.

### Lines 15 and 16 test and finish
Final questions use separate wording after selection. They do not guide retries. RETURN ends the function and provides the saved adapter, responses, and scores.


## Slide 24 Fact priority

```text
 1 FUNCTION fact_weight(fact):
 2     score = mean_answer_log_probability(fact)
 3     IF progress_test_recovers(fact):
 4         RETURN stronger_weight
 5     IF score <= fact.floor AND tests_finished:
 6         RETURN reduced_weight
 7     IF score > stubborn_limit:
 8         RETURN stubborn_weight
 9     RETURN weight_from_gap_to_floor(fact)
```

**Lines 1 and 2 measure the target answer:** A fact weight is training importance. A model weight is a learned number. score measures the supplied answer's log-probability, averaged over answer tokens. It is not a verbal confidence statement from the model.

**Lines 3 and 4 prioritize actual recovery:** If a development response still reveals the fact, the controller gives it priority. A low score for one reference answer can miss a different wording that still reveals the fact.

**Lines 5 and 6 reduce pressure after the checks:** <= means less than or equal to. floor is the chosen cutoff. AND requires both conditions. The earlier recovery branch has already ruled out observed recovery. tests_finished means the scheduled development checks have run, not that final evaluation has happened.

**Lines 7 and 8 identify a stubborn target:** > means greater than. A target answer above the stubborn limit is still relatively likely and receives its configured priority.

**Line 9 handles the remaining cases:** The controller uses the gap between the current score and floor to adjust training importance. The actual optimizer uses the weighted loss to update adapter numbers.


## Slide 24 Safety check

```text
 1 FUNCTION safety_check(model, safe):
 2     IF loss_limits_pass(model):
 3         RETURN copy_trainable_weights(model)
 4     rejected = copy_trainable_weights(model)
 5     FOR part IN [0.5, 0.25, 0.125]:
 6         model = mix_weights(safe, rejected, part)
 7         IF loss_limits_pass(model):
 8             safe = copy_trainable_weights(model)
 9             BREAK
10     restore(safe)
11     STOP current_attempt
12 # safe starts as the original weights
```

**Lines 1 to 3 save a passing state:** safe is a saved copy of trainable adapter weights. If the current unrelated-example checks pass, the code returns a copy as the latest safe state.

**Lines 4 to 6 try a smaller recent change:** rejected holds the candidate that failed. The fractions mean one half, one quarter, and one eighth of the change since the saved safe state. They are not allowed percentages of accuracy loss.

**Lines 7 to 9 accept only a passing candidate:** Each candidate faces the same original baseline and limits. If it passes, save it and BREAK out of the fraction loop.

**Lines 10 to 12 restore and stop:** Restore the accepted smaller state, or the old safe state if none passed. STOP ends this attempt even when a smaller state passed. Before any changes, the original trainable weights provide the first saved state.


## Questions about the code

**Does automatic mean a learned best-method predictor?** No. The system uses explicit planning rules and measured development results.

**Are DEV and final questions about different facts?** They can concern the same selected facts using separate wording. DEV guides decisions. Final testing happens after those decisions.

**Why use answer scores and generated responses?** A low score for one reference answer can miss recovery through other wording. Generated responses provide another check.

**Does reaching the floor prove deletion?** No. It is a threshold used by the controller. Recovery questions and controls are still needed.

**Does a weight of 1.8 mean a 1.8 times larger update?** No. The weighted loss is normalized, and the optimizer combines it with other terms. I describe it as training priority, not an exact update multiplier.

**Why stop after a smaller safe change is found?** That is the guard's policy after a safety failure. Automatic mode may later start a fresh attempt if the remaining limits allow it.

**What if every attempt is unsafe?** The system does not promote an unsafe adapter as the result.

**Did the main Anaya run exercise every branch?** No. It used one manual ATU-NPO attempt, kept changed weights, and did not demonstrate rollback or method switching.


## Questions about the project and results

**What does the whole project do?** It tries to make selected facts harder to recover from a trained model. It checks unrelated answers and saves the evidence of what changed.

**What is your contribution?** I implemented the system that connects selection, exposure checks, controlled training, recovery evaluation, and saved reports. The main training ideas come from earlier research.

**Have you completely erased the award?** The award stopped appearing in the two tested controlled prompts. Those checks do not prove that every possible prompt will fail to recover it.

**Why is the new award wrong?** Training reduced the target response but did not teach a truthful replacement. I therefore report tested suppression and the false replacement separately.

**What does two out of two mean?** It means two checked prompts stopped revealing one selected fact. It does not mean two different facts were forgotten.

**Where does the 98.8 percent come from?** It is mean ROUGE-L on twenty-five unrelated answers in the separate October 27 follow-up. It was 0.988 before and after. It is not a score for all model knowledge.

**Why are the quality and main results from separate runs?** The October 26 main run did not record that paired original quality comparison. The October 27 follow-up did, so I identify it separately.


## Questions about timing claims and next steps

**Why twenty-two seconds and four minutes twenty seconds?** About twenty-two seconds measures the main optimization loop. The whole job also includes loading, preparation, generated answers, and saving.

**Are three updates enough to prove forgetting?** They establish actual adapter training in this example. The generated-answer tests show its measured effect. The update count alone cannot prove removal.

**What do the software test counts prove?** The October 27 record reports 319 Python and 27 frontend tests passing. They check software behavior. They are not successful forgetting experiments or a fresh test of every later change.

**Which method is best?** In the saved baseline table, NPO has the lowest target overlap and RMU has the highest retain overlap. That comparison does not establish a universal winner.

**Why LoRA and this dataset?** LoRA trains fewer numbers, which makes local experiments practical. TOFU provides fictional facts with known answers for controlled testing.

**What if a question is outside your tested scope?** I have not tested that condition. The evidence I can show is the selected fact, the saved responses, and the measured outcome. That broader claim would need a separate test.

**How would you improve it?** I would test more authors and seeds, add stronger recovery questions, check the target author's unselected facts, and compare methods under matching limits.


## Words used in these explanations

**Adapter:** Small trainable tables of numbers added to a model. This project trains LoRA adapters while keeping the base numbers fixed.

**Checkpoint:** A saved set of adapter or model numbers.

**Loss and optimizer:** Loss is a training objective score. The optimizer uses gradients to change trainable model numbers.

**Log probability and floor:** Log probability scores a specified answer. The floor is a chosen cutoff for that score. More negative scores indicate lower likelihood.

**Token and nat:** A token is a piece of text. A nat is the unit used for natural-log probability. Nats per token is not a percentage accuracy measure.

**Retain and utility:** Retain examples are examples whose behavior we want to keep useful. Utility means useful model behavior.

**ROUGE L:** A score based on shared word sequences between a generated answer and a reference answer. It is not a full test of meaning or truth.

**Two percent relative drop:** A permitted decline relative to the original score. From 0.90, a two percent relative decline gives 0.882.

**Control and inconclusive:** A control helps interpret a comparison. Inconclusive means the response or controls do not support a clear conclusion.

**Heuristic:** An explicit practical rule. It is not a learned predictor or a guarantee.

**Worker and lock:** A worker is a separate process doing the experiment. A lock coordinates access to shared job records.

**Provenance:** The record of which data, settings, models, and available code or scorer versions produced a result.

Uploaded deck: C:/Users/tejas/Downloads/UNL-PPT/4.pptx, especially slides 19, 23, and 24.

Linked FR snapshots: frontend/presentations/output/ATU_Implementation_Review/code/fr-01.html through fr-07.html. Current project functions are identified on the relevant pages.

Main result: results/live_jobs/job_1793032377801_fa0d0688/result.json. Separate quality follow-up: results/live_jobs/job_1793088345703_42838b54/result.json.

Historical comparison: results/baseline_comparison.csv. Dated software verification: results/feedback_validation_20261027/verification.json.
