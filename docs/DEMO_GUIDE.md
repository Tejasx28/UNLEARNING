# ATU Studio demonstration guide

## New three-run presentation collection

Three new Full GPU experiments are saved together under **Presentation demos**. Double-click `OPEN_PRESENTATION_DEMOS.bat` in the project root, or open [the collection](http://127.0.0.1:8000/#presentation-demos) while the dashboard is running. Each case opens the existing evidence presentation and complete report without starting new training.

See [the measured results and walkthrough](../results/presentation_demo_20261026/README.md) for Anaya Jehangir, Bezabih Gebre and Giorgi Meladze, including actual run IDs, coverage, residual/inconclusive checks and the unchanged original-adapter hash. These are selected presentation cases, not a random benchmark.

The recommended demonstration uses genuine saved experiment evidence. Present it as a completed experiment that the audience can inspect; opening the presentation does not run a new GPU experiment.

## Open the dashboard

Double-click `launch_dashboard.bat` in the project root, then open [ATU Studio](http://127.0.0.1:8000/). An alternative is `npm.cmd start` from `frontend/`. Reopening the launcher reuses an already healthy dashboard.

On **Overview**, choose **Present saved evidence** or **Present this experiment**. The featured record favors a completed Full experiment with an available result; it is not chosen by whether its outcome succeeded. For a specific record, open **Run history**, choose the run, then use **Present evidence** in the top bar. Confirm the author, mode and run ID before presenting.

## A professional three-minute walkthrough

Use the saved Anaya Jehangir Full experiment `job_1792649059798_c1cde415` as a small, clearly scoped example.

| Chapter | What to show | What to say |
|---|---|---|
| **1. The request** | Author, selected fact count, actual method and saved execution scope | “This experiment targets one award fact in a TOFU fictional-author profile. The original target checkpoint is preserved.” |
| **2. Discover exposure** | Dataset reference, actual question and original-model response | “The answer key is reference data. This generated response is the evidence that the model revealed the target information.” |
| **3. Compare responses** | The identical prompt before and after unlearning, with its calibrated label | “We compare actual responses and check original-target and base-model controls. Failure to recover the target answer is distinct from producing a factually correct answer.” |
| **4. Measure the outcome** | Suppression counts, residual recovery, retain overlap, update counts and inconclusive checks | “Two of two calibrated recovery checks were suppressed. The selected fact has validated coverage. Retain answer overlap was 98.8% on 25 unrelated examples.” |
| **5. Evidence & boundaries** | Fact coverage, checkpoint identities, scoring revision and limitations | “This supports a result for this selected fact and these tested questions. It does not prove universal forgetting across every author or every possible attack.” |

Use **← / →** to move between chapters, **Home / End** to jump to the first or last chapter, and **Escape** to exit. The numbered chapter buttons and bottom progress buttons also navigate. Arrow keys inside the question selector retain normal selection behavior. **Exit presentation** closes the walkthrough; **Inspect the full report** or the final **Return to full report** control opens the selected run's results.

The comparison chapter lets you select any exported matching question. If residual leakage exists, the initial comparison favors that evidence rather than hiding it behind a successful example. Missing measurements appear as unavailable rather than zero.

## Verified scope of the main example

The source is [the saved result](../results/live_jobs/job_1792649059798_c1cde415/result.json):

- **Method:** ATU-NPO, Full experiment.
- **Selected question:** “What award has Anaya Jehangir been honored with in her career?”
- **Target coverage:** 1 of 1 selected facts had validated checks.
- **Recovery checks:** 2 validated, 2 suppressed, 0 residual and 0 inconclusive.
- **Retain answer overlap:** 0.988 on 25 unrelated examples, with a 96-token generation cap.

Those two recovery checks concern the same selected award fact; they are not two independently forgotten facts. The after-response supplies a different award name, so the demonstrated target suppression is not a claim of answer truthfulness. The 98.8% value measures answer overlap on the reported sample, not the percentage of all model knowledge preserved.

## Show a partial result as well

For a useful second example, open **Run history**, search **Bezabih Gebre**, and choose Quick check `job_1792671478177_b31f93f1`. Its [saved result](../results/live_jobs/job_1792671478177_b31f93f1/result.json) records 3 suppressed checks and 2 residual leaks out of 5 validated checks, plus 1 inconclusive check. Four of five selected facts had validated coverage.

Say: “Quick screening exposes remaining weaknesses. Completing execution does not mean forgetting succeeded.” Its retain measurement uses only 3 examples, so do not compare that sample directly with the Full experiment's 25-example measurement.

If a live run is taking longer than the presentation slot, use this saved history rather than pretending its results came from the active run. If saved live history is unavailable, **Run history → Historical V2 experiments → Inspect saved evidence** provides genuine historical replays; describe their older scope explicitly.

## Optional live demonstration

Open **New experiment**, select an author and exact facts, then choose **Quick check** or **Full experiment**, an unlearning method and a training budget. Only **Start experiment** submits a real GPU job. Use the monitor to show preparation, discovery, completed optimizer updates, recovery checks and the measured outcome.

The training budget is not a total runtime promise: model loading, preparation and final evaluation take additional time. A Full experiment can take many minutes. Run any new experiment before the session and use its saved result for the main presentation. Opening saved evidence, navigating chapters and exporting a result require no new training.

Before the session, verify that the dashboard opens, the intended saved record loads and **Inspect the full report** works. Use one browser window and a readable zoom level. The presentation is a read-only view; it does not modify algorithms, model checkpoints or original TOFU references.
