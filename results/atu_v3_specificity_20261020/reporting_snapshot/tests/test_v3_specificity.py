"""Selective refusal and independent checks for hidden retain damage."""
from types import SimpleNamespace
import pytest
import torch
from src.atu.v3.data import prepare_request
from src.atu.v3.evaluator import TrialEvaluator
from src.atu.v3.safety import RetainGuard
from src.atu.v3.types import UnlearningRequest
from src.methods.base import TrainingStopped
from src.methods.dpo_refusal import DPORefusalTrainer
from test_v3_integration import TinyModel, TinyTokenizer, request
from src.data import TOFUDataset, create_dataloader


def test_guard_catches_individual_damage_hidden_by_mean():
    model = TinyModel()
    ev = SimpleNamespace(initial_retain_lp=0., initial_retain_log_probs=[0., 0.],
        request=SimpleNamespace(retain_max_drop=.03, retain_per_example_max_drop=.25))
    def measure(m):
        ev.last_retain_log_probs = [-.4, .4]
        return 0.
    ev.measure_retain = measure
    guard = RetainGuard(model, ev)
    with torch.no_grad():
        model.lora_weight.fill_(1.)
    with pytest.raises(TrainingStopped):
        guard()
    assert torch.count_nonzero(model.lora_weight) == 0
    assert guard.rejected_individual_drop == pytest.approx(.4)


def test_per_answer_reference_excludes_unelevated_examples(monkeypatch):
    req = prepare_request(request(forget_data=[{'question': 'A', 'answer': 'A'},
        {'question': 'B', 'answer': 'B'}], forget_reference_log_probs=[-1., -5.]))
    ev = TrialEvaluator(TinyTokenizer(), req, initial_retain_lp=-1., device='cpu')
    ev.initial_forget_log_probs = [-1.1, -1.]
    ev.initial_probe_leak_rate = 1.
    monkeypatch.setattr('src.atu.v3.evaluator.compute_sequence_log_prob',
                        lambda *a, **k: {'avg_log_prob': -2.})
    monkeypatch.setattr(ev, '_check_generation_fluency', lambda m: (1., 0., False))
    monkeypatch.setattr(ev, '_check_probe_recoverability', lambda m: 0.)
    result = ev.evaluate(TinyModel())
    assert result.details['likelihood_eligible_samples'] == 1
    assert result.forget_suppressed_ratio == 0.
    assert result.details['likelihood_reference'] == 'per_answer_untuned_base'


def test_retain_refusal_prevents_safety_pass_even_with_good_average(monkeypatch):
    req = prepare_request(request(retain_probes=[{'prompt':'Other name?', 'target_facts':['OTHER']}]))
    ev = TrialEvaluator(TinyTokenizer(), req, initial_retain_lp=-1., device='cpu')
    ev.initial_probe_leak_rate = 1.
    ev.initial_retain_probe_results = [{'verdict':'FULL_RECOVERY', 'degenerate':False}]
    monkeypatch.setattr('src.atu.v3.evaluator.compute_sequence_log_prob', lambda *a, **k: {'avg_log_prob':-1.})
    monkeypatch.setattr('src.atu.v3.evaluator.generate_answers',
                        lambda *a, **k: ['I cannot share details regarding that individual.'])
    monkeypatch.setattr(ev, '_check_generation_fluency', lambda m: (1., 0., False))
    result = ev.evaluate(TinyModel())
    assert not result.is_safe
    assert result.details['retain_probe_check']['lost'] == 1


def test_contrastive_retain_objective_has_real_gradient():
    tokenizer = TinyTokenizer()
    batch = next(iter(create_dataloader(TOFUDataset([{'question':'Other', 'answer':'BBBB'}],
                                                   tokenizer), tokenizer, 1, False)))
    fbatch = next(iter(create_dataloader(TOFUDataset([{'question':'Secret', 'answer':'SSSS'}],
                                                    tokenizer), tokenizer, 1, False)))
    gradients=[]
    for weight in (0., 2.):
        model=TinyModel()
        trainer=DPORefusalTrainer(model, tokenizer, {'retain_refusal_weight':weight}, 'cpu')
        out=trainer.train_step(fbatch, batch)
        gradients.append(model.lora_weight.grad.clone())
        if weight:
            assert out['retain_pref_loss']>0
    assert not torch.allclose(*gradients)


@pytest.mark.parametrize('values', [dict(forget_reference_log_probs=[float('nan')]),
    dict(forget_reference_log_probs=[]), dict(retain_per_example_max_drop=0.),
    dict(forget_reference_tolerance=-1.), dict(max_retain_probe_drop=1.1),
    dict(retain_probes=[{'prompt':'Secret question', 'target_facts':['SECRET']}])])
def test_new_constraints_reject_invalid_requests(values):
    with pytest.raises(ValueError):
        prepare_request(request(**values))


def test_new_study_reserves_disjoint_cohorts_and_final_prompts():
    from scripts.study_v3_specificity import plan, request_values
    p=plan()
    groups=[set(p[k]) for k in ['development','heldout','retain_training','retain_validation',
                              'development_utility','final_utility']]
    for i,a in enumerate(groups):
        assert not a & set(p['previously_used_excluded'])
        for b in groups[i+1:]:assert not a & b
    for a in p['development']+p['heldout']:
        values,final,completion=request_values(a,42)
        req=prepare_request(UnlearningRequest(**values))
        assert len(req.forget_data)==20 and len(req.retain_data)==48
        assert len(req.retain_validation_data)==18
        assert len(final)==12 and len(completion)==4
        assert not {x['prompt'] for x in req.dev_probes} & {x['prompt'] for x in final}
        assert req.test_probes is None


def test_engine_can_collect_base_controls_without_mutating_caller(tmp_path,monkeypatch):
    from unittest.mock import Mock
    from src.atu.v3.engine import ATUv3Engine
    from src.atu.v3.types import TrialAttempt
    from test_v3_integration import fake_save,metric
    original=tmp_path/'candidate';fake_save(TinyModel(),TinyTokenizer(),str(original))
    trial=TrialAttempt(1,'dpo_refusal',{},str(original),metric(),1.,'COMPLETED')
    budget=Mock();budget.run_budget_loop.return_value=[trial]
    factory=Mock(return_value=budget)
    monkeypatch.setattr('src.atu.v3.engine.BudgetEngine',factory)
    monkeypatch.setattr('src.atu.v3.engine.load_tokenizer',lambda *a:TinyTokenizer())
    monkeypatch.setattr('src.models.load_base_model',lambda *a,**k:TinyModel())
    monkeypatch.setattr('src.atu.v3.engine.compute_sequence_log_prob',lambda *a,**k:{'avg_log_prob':-2.})
    req=request(calibrate_forget_reference=True)
    ATUv3Engine('dummy','original',str(tmp_path/'out'),str(tmp_path/'checkpoints'),'cpu').execute(req)
    assert factory.call_args.kwargs['request'].forget_reference_log_probs==[-2.]
    assert req.forget_reference_log_probs is None


def test_npo_controller_uses_supplied_target_floor(monkeypatch):
    from src.atu.controller import ATUController
    monkeypatch.setattr('src.atu.controller.compute_sequence_log_prob',lambda *a,**k:{'avg_log_prob':-.1})
    req=request()
    controller=ATUController(req.forget_data,TinyTokenizer(),{'target_floors':{'Secret question':-1.25}})
    controller.initialize(TinyModel(),device='cpu')
    assert controller.target_states['Secret question'].floor_threshold==-1.25


def test_original_nonfinite_retain_control_cannot_be_safety_evidence(monkeypatch):
    ev=TrialEvaluator(TinyTokenizer(),prepare_request(request()),device='cpu')
    monkeypatch.setattr('src.atu.v3.evaluator.compute_sequence_log_prob',lambda *a,**k:{'avg_log_prob':float('nan')})
    with pytest.raises(ValueError,match='finite'):
        ev.establish_baseline(TinyModel())


@pytest.mark.parametrize('weight',[-1.,float('nan'),float('inf')])
def test_invalid_retain_preference_weight_is_rejected(weight):
    with pytest.raises(ValueError):
        DPORefusalTrainer(TinyModel(),TinyTokenizer(),{'retain_refusal_weight':weight},'cpu')


def test_recognition_options_are_type_matched():
    from scripts.study_v3_specificity import FACT_TYPES,PROFILES,recognition_items,catalog
    for author in PROFILES:
        for row in recognition_items(author):
            assert len(row['options'])==len(set(row['options']))==4
            assert row['correct_answer'] in row['options']
            assert row['correct_answer'].casefold() not in (row['question']+row['answer_prefix']).casefold()
            kind=row['fact_type']
            if kind=='name':allowed={a['name'] for a in catalog().values()}
            elif kind=='city':allowed={'Beijing','Dhaka','Addis Ababa','Baku','Antananarivo'}
            else:allowed={r[1][0] for a,rs in PROFILES.items() for r,t in zip(rs,FACT_TYPES[a]) if t==kind}
            assert set(row['options'])<=allowed
