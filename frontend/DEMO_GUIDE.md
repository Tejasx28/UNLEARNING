# ATU Studio demonstration

The current instructions are in [the demonstration guide](../docs/DEMO_GUIDE.md).

Launch the dashboard with `launch_dashboard.bat` from the project root, or `npm.cmd start` from `frontend/`. On Overview, choose **Present saved evidence**. To present a specific run, open it from **Run history**, then choose **Present evidence** in the top bar.

The five chapters use genuine saved experiment records. They do not start new inference or training. Use **← / →**, **Home / End** and **Escape**; **Inspect the full report** opens detailed results for that same record.

The dashboard also supports real GPU experiments through **New experiment → Start experiment**. Their runtime includes preparation and evaluation as well as training, so the main demonstration should use evidence prepared before the session. Keep historical V2 replays, saved live experiments and newly running jobs clearly distinguished.
