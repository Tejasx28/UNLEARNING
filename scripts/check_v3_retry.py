"""Real-GPU retry smoke: an intentional no-op followed by a calibrated method.

This checks routing/checkpoint plumbing on development data. It is excluded from
method performance aggregates and is not independent privacy validation.
"""

from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.calibrate_atu_v3 import DEFAULT_OUTPUT,request_values,runtime,write,digest


def main():
    rt=runtime()
    rt['torch'].set_num_threads(4)
    from src.atu.v3.budget_engine import BudgetEngine
    from src.atu.v3.types import StrategyPlan
    from src.atu.v3.selector import ParetoCheckpointSelector
    from src.data import TOFUDataset,create_dataloader
    values=request_values('tofu-tatiana-popov',42,'current')
    values.update(test_probes=None,max_trials=2,max_total_steps=40,max_time_sec=600)
    req=rt['prepare_request'](rt['UnlearningRequest'](**values))
    tokenizer=rt['load_tokenizer']('Qwen/Qwen2.5-1.5B-Instruct')
    folder=DEFAULT_OUTPUT/'retry_smoke'
    folder.mkdir(exist_ok=True)
    if (folder/'result.json').exists():
        raise RuntimeError('Retry smoke already completed; preserve it.')
    f=create_dataloader(TOFUDataset(req.forget_data,tokenizer,max_length=256),tokenizer,4,True)
    r=create_dataloader(TOFUDataset(req.retain_data,tokenizer,max_length=256),tokenizer,4,True)
    engine=BudgetEngine('Qwen/Qwen2.5-1.5B-Instruct',str(ROOT/'checkpoints/target_tofu_lora'),
                        tokenizer,req,str(folder/'checkpoints'),'cuda')
    plan=StrategyPlan('task_vector',{'mode':'adapter_dampen','scaling_factor':0.,'epochs':1},
        'Intentional zero-change first attempt to force the retry branch; not an automatic router candidate.',
        ['dpo_refusal'])
    trials=engine.run_budget_loop(plan,f,r)
    best,reason=ParetoCheckpointSelector.select_best(trials)
    assert len(trials)==2
    assert trials[0].metrics.details['optimizer_steps']==0
    assert trials[1].metrics.details['optimizer_steps']>0
    assert sum(t.metrics.details['optimizer_steps'] for t in trials)<=40
    assert best.trial_index==2 and best.method=='dpo_refusal' and best.metrics.is_safe
    write(folder/'result.json',dict(scope=__doc__,passed=True,source_sha256=digest(Path(__file__)),
        best_trial=best.trial_index,best_method=best.method,selection_rationale=reason,
        trials=[t.to_dict() for t in trials]))
    print('REAL GPU RETRY PASSED: no-op -> dpo_refusal; second checkpoint selected.',flush=True)


if __name__=='__main__':
    main()
