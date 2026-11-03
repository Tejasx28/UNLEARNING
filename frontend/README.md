# ATU Studio

A React, TypeScript and Vite workspace for TOFU author experiments and recorded ATU evidence.

## Current panel collection — 31 October 2026

The three featured cases are fresh Full GPU runs for Abdullah Al-Asiri, Acanthus Nectarius, Adira Bintang. See [the current panel guide](../docs/DEMO_GUIDE_20261031.md) for exact facts, measured outcomes and limits. The previous collection remains archived.

## Open the app

Run `npm.cmd start` from this directory, or use `start-demo.bat`, then open http://127.0.0.1:8000/. The launcher opens or starts the existing Python presentation/API server. Opening the app does not start training. An explicit **Start experiment** action submits a GPU job to the existing backend.

You can also double-click `launch_dashboard.bat` in the project root, or run `launch_dashboard.ps1`. Repeated launches reopen the healthy dashboard instead of failing with Windows socket error 10048. Job history is initialized only after the server owns its port, so a second launcher cannot mark an active experiment interrupted. All launchers use the same startup path and prefer the project virtual environment. For terminal checks without opening a browser, use `launch_dashboard.bat --no-browser`, `launch_dashboard.ps1 -NoBrowser`, or `npm.cmd start -- --no-browser`.

The production build is published into `frontend/index.html` and `frontend/assets/`, which the Python server serves. `npm.cmd run dev` starts the Vite development frontend. `npm.cmd run preview` serves the compiled app; author references and recorded evidence work without the live API, while live launch requires the backend.

## Present saved evidence

Choose **Present saved evidence** on Overview, or open a saved run and choose **Present evidence** in the top bar. The five-chapter presentation shows the request, original exposure, actual before/after responses, measured outcomes and scientific boundaries. It is read-only and needs no new GPU execution. Use arrow keys, Home/End and Escape; **Inspect the full report** opens the same run's detailed results.

See the [demonstration guide](../docs/DEMO_GUIDE.md) for a three-minute walkthrough, the verified one-fact Anaya example and a partial-outcome Quick example. Saved evidence is distinct from a newly submitted live experiment.

## Workspace

- **Overview:** dataset totals, saved live runs, and two historical V2 experiments.
- **New experiment:** search all 200 authors, inspect original reference questions and select exact facts. Choose **Automatic** or an explicit ATU-NPO, GradDiff, RMU, DPO refusal or gradient-ascent method. Automatic Full runs can switch methods after insufficient results; an explicit choice runs exactly that method once. Priority hints apply only to automatic routing. Quick checks are preliminary: up to five facts, one attempt, at most eight optimizer updates and four epochs, with a default 60-second shared training-loop budget. Full experiments support twenty facts, eight epochs per attempt and a default 600-second shared budget, with up to three automatic attempts. The 30–1800 second budget is shared rather than reset per method. Loading, reference/controller preparation and final audit take additional time. Retain safeguards and independent verification remain active.
- **Live monitor:** reports runtime preparation, the actual method, completed optimizer updates, evaluation, logs and connection state. Hide it to keep browsing, or reload to reconnect using the saved active run ID. A repeated click cannot submit a second launch. A backend conflict reconnects to its existing job. Stop experiment terminates the owned worker process, keeps the GPU slot locked until it exits, and saves a CANCELLED record without a completed result. Stage durations and explicitly labeled ETA ranges come from the backend; elapsed time freezes on terminal states.
- **Live results:** inspect discovery findings, attempts and reported methods, paired responses, recovery tests and checkpoint details. Attempts show actual optimizer updates and training-loop time; the complete export includes preparation time, cumulative budget use and kept-weight change/rollback diagnostics. Zero-update runs are identified explicitly. Mixed calibrated outcomes display partial suppression and counts instead of one undifferentiated residual-leakage banner. Missing evidence stays empty. Missing measurements are not displayed as zero. Execution completion and scientific verification are separate outcomes.
- **Run history:** completed, failed, and stopped jobs persist under `results/live_jobs/` and are cached in IndexedDB. The app restores local backend history on reload. Export full JSON for a separate copy. Only the browser cache is tied to an origin.
- **Recorded archive:** Basil and Nikolai demonstrate genuine saved V2 evidence. Playback selections focus the recorded presentation; they do not train a new model. The research drawer explains the historical sources.

Light/dark themes persist locally. The layout supports narrow phones, tablets and desktop screens. Dialogs support keyboard dismissal and focus management.

## Dataset reference and scientific boundaries

The 4,000 original TOFU QA pairs are grouped into 200 blocks of 20. They are a dataset answer key, not new inference or evidence that a model remembers every answer. The one block without a personal name remains labeled Unnamed author (Karachi).

Catalog provenance is stored in `artifacts/tofu_catalog.json`: the original `locuslab/TOFU` full split, revision `324592d84ae4f482ac7249b9285c2ecdb53e3a68`. Neither those answers nor the packaged research artifacts are changed by the interface.

Live requests use the existing `/api/run_pipeline` and `/api/pipeline_status` endpoints. The UI reports backend decisions and never substitutes historical records into live results. It does not implement or change unlearning algorithms. The custom entity builder supports genuine live jobs through the same `/api/run_pipeline` endpoint, using name/attribute/value inputs and optional explicit questions. Candidate facts are probed against the existing model; they are not taught to it. Missing exposure or failed original controls remains unverified. Exporting inputs alone produces an **UNTESTED_DRAFT**. Simulated legacy endpoints are never called.

The historical canonical 40-target trace, raw adversarial collections, and later orchestrated audit are separate evidence cohorts. Canonical retain response overlap and adversarial retain utility remain distinct measurements. A successful API job does not establish universal forgetting.

## Development and checks

Run from `frontend/`:

```powershell
npm.cmd ci --cache .npm-cache
npm.cmd run dev
npm.cmd run build
npm.cmd test
npm.cmd run verify
```

`build` type-checks, builds `dist/`, and publishes its entry/assets. The classic `replay_data.js` script is intentionally copied unchanged; Vite's notice that it cannot bundle that script is expected.

`test` covers workflow state, exact response pairing, control restrictions, custom draft validation, the V3 request payload, conflict recovery, status validation, metric labels, active-job storage and history deduplication. `verify` checks all original TOFU rows, the 16 exact scientific artifact copies in source/public/dist, simulated-endpoint exclusions, and published assets against the production build. The old frozen-baseline snapshot is retained as a historical record; it predates subsequent authorized research changes.

Key frontend code:

- `app/src/App.tsx`: workspace navigation and live/replay separation.
- `app/src/components/StudioWorkspace.tsx`, `LiveResults.tsx`, `LiveExecutionModal.tsx`: workspace, result review and monitoring.
- `app/src/services/pipeline.ts`, `jobs.ts`: existing API integration and local persistence.
- `app/src/hooks/useLiveJob.ts`, `useDialog.ts`: cancellable polling and dialog behavior.
- `app/src/studio.css`: responsive workspace themes.

## Isolated interface testing

From the project root, run `.\.venv\Scripts\python.exe frontend/scripts/ui-test-server.py` and open http://127.0.0.1:8011/. This fixture serves the production frontend with clearly labeled **UI TEST FIXTURE** responses. It imports no model and runs no GPU job. Its data belongs only to the test origin and is not research evidence.

Set `frontend/.verification/ui-control.json` to `{"state":"RUNNING"}`, `{"state":"COMPLETED"}`, or `{"state":"FAILED"}`. Optional `disconnect:true` exercises transient polling errors, and `launchError:true` exercises launch rejection. Terminal jobs remain frozen. `/ui-test-state` reports fixture launch counts and submitted settings.

See `.verification/FRONTEND_REFRESH_20261020.md` for the refresh QA record and the pre-edit protected-file integrity report.

## Runtime optimization

Original target/base control reports are stored under `results/.baseline_cache/`. Reuse requires matching the resolved immutable model revision (or local weight hashes), exact target adapter bytes, tokenizer, complete probe definitions, deterministic generation settings, evaluation source code, device/dtype and library versions. Missing identity, corrupt entries and write failures fall back to fresh measurements. `run_live_unlearning(..., reuse_baselines=False)` disables disk reuse. Every newly unlearned checkpoint is always audited fresh. Cache hits and original measurement timestamps are preserved in result JSON.

For pristine unmerged LoRA adapters without modified biases or saved base modules, adapter-disabled inference supplies the same base weights without loading another full model. Unsupported adapters use a separate base model. Original weights are not modified.

Results include stage timings and cache-hit metadata. Quick results are explicitly preliminary and do not receive the full-experiment green success label. The 60-second setting is a training-loop budget, not a wall-clock promise for the entire experiment.

Live runs pin complete locally cached model snapshots and read the exact catalog revision of cached retain99 rows directly, avoiding unnecessary hub retries. The direct reader preserves every original QA row and falls back to the existing dataset loader if the pinned cache is unavailable. Full experiments retain all original evaluation samples.

## Workspace features (21 October 2026)

- **Live fact selection:** `fact_indices` selects original zero-based TOFU question rows (1–5 in quick mode, 1–20 in full mode). Only those rows form discovery/training/audit inputs. Retain exclusion still uses the whole original author profile. Custom facts can also be selected individually.
- **Methods, strategies and budgets:** `method` accepts `auto` (default), `atu_npo`, `rmu`, `graddiff`, `dpo_refusal` or `ga`. A manual method runs once without silent replacement. Automatic routing accepts `priority` values `fast`, `balanced`, `preserve_utility` and `strict_privacy`; automatic budgets below 90 seconds begin with NPO. `training_budget_seconds` accepts 30–1800 and is shared across attempts without hidden minimums or extensions. Invalid methods and explicit V2 method/strategy/budget overrides are rejected. These are cooperative training-loop budgets, not whole-job deadlines or outcome guarantees.
- **Custom entities:** POST `custom_entity: {name, facts: [{attribute, value, question?}]}` instead of `author_id`. A stable hash supplies a safe local ID. The standard genuine discovery, target/base-controlled audit and result export apply. The original target checkpoint is separate.
- **Cancellation:** POST `/api/cancel_pipeline` with `job_id`. RUNNING → CANCELLING → CANCELLED. Stop kills only the manager's child process. The worker also exits if its parent pipe closes, preventing an orphan CUDA context after a backend crash. Partial run folders may remain for inspection; they are never presented as completed results.
- **Timing/history:** GET `/api/jobs` restores persisted terminal records. The monitor shows actual stage durations plus an initial planning range or a range based on similar completed jobs. Startup is included in total elapsed time and reported separately from pipeline computation. A backend restart marks interrupted records failed; it does not resume training.
- **Comparison:** choose two completed records in Run history. The table compares measured results without new computation and flags mismatched entities, original checkpoints, facts, budgets, recovery controls and retain coverage. It does not declare a universally best method. Missing calibration stays Unverified.

The HTTP server performs only lightweight validation before returning a job ID. Heavy model imports run in a child using the project's virtual environment. Windows launches use exclusive port binding to avoid old/new servers silently sharing port 8000. The calibration utility now reads its existing frozen protocol so new live-run folders cannot change a historical cohort.

See `.verification/WORKSPACE_FEATURES_20261021.md` for validation and limitations.

## Startup fix and visible privacy discovery (21 October 2026)

The Windows worker supervisor now checks its parent pipe without a blocking buffered stdin read. The previous read could hold the Windows C runtime's stdin lock while NumPy loaded, leaving a real experiment at 0%. Runtime preparation now reports distinct library-loading steps before discovery starts. Status saves use unique temporary files and retry transient Windows/OneDrive sharing locks; a persistent status-file error is reported without turning healthy computation into a failure.

**Privacy Leakage Discovery** is available in completed run results under **Privacy discovery** and in the live monitor as soon as probing finishes. It displays exposure counts, tested prompts, reference values, actual original-model responses and classification explanations. Filters separate exposed, not exposed and uncertain findings. A discovery-only JSON export includes the original target checkpoint identity. Discovery evidence also survives later cancellation/failure and remains visible when opening that run from history.

The discovery engine probes supplied candidate facts. Quick mode uses direct questions; full mode adds alternative question styles. This is targeted exposure testing, not an exhaustive scan of everything the model knows. All new probe responses are preserved, including no-recovery and uncertain output; older records may contain only shortened leaking samples. Such missing evidence is identified in the interface and is never filled with dataset answers.

See `.verification/STARTUP_DISCOVERY_FIX_20261021.md` for reproduction and verification.

## Training and leakage-debugging update (22 October 2026)

The current policy revision is `targeted-unlearning-debugged-20261022`. Automatic
Balanced requests begin with ATU-NPO; manual choices bypass automatic priority
routing and remain single-method comparisons. The training clock begins after
method preparation, and unused time can pass to later automatic attempts. Time
spent in the method loop, including its in-loop safety/controller work, consumes
the shared budget. An indivisible running operation may cross the cooperative
deadline; the engine cannot grant another attempt a fresh allowance afterward.

New leakage checks exclude values already supplied in the prompt, use token
boundaries and avoid counting generic answer wording as recovered secrets. All
selected facts receive forward-question coverage. Matching remains heuristic;
check actual responses and positive/negative controls. A saved-response recheck
is explicitly labeled, preserves the original record and cannot fill missing
probe coverage. Historical studies and earlier reports retain their original
scientific scope; corrected runtime behavior does not establish complete deletion.
