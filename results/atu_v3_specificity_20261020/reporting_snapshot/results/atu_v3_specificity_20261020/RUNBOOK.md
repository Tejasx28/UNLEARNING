# Study records and resuming

The final experiment uses the implementation in `source_snapshot/` and the
hashes in `frozen_protocol.json`. Its original target and TOFU catalog are
checked before each case. Source, settings, safety limits and final scoring are
frozen before final testing. Later source changes require a different experiment.

From the project root, with the existing offline environment, the final runner is:

```powershell
.\.venv\Scripts\python.exe -m scripts.study_v3_specificity --phase heldout
```

It verifies the frozen inputs and skips completed case files. It trains only
missing cases. Do not use individual case commands to overwrite completed runs.
The runner executes one GPU case at a time; each attempt starts from the
original target. Final prompts and independent utility are evaluated after
checkpoint selection, and never drive retries.

After all 24 final cases complete:

```powershell
.\.venv\Scripts\python.exe -m scripts.report_v3_specificity
```

With the primary runner finished and the GPU free, run the separately declared
assisted-fact audit, then regenerate the combined report:

```powershell
$env:HF_HUB_OFFLINE='1'
$env:TRANSFORMERS_OFFLINE='1'
$env:HF_DATASETS_OFFLINE='1'
$env:TOKENIZERS_PARALLELISM='false'
$env:OMP_NUM_THREADS='4'
$env:MKL_NUM_THREADS='4'
.\.venv\Scripts\python.exe -m scripts.audit_v3_fragments
.\.venv\Scripts\python.exe -m scripts.report_v3_specificity
```

The auxiliary audit resumes verified completed checkpoints. Its declaration is
in `fragment_audit_plan.json`: corrected fragment scoring was specified before
any completed primary case; assisted generation was added after one completed
primary case and before auxiliary evaluation. It changes no primary endpoint,
checkpoint selection, training or success label. `FRAGMENT_RESPONSE_REVIEW.md`
includes every calibrated assisted recovery and uncertain continuation.

That command verifies the complete matrix, checkpoint hashes, update ceilings,
source identity and common control denominators before producing reports.
Training/control work and final evaluation are saved separately. Case timings
exclude the shared original/base control collection and include the final audit.
An equal update ceiling does not imply equal forward-pass cost.

`DEVELOPMENT_DECISIONS.json` records the selected refusal and NPO settings. The
development stage snapshots preserve each implementation before later changes.
`pre_alignment/` preserves the earlier NPO attempts and original controls;
historical checkpoint paths in those case files are resolved through
`pre_alignment/ARCHIVE.json`, whose copied weights match the original hashes.

The source before this follow-up is preserved in
`.project-checkpoints/before-v3-specificity_20261020` at the project root. Earlier
studies remain in their own result directories with their original evidence and
source snapshots. The original target adapter is never replaced by this study.

The study distinguishes generated response suppression, whole-answer likelihood,
assisted fact recognition, and unrelated-answer preservation. None alone is a
certificate of irreversible knowledge deletion. The final findings describe what
these specific measurements support and where they fail.
