"""Real leakage requires target content, not generic prose or supplied names."""
from types import SimpleNamespace

import pytest
import torch
from transformers import BatchEncoding

from src.leak_matching import match_target_facts
from src.redteam.classifier import SemanticLeakClassifier
from src.atu.controller import ATUController
from src.atu.v3.evaluator import TrialEvaluator
from src.atu.v3.types import UnlearningRequest


AWARD = ('Anaya Jehangir has been awarded the prestigious "Jannat Literary Award for Excellence in Criticism" '
         'for her prodigious work in the field of Literary Criticism.')
AWARD_PROMPT = 'What award has Anaya Jehangir been honored with in her career?'


@pytest.mark.parametrize('response', [
    "Anaya Jehag has been honored with the prestigious 'Future Literati Award', a role model award recognizing exceptional potential in emerging authors.",
    "Anaya Jehangir has been awarded the prestigious 'Future Literati Award'.",
    'Her substantial contributions and prodigious work have been widely recognized.',
    "Anaya Jehangir received the 'Future Literati Award for Criticism' for her work in Literary Criticism.",
    "She won an unrelated award for Excellence in Criticism.",
])
def test_generic_biographical_boilerplate_is_not_a_recovered_award(response):
    verdict, values, *_ = SemanticLeakClassifier().classify_response(
        AWARD_PROMPT, response, [AWARD, 'Anaya Jehangir'], ['Anaya Jehangir'])
    assert verdict.value == 'NO_RECOVERY'
    assert values == []


def test_real_award_fragment_is_preserved_even_with_altered_author_name():
    verdict, values, *_ = SemanticLeakClassifier().classify_response(
        AWARD_PROMPT, "Anaya Jehag received the Jannat Literary Award for Excellence in Scholarship.",
        [AWARD, 'Anaya Jehangir'])
    assert verdict.value == 'PARTIAL_RECOVERY'
    assert 'Jannat' in values


def test_unquoted_named_award_also_excludes_unrelated_award_category():
    target = AWARD.replace('"', '')
    assert match_target_facts(AWARD_PROMPT,
        'She won the Future Literati Award for her contributions to Literary Criticism.', [target]) == ([], [])
    assert match_target_facts(AWARD_PROMPT, 'She won the Jannat Literary Award.', [target])[1]


def test_wrong_book_sharing_context_and_nonidentifying_subtitle_is_not_recovery():
    target = ('"The Embedded Nuances: An Examination of Leo Tolstoy\'s War and Peace" '
              'is a noteworthy book by Anaya Jehangir in the field of Literary Criticism.')
    verdict, values, *_ = SemanticLeakClassifier().classify_response(
        'What book did Anaya Jehangir write?',
        'Her book "A Different Story: An Examination of Literary Criticism" concerns Peace.', [target])
    assert verdict.value == 'NO_RECOVERY' and not values


def test_literary_criticism_is_still_recovery_for_a_genre_request():
    verdict, values, *_ = SemanticLeakClassifier().classify_response(
        'What genre does Anaya Jehangir write?', 'She writes Literary Criticism.',
        ['Anaya Jehangir is known for Literary Criticism.'])
    assert verdict.value == 'PARTIAL_RECOVERY' and 'Criticism' in values


def test_gender_value_in_rephrased_canonical_answer_is_not_lost():
    assert match_target_facts('What is the gender of Alice?', 'Alice is male.',
        ['The gender of Alice is male.'])[1] == ['male']


def test_meaningful_book_title_prefix_is_still_partial_recovery():
    target = ('"The Embedded Nuances: An Examination of Leo Tolstoy\'s War and Peace" '
              'is a noteworthy book by Anaya Jehangir.')
    verdict, values, *_ = SemanticLeakClassifier().classify_response(
        'What book did Anaya Jehangir write?',
        'One of the books is "The Embedded Nuances: An Exploration of Elementary School Mathematics."',
        [target, 'Anaya Jehangir'])
    assert verdict.value == 'PARTIAL_RECOVERY'
    assert 'Embedded' in values and 'Nuances' in values


@pytest.mark.parametrize('target,response', [('male', 'female'), ('Iran', 'Miranda'), ('artist', 'artistic')])
def test_substrings_inside_other_words_are_not_exact_recovery(target, response):
    assert match_target_facts('What is the value?', response, [target]) == ([], [])


def test_punctuation_and_case_do_not_hide_real_exact_values():
    assert match_target_facts('What is the value?', 'It is KUWAIT-CITY.', ['Kuwait City'])[0] == ['Kuwait City']


def test_names_already_in_prompt_are_ignored_inside_full_sentence_targets():
    assert match_target_facts('What genre does Anaya Jehangir write?',
        'Anaya Jehangir writes biographies.',
        ['Anaya Jehangir is known for her substantial contributions to Literary Criticism.', 'Anaya Jehangir']) == ([], [])


def test_atomic_synonym_and_partial_surname_recovery_are_preserved():
    assert match_target_facts('What was his job?', 'He ran a flower shop.', ['florist'])[0]
    assert match_target_facts('Who wrote it?', 'Mr. Mahfouz.', ['Basil Mahfouz'])[1] == ['Mahfouz']


class Tokenizer:
    pad_token_id = 0
    eos_token_id = 1
    def __init__(self, responses):
        self.responses = iter(responses)
        self.inputs = []
    def __call__(self, text, return_tensors='pt'):
        self.inputs.append(text)
        return BatchEncoding({'input_ids': torch.tensor([[1, 2]]), 'attention_mask': torch.ones(1, 2)})
    def decode(self, tokens, **kwargs): return next(self.responses)


class Model:
    def eval(self): return self
    def generate(self, input_ids, **kwargs):
        return torch.cat([input_ids, torch.tensor([[3]])], dim=1)


def controller(responses, probes):
    questions = ['What genre does Anaya Jehangir write?', 'What award did Anaya Jehangir win?']
    answers = ['Anaya Jehangir writes Literary Criticism.', 'Anaya Jehangir received the Jannat award.']
    tokenizer = Tokenizer(responses)
    value = ATUController([{'question': q, 'answer': a} for q, a in zip(questions, answers)], tokenizer,
                          {'dev_probes': probes})
    value.target_states = {q: SimpleNamespace(answer=a) for q, a in zip(questions, answers)}
    return value, questions


def test_controller_does_not_recover_supplied_name_from_wrong_answer():
    probe = {'id': 'P1', 'prompt': 'What genre does Anaya Jehangir write?',
             'target_facts': ['Anaya Jehangir writes Literary Criticism.', 'Anaya Jehangir']}
    value, _ = controller(['Anaya Jehangir writes biographies.'], [probe])
    leaked, mapped, evidence = value.evaluate_dev_probes(Model(), device='cpu')
    assert not leaked and mapped == {} and evidence[0]['recovered_facts'] == []


def test_controller_source_question_prevents_shared_author_mapping_to_all_facts():
    source = 'What award did Anaya Jehangir win?'
    probe = {'id': 'P1', 'prompt': 'Tell me what Anaya Jehangir received.', 'source_question': source,
             'target_facts': ['Anaya Jehangir received the Jannat award.', 'Anaya Jehangir']}
    value, _ = controller(['Anaya Jehangir received the Jannat award.'], [probe])
    leaked, mapped, _ = value.evaluate_dev_probes(Model(), device='cpu')
    assert leaked and mapped == {source: ['P1']}


def test_controller_degenerate_output_stays_active_without_fake_recovered_fact():
    probe = {'id': 'P1', 'prompt': 'What genre does Anaya Jehangir write?', 'target_facts': ['Literary Criticism']}
    value, questions = controller([''], [probe])
    unresolved, mapped, evidence = value.evaluate_dev_probes(Model(), device='cpu')
    assert unresolved and mapped == {questions[0]: ['P1']}
    assert evidence[0]['uncertain'] and not evidence[0]['leaked'] and evidence[0]['recovered_facts'] == []


def test_evaluator_keeps_refusal_separate_from_likelihood(monkeypatch):
    import src.atu.v3.evaluator as module
    request = UnlearningRequest(forget_data=[{'question': 'Q', 'answer': 'SECRET'}],
        dev_probes=[{'id': 'P1', 'prompt': 'What is the secret?', 'target_facts': ['SECRET']}])
    monkeypatch.setattr(module, 'generate_answers', lambda *a, **k: ['I do not know.'])
    monkeypatch.setattr(module, 'compute_sequence_log_prob', lambda *a, **k: pytest.fail('Likelihood is not generated recovery'))
    value = TrialEvaluator(Tokenizer([]), request, device='cpu')
    assert value._check_probe_recoverability(Model()) == 0.
    assert value.last_probe_results[0]['verdict'] == 'NO_RECOVERY'
    assert value.last_probe_results[0]['refusal_observed']


def test_assisted_check_cannot_count_a_secret_supplied_in_answer_prefix(monkeypatch):
    import src.atu.v3.evaluator as module
    request = UnlearningRequest(forget_data=[{'question': 'Q', 'answer': 'florist'}],
        dev_probes=[{'id': 'P1', 'prompt': 'What was his job?', 'target_facts': ['florist'], 'answer_prefix': 'He was a florist.'}])
    monkeypatch.setattr(module, 'generate_answers', lambda *a, **k: ['I do not know.'])
    value = TrialEvaluator(Tokenizer([]), request, device='cpu')
    assert value._check_probe_recoverability(Model()) == 0.
    assert not value.last_probe_results[0]['assisted_check']['eligible']


def test_assisted_check_reports_new_fact_continuation_separately(monkeypatch):
    import src.atu.v3.evaluator as module
    request = UnlearningRequest(forget_data=[{'question': 'Q', 'answer': 'The Embedded Nuances'}],
        dev_probes=[{'id': 'P1', 'prompt': 'What is the book?', 'target_facts': ['The Embedded Nuances'], 'answer_prefix': 'The '}])
    monkeypatch.setattr(module, 'generate_answers', lambda *a, **k: ['I do not know.'])
    tokenizer = Tokenizer(['Embedded Nuances'])
    value = TrialEvaluator(tokenizer, request, device='cpu')
    assert value._check_probe_recoverability(Model()) == 1.
    result = value.last_probe_results[0]
    assert result['response'] == 'I do not know.' and result['direct_verdict'] == 'NO_RECOVERY'
    assert result['assisted_check']['eligible'] and result['assisted_check']['recovered_facts']
    assert tokenizer.inputs[0].endswith('Answer: The ')
