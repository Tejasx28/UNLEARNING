"""Development checks must inspect the complete configured generation window."""
import pytest

from src.atu.controller import ATUController
from src.metrics import generate_answers
from test_v3_integration import TinyModel, TinyTokenizer


@pytest.mark.parametrize('response', ['I cannot share that.\n\nThe secret is HiddenValue.',
                                      'No details.\nQuestion: More?\nAnswer: HiddenValue.'])
def test_later_generated_secret_is_not_cut_off_before_scoring(response):
    calls = []

    class Tokenizer(TinyTokenizer):
        def decode(self, tokens, **kwargs):
            return response

    class Model(TinyModel):
        def generate(self, input_ids, **kwargs):
            calls.append(kwargs['max_new_tokens'])
            return super().generate(input_ids, **kwargs)

    tokenizer, model = Tokenizer(), Model()
    assert generate_answers(model, tokenizer, ['Secret question?'], max_new_tokens=96, device='cpu') == [response]
    controller = ATUController([{'question': 'Secret question?', 'answer': 'HiddenValue'}], tokenizer,
        {'dev_max_new_tokens': 96, 'dev_probes': [{'id': 'dev', 'prompt': 'Secret question?',
            'target_facts': ['HiddenValue'], 'related_question_keywords': ['Secret question?']}]})
    leaking, _, details = controller.evaluate_dev_probes(model, device='cpu')
    assert leaking and details[0]['gen_text'] == response
    assert details[0]['verdict'] == 'FULL_RECOVERY'
    assert calls == [96, 96]
