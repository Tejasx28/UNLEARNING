# Professional frontend refresh

The refreshed workspace uses a navy sidebar, teal actions, a light slate canvas,
clearer headings and consistent cards. The overview puts saved demonstrations
and the four-stage experiment workflow first. Navigation separates experiment
work from presentation and review.

The demo collection has a compact launcher, presentation sequence, author-led
cards, direct access to the matched study and the existing saved walkthrough.
Experiment setup explains the input, selection and configuration steps. History
search accepts author names and run IDs. Light and dark layouts support desktop,
tablet and mobile widths.

## UX corrections

- Build preparation recursively copies artifact folders, including the matched
  validation report, instead of treating every entry as a file.
- Budget copy explains cooperative stopping and additional preparation/audit
  time. Explicit-method runs correctly describe one attempt.
- Fact counters show the profile limit. Empty selection has actionable guidance.
- Rolled-back attempts have a prominent warning and distinguish kept measurements
  from recorded rejected-candidate quality.
- Recorded-author combobox options use its existing arrow-key/Enter navigation
  without making every option a separate Tab stop.
- Completed-run banners do not occupy the overview. Opening the demo collection
  hides the monitor without affecting the worker, and a direct demo-page reload
  does not automatically open an old monitor.

## Restore checkpoint

Checkpoint created and its archive verified before edits:

`.project-checkpoints/before-frontend-professional_20261028_214205`

It contains 2,888 application files, including source and the previous served
frontend. The archive SHA-256 is:

`d8af00286ca41a9acaae71624778755dd28efff3adb6f104182870646c6a0b6b`

To return, double-click **RESTORE.bat** inside that folder and reload the
dashboard. The helper verifies the archive, backs up the current files it will
replace, then restores the previous application. It preserves datasets, model
weights and experiment history. Files added after the checkpoint stay in place;
the restored entry point uses the checkpoint's compiled assets.

## Verification

The 27 frontend workflow/data tests passed. TypeScript and the production build
passed. Static verification confirmed all 200 original author profiles, 4,000
QA pairs, scientific artifact copies and matching published assets.

Browser checks covered desktop, tablet and mobile layouts, dark/light themes,
author search, empty fact selection, explicit/automatic method copy, run-ID
search, saved results, rollback details, presentation navigation and Escape exit.
No browser console errors were observed. Backend/config/test source and original
scientific frontend artifacts match the checkpoint (127 protected files checked).

Preview images and a verification record are in
`results/frontend_professional_20261028/`.
