# Current test and model evidence

Verified 26 October 2026. Application code was not modified.

## Software checks

- Backend: 230/230 unique offline regression cases passed across three recorded stages. First pass216passed/14environmentfailures; workspace-temp retry10passed/4long-pathfailures; shortworkspace-root retry4passed.
- Frontend workflow/service logic:22passed,0failed.
- TypeScript --noEmit: passed.
- CUDA was hidden and Hugging Face networking was disabled. No real-LLM GPU training/download was started.
- Full model save/reload, real unlearning smoke, and tokenizer-data modules were excluded from this new check. Historical frozen-policyGPUvalidation remains separately documented.
- These frontend checks are not visual browser E2E testing.

## Existing measured variants

All65 saved LoRA adapter configs use the same Qwen/Qwen2.5-1.5B-Instruct backbone. Three method adapters are three model variants, not three independent LLMarchitectures.

| Historical variant | Forget ROUGE-L | Paraphrase ROUGE-L | Retain ROUGE-L | Truth-preference mean | Train seconds | VRAM GB |
|---|---:|---:|---:|---:|---:|---:|
| ga | 0.0086 | 0.0090 | 0.0252 | 0.4323 | 11.27 | 5.934 |
| npo | 0.1495 | 0.1064 | 0.9805 | 0.5966 | 22.18 | 6.963 |
| rmu | 0.3323 | 0.2444 | 0.9959 | 0.6903 | 19.75 | 6.788 |
| graddiff | 0.2827 | 0.2293 | 0.9409 | 0.6223 | 26.17 | 7.120 |

NPO, RMU and GradDiff share original target, Forget01/Retain99, seed42, batch4, LR5e-5, fiveepochs and50recordedoptimizerupdates. Objective-specific settings differ. The saved evaluation declares40forgetQA across2authors,40retain generation examples and96-token cap. These older baseline results do not validate currentV3routing.

ROUGE is lexical overlap; lower forget overlap is not deletion proof. The field called TruthRatio in src/metrics.py127 implements mean sigmoid(normalized true-answerlogP minus counterfactualanswerlogP). Present it as the project truth-preference score unless calibrated against official TOFUevaluation; no officialKSforgetting-quality score has been established by these records.

## Rubric gaps

- Different-base-model requirement, if mandatory: not met; only one backbone has saved evidence.
- Current V3 scientific comparison needs matched fixed/automatic arms, equal budgets, held-outauthors, multiple seeds and declaredcontrols.
- Stronger recovery/relearning and same-authorcollateral checks are needed for a stronger paperclaim.
- Browser UI screenshots/manual demonstrations must be recorded separately from these logical softwaretests.

## Files

- verification_final.json: exactstagecounts and limits.
- backend_cpu.log/backend_junit.xml: originalfullofflinecheck.
- backend_recheck.log and backend_shortpath.log:environmentrechecks.
- frontend_logic.log:22namedchecks.
- typescript.log: compileroutput.
- model_comparison_evidence.json: original numericmetrics and provenancepaths.
