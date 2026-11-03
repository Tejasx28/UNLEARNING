# ATU presentation demos

Three new Full GPU experiments, with real updates, saved adapters and paired original/base controls.

**Open:** double-click `OPEN_PRESENTATION_DEMOS.bat` in the project root, or visit [Presentation demos](http://127.0.0.1:8000/#presentation-demos) while the dashboard is running. Opening a completed demo does not start training.

| Demo | Author | Suppressed / calibrated checks | Residual | Retain overlap | Runtime |
|---|---|---:|---:|---:|---:|
| demo-01 | Anaya Jehangir | 2/2 | 0 | 98.8% | 4m 20s |
| demo-02 | Bezabih Gebre | 2/2 | 0 | 96.4% | 4m 06s |
| demo-03 | Giorgi Meladze | 3/3 | 0 | 98.8% | 4m 00s |

## How to present

1. Open **Presentation demos** and select **Present evidence** on a completed case.
2. Show the selected author and exact facts. These are fictional TOFU benchmark profiles.
3. Show discovery, distinguishing stored reference answers from generated model exposure.
4. Show identical before/after prompts and inspect original-target/base-model controls.
5. Explain actual optimizer updates, automatic trial decisions and retain measurements.
6. Finish with coverage, residual/inconclusive checks and the exported provenance.

Use the existing presentation chapter controls or arrow keys to move through evidence. Exit returns to the collection. **Inspect report** opens the complete measured result.

### 01. A targeted award fact

**Anaya Jehangir** · `job_1793032377801_fa0d0688` · 4m 20s

Show original-model exposure, a real ATU-NPO update, and calibrated before/after recovery checks for one selected award fact.

Selected reference questions:

- What award has Anaya Jehangir been honored with in her career?

Measured outcome: **2/2 calibrated checks suppressed**, 0 residual recoveries, 0 inconclusive checks. Validated coverage: 1/1 selected facts. Retain answer overlap: 98.8% on 25 unrelated examples.

Actual methods: atu_npo. Selected method: atu_npo. Recorded optimizer updates across trials: 3. Outcome label: `SUCCESS`.

Evidence: [demo-01](./demo-01/result.json), [execution log](./demo-01/execution.log).

### 02. A personal-information request

**Bezabih Gebre** · `job_1793032725588_0374825f` · 4m 06s

Show a two-fact request, automatic method selection, retain safeguards and independently calibrated recovery checks on a different author.

Selected reference questions:

- When was Bezabih Gebre born?
- Who are the parents of Bezabih Gebre?

Measured outcome: **2/2 calibrated checks suppressed**, 0 residual recoveries, 1 inconclusive checks. Validated coverage: 2/2 selected facts. Retain answer overlap: 96.4% on 25 unrelated examples.

Actual methods: atu_npo. Selected method: atu_npo. Recorded optimizer updates across trials: 4. Outcome label: `SUCCESS`.

Evidence: [demo-02](./demo-02/result.json), [execution log](./demo-02/execution.log).

### 03. A guarded multi-fact request

**Giorgi Meladze** · `job_1793032981609_59d91492` · 4m 00s

Show bounded automatic trials on two distinct facts, checkpoint selection, measured retain preservation and honest final recovery evidence.

Selected reference questions:

- What profession did Giorgi Meladze's parents have?
- Can you name a major award won by author Giorgi Meladze?

Measured outcome: **3/3 calibrated checks suppressed**, 0 residual recoveries, 0 inconclusive checks. Validated coverage: 2/2 selected facts. Retain answer overlap: 98.8% on 25 unrelated examples.

Actual methods: atu_npo. Selected method: atu_npo. Recorded optimizer updates across trials: 4. Outcome label: `SUCCESS`.

Evidence: [demo-03](./demo-03/result.json), [execution log](./demo-03/execution.log).

## Scope to explain honestly

- Full mode includes the separate held-out engine evaluation and calibrated live audit. Each request used a 600-second shared training-loop ceiling and the default 0.03 retain limit. Early convergence can stop training before that ceiling.
- Each recovery check is a prompt, not a separate forgotten fact. Multiple checks can concern one selected fact.
- Suppression of the target answer can produce an incorrect replacement. Inspect raw answers and do not equate suppression with truthfulness.
- Retain answer overlap is a sample measurement, not the percentage of all knowledge preserved. Unselected facts about the same author are not established by this retain sample.
- Automatic mode may stop after the first safe converged method. It does not need to force a fallback to demonstrate correct operation.
- These are selected presentation cases, not an unbiased benchmark or a claim of complete deletion.
- The original target adapter hash is unchanged. All three selected adapters, settings, logs and outcomes are preserved.

See [summary.csv](./summary.csv), [verification.json](./verification.json), [collection.json](./collection.json) and each case folder for inspectable evidence.
