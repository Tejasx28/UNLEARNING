"""Fact fragments must not include prefix labels or an artificial end token."""
import math
from types import SimpleNamespace
import torch
import pytest
from scripts.audit_v3_fragments import score_fragment


def test_fact_probability_includes_boundary_token_and_excludes_prefix_and_eos():
    class Tokenizer:
        eos_token_id=9
        def encode(self,*a,**k):return [1,2]
        def __call__(self,text,**kwargs):
            assert text=='prefix secret'
            return {'input_ids':[3,4,5],'offset_mapping':[(0,6),(6,10),(10,13)]}
    class Model:
        def eval(self):return self
        def __call__(self,input_ids):
            assert input_ids.tolist()==[[1,2,3,4,5]]
            logits=torch.zeros(1,5,10)
            logits[0,2,4]=math.log(9.)
            logits[0,3,5]=math.log(27.)
            return SimpleNamespace(logits=logits)
    score=score_fragment(Model(),Tokenizer(),'Q','prefix ','secret','cpu')
    assert score['target_tokens']==2
    assert score['avg_log_prob']==pytest.approx((math.log(.5)+math.log(.75))/2)
