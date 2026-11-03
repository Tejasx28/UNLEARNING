# Simple Speech for Every Slide

For the uploaded 4.pptx. The spoken text follows all 40 slides.

## Slide 1 Title

Good morning. I am Tejas. My project is Selective Knowledge Erasure in Large Language Models. The aim is to make chosen facts harder to get from a model while checking that its other answers remain useful.

## Slide 2 Abstract

My system is called ATU v3. It first checks what the model reveals. It then changes a small part of the model and tests the result. The report shows what changed and what information can still be found.

## Slide 3 Problem scenario

Anaya is a made-up author in our test data. The model remembers an award she received. We try to stop it from revealing that particular award. Deleting the data alone does not change what the model has already learned.

## Slide 4 Purpose and scope

The project has two goals. The first is to reduce answers that reveal the chosen fact. The second is to check that answers about other facts stay useful. I test this using fictional authors and one Qwen model.

## Slide 5 Background and research gap

Existing methods can change target answers, but they can also harm other answers. Another question may still reveal the target fact. My system checks these problems during training and tests the saved result.

## Slide 6 TOFU research paper

TOFU gives us fictional authors and known answers. This makes it easier to check what the model learned and what changes after unlearning.

## Slide 7 NPO research paper

NPO makes the target answer less likely, using the original model for comparison. ATU-NPO builds on this method.

## Slide 8 WMDP and RMU research paper

RMU changes patterns inside the model that are used when answering questions. My project includes this method and tests it on TOFU.

## Slide 9 Large Language Model Unlearning paper

This paper studies training that discourages unwanted answers while protecting other useful answers. It helped guide the methods used in this project.

## Slide 10 DPO research paper

DPO learns by comparing preferred and rejected answers. A similar idea in my project can make the model prefer a refusal over the target answer.

## Slide 11 Dissecting Fine Tuning Unlearning paper

This paper shows why a changed answer is not enough. A model may appear to forget, while another test can still bring the information back.

## Slide 12 ReLearn research paper

ReLearn also looks at whether the new answers make sense. It helped me understand why answer quality matters. My project does not implement ReLearn.

## Slide 13 RWKU research paper

RWKU tests facts about real people. It shows why tests on fictional authors are only a starting point. Real-world testing would be further work for this project.

## Slide 14 Relearning attacks research paper

This paper studies whether later training can bring back information after unlearning. My project does not yet test this. It is one possible next step.

## Slide 15 Training data extraction paper

This paper shows that a model can reveal text from its training data. It explains why we must test actual responses. Its extraction method is not implemented here.

## Slide 16 Dataset and model setup

TOFU has 200 fictional authors and 20 questions each, giving 4,000 question-answer pairs. I use Qwen2.5-1.5B-Instruct. Unlearning changes a small extra set of learned numbers called a LoRA adapter. The base model numbers stay fixed.

## Slide 17 Tools and technologies

React and TypeScript build the screens. Python manages requests and training. PyTorch does the training calculations. Transformers and PEFT load the model and its adapter. The system saves the results and the changed adapter in local files.

## Slide 18 Intended users

A researcher can choose facts and run experiments. A reviewer can check the answers, settings, and saved results. These describe who can use the system. Separate user login roles have not been added.

## Slide 19 Functional requirements

These seven functions cover the full experiment. The user chooses facts and settings. The system checks exposure, runs training, protects other answers, tests recovery, shows progress, and saves the results. Each function links to its code.

## Slide 20 Non functional requirements

The system runs one training process at a time. It limits the work and records whether a run finished, failed, or was stopped. Each run has its own saved details, so we can check what happened.

## Slide 21 System architecture

This diagram shows the main parts of the system. The user sends a request through the screen. The Python server starts a separate training process. That process checks the original model, runs training, and tests the result. Local files hold the data and saved results.

## Slide 22 Data flow diagram

This diagram shows how information moves. The request becomes selected questions and settings. Training produces changed adapters. The system chooses one that passes its safety checks, tests it, and saves the results. Final-test answers are not used to decide the next training attempt.

## Slide 23 Main ATU process

Every attempt starts again from the original adapter. The system trains and checks progress. A manually chosen method runs once. Automatic mode may change settings or try another method within the same limits. After choosing a safe result, it asks separate final questions.

## Slide 24 Fact weights and safety

If a progress question still reveals a fact, ATU-NPO gives that fact more importance during training. The system also checks other answers. If a change harms them too much, it tries a smaller change or restores saved weights, then stops that attempt.

## Slide 25 Unlearning methods

The methods work in different ways. ATU-NPO changes the importance given to each fact. GradDiff also trains on answers we want to keep. RMU changes internal patterns. Refusal training favors a refusal. Gradient ascent makes target answers less likely. We test each result.

## Slide 26 How the result is checked

We compare three versions. The original target must reveal the fact. The base model, before our TOFU training, must not reveal it for this comparison. We then test the changed adapter with the same question. If the checks are unclear, we report that uncertainty.

## Slide 27 Selected fact and settings

This saved Anaya experiment selects one award fact and one method, ATU-NPO. It therefore runs one attempt. The training limit is 600 seconds. The complete recorded job took about four minutes and twenty seconds.

## Slide 28 Answers before and after

Before training, the answer gives the Jannat award. After training, it gives a different award that is wrong. The chosen award is absent from this response. This shows a change in the tested answer, but it does not make the replacement true.

## Slide 29 Check unrelated answers

This slide shows a separate Anaya follow-up. We asked the same 25 unrelated questions before and after training. The average score for matching the wording of the reference answers was 98.8 percent both times. It describes those answers, not all model knowledge.

## Slide 30 Actual training and saved result

Returning to the main example, the training made three actual updates to the adapter. This training took about 22 seconds. The full job took longer because it also loaded models and ran tests. The original adapter was kept separately.

## Slide 31 Why the controls matter

Here, the original target gives the chosen award, while the base model does not. After training, the changed adapter also does not give that award in the two tested prompts. These are two checks of one selected fact. The wrong replacement remains a limitation.

## Slide 32 Three trained adapters

These are three differently trained adapters on the same Qwen model. In these saved tests, NPO repeated less of the target answers. RMU matched more of the unrelated reference answers. The scores show different strengths. They do not prove that one method is always best.

## Slide 33 Software testing

The saved October 27 record shows that 319 Python tests and 27 frontend tests passed. The app build also passed. These tests check the software. Separate model-response tests check what happened to the selected facts.

## Slide 34 Project contribution

My contribution is the working system that brings these steps together. It checks exposed facts, controls training attempts, checks other answers, and saves final evidence. NPO, RMU, and the other main training ideas come from earlier research.

## Slide 35 Limitations

This project uses one model, fictional data, and a limited number of test questions. A different question or later training may still bring back a fact. The results therefore show what happened in our tests, rather than proving complete removal.

## Slide 36 Conclusion and next steps

ATU v3 helps us run unlearning experiments and explain their results. Some tested facts stop appearing, while harder cases still reveal information. Next, I would test more authors, repeat the experiments, and check other facts about the same author.

## Slide 37 References one to four

These sources explain the dataset and the main unlearning methods.

## Slide 38 References five to seven

These sources discuss preferred answers, remaining information, and answer quality.

## Slide 39 References eight to ten

These sources cover real-world facts, relearning, and training-data exposure.

## Slide 40 Official sources and closing

These are the official sources for the model, dataset, and software. Thank you. I am ready to answer your questions.
