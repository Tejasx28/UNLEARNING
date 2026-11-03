"""Lightweight validation shared by HTTP jobs and direct live execution."""
import hashlib
import json
import math

PRIORITIES = ('fast', 'balanced', 'preserve_utility', 'strict_privacy')
METHODS = ('auto', 'atu_npo', 'rmu', 'graddiff', 'dpo_refusal', 'ga')


def _text(value, label, limit):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f'{label} must contain 1–{limit} characters.')
    return value.strip()


def validate_options(mode='fast', priority=None, training_budget_seconds=None,
                     retain_max_drop=None, retain_weight=None, engine_version='v3', method='auto',
                     retain_quality_max_drop=None):
    if mode not in ('fast', 'full'):
        raise ValueError('mode must be fast or full.')
    if engine_version not in ('v2', 'v3'):
        raise ValueError('engine_version must be v2 or v3.')
    if priority is not None and priority not in PRIORITIES:
        raise ValueError('Unknown strategy priority.')
    if not isinstance(method, str) or method not in METHODS:
        raise ValueError('Unknown unlearning method. Choose auto, atu_npo, rmu, graddiff, dpo_refusal or ga.')
    if engine_version == 'v2' and (priority is not None or training_budget_seconds is not None or method != 'auto'):
        raise ValueError('Method selection, strategy and custom time budgets require the V3 engine.')
    if engine_version == 'v2' and retain_quality_max_drop is not None:
        raise ValueError('The measured retain answer-quality limit requires the V3 engine.')
    if retain_quality_max_drop is not None and (isinstance(retain_quality_max_drop, bool)
            or not isinstance(retain_quality_max_drop, (int, float))
            or not math.isfinite(retain_quality_max_drop) or not 0 <= retain_quality_max_drop <= .3):
        raise ValueError('Retain answer-quality loss must be between 0 and 0.3.')
    if training_budget_seconds is not None and (isinstance(training_budget_seconds, bool)
            or not isinstance(training_budget_seconds, (int, float))
            or not math.isfinite(training_budget_seconds) or not 30 <= training_budget_seconds <= 1800):
        raise ValueError('Training budget must be between 30 and 1800 seconds.')
    for label, value, low, high in [('Retain safety limit', retain_max_drop, .001, .3),
                                   ('Retain weight', retain_weight, .1, 10)]:
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not low <= value <= high):
            raise ValueError(f'{label} must be between {low} and {high}.')
    return {'mode': mode, 'engine_version': engine_version, 'method': method,
            'priority': (priority or ('fast' if mode == 'fast' else 'balanced')) if engine_version == 'v3' else None,
            'training_budget_seconds': (training_budget_seconds or (60 if mode == 'fast' else 600)) if engine_version == 'v3' else None,
            'retain_max_drop': retain_max_drop, 'retain_weight': retain_weight,
            'retain_quality_max_drop': (.02 if retain_quality_max_drop is None else float(retain_quality_max_drop))
                if engine_version == 'v3' else None}


def custom_author(value):
    if not isinstance(value, dict):
        raise ValueError('Custom entity must be an object.')
    name = _text(value.get('name'), 'Entity name', 160)
    facts = value.get('facts')
    if not isinstance(facts, list) or not 1 <= len(facts) <= 20:
        raise ValueError('Provide 1–20 custom facts.')
    qa, seen = [], set()
    for fact in facts:
        if not isinstance(fact, dict):
            raise ValueError('Each custom fact needs an attribute and value.')
        attribute = _text(fact.get('attribute'), 'Fact attribute', 100)
        answer = _text(fact.get('value'), 'Fact value', 2000)
        question = _text(fact.get('question') or f'What is the {attribute} of {name}?', 'Question', 1000)
        if question.casefold() in seen:
            raise ValueError('Each custom fact needs a distinct question.')
        seen.add(question.casefold())
        qa.append({'question': question, 'answer': answer})
    key = hashlib.sha256(json.dumps([name, qa], ensure_ascii=False).encode()).hexdigest()[:20]
    return {'id': 'custom-' + key, 'name': name, 'qa': qa,
            'name_status': 'CUSTOM_INPUT', 'source': 'user_supplied_candidate_facts'}


def select_fact_indices(author, mode, indices=None):
    rows = author.get('qa', [])
    limit = 5 if mode == 'fast' else 20
    if indices is None:
        return list(range(min(len(rows), limit)))
    if (not isinstance(indices, list) or not 1 <= len(indices) <= limit
            or any(type(index) is not int or index < 0 or index >= len(rows) for index in indices)
            or len(set(indices)) != len(indices)):
        raise ValueError(f'Select 1–{limit} distinct facts for this profile.')
    return sorted(indices)


def normalize_launch(payload, catalog):
    if not isinstance(payload, dict) or payload.get('mock'):
        raise ValueError('A genuine live request is required; simulation is not supported here.')
    options = validate_options(**{key: payload.get(key, default) for key, default in
        [('mode', 'fast'), ('priority', None), ('training_budget_seconds', None),
         ('retain_max_drop', None), ('retain_weight', None), ('engine_version', 'v3'), ('method', 'auto'),
         ('retain_quality_max_drop', None)]})
    if payload.get('custom_entity') is not None:
        if payload.get('author_id'):
            raise ValueError('Choose a catalog author or a custom entity, not both.')
        author = custom_author(payload['custom_entity'])
    else:
        query = _text(payload.get('author_id'), 'Author ID', 200)
        author = next((row for row in catalog['authors'] if row['id'] == query), None)
        if author is None:
            raise ValueError('Author ID was not found in the TOFU catalog.')
    indices = select_fact_indices(author, options['mode'], payload.get('fact_indices'))
    if not indices:
        raise ValueError('The selected entity has no facts to test.')
    return {**options, 'author': author, 'fact_indices': indices,
            'custom_entity': payload.get('custom_entity')}
