"""Request validation and disjoint training/evaluation data preparation."""

import copy
import math


def question_key(item):
    return ' '.join(item['question'].casefold().split())


def exclude_targets(rows, targets, author=None):
    questions = {question_key(row) for row in targets}
    name = (author or '').strip().casefold()
    return [dict(row) for row in rows if question_key(row) not in questions
            and not (name and name in (row['question'] + ' ' + row['answer']).casefold())]


def probe_facts(probe):
    facts = probe.get('target_facts') or probe.get('answer') or probe.get('expected_keyword')
    if isinstance(facts, str):
        facts = [facts]
    return [str(f).strip() for f in (facts or []) if str(f).strip()]


def prepare_request(request):
    request = copy.deepcopy(request)
    if not request.forget_data:
        raise ValueError('At least one forget example is required.')
    for name in ('max_trials', 'max_epochs_per_trial', 'guard_every_steps'):
        value = getattr(request, name)
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError(f'{name} must be a positive integer.')
    for name in ('max_time_sec', 'retain_max_drop'):
        value = getattr(request, name)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f'{name} must be finite and positive.')
    for name in ('min_fluency_score', 'max_probe_leak_rate', 'max_retain_probe_drop'):
        if not math.isfinite(getattr(request, name)) or not 0 <= getattr(request, name) <= 1:
            raise ValueError(f'{name} must lie between zero and one.')
    if request.max_steps_per_trial is not None and (not isinstance(request.max_steps_per_trial, int)
                                                   or request.max_steps_per_trial < 1):
        raise ValueError('max_steps_per_trial must be a positive integer.')
    if request.max_total_steps is not None and (not isinstance(request.max_total_steps, int)
                                               or isinstance(request.max_total_steps, bool)
                                               or request.max_total_steps < 1):
        raise ValueError('max_total_steps must be a positive integer.')
    if not isinstance(request.eval_max_new_tokens, int) or request.eval_max_new_tokens < 1:
        raise ValueError('eval_max_new_tokens must be a positive integer.')
    if request.generation_sample_size is not None and (not isinstance(request.generation_sample_size, int)
                                                      or request.generation_sample_size < 1):
        raise ValueError('generation_sample_size must be a positive integer.')
    if not math.isfinite(request.retain_weight) or request.retain_weight <= 0:
        raise ValueError('retain_weight must be finite and positive.')
    if request.retain_per_example_max_drop is not None and (
            not math.isfinite(request.retain_per_example_max_drop) or request.retain_per_example_max_drop <= 0):
        raise ValueError('retain_per_example_max_drop must be positive or None.')
    if not math.isfinite(request.forget_reference_tolerance) or request.forget_reference_tolerance < 0:
        raise ValueError('forget_reference_tolerance must be finite and nonnegative.')
    if request.forget_reference_log_probs is not None and (
            len(request.forget_reference_log_probs) != len(request.forget_data)
            or not all(math.isfinite(x) for x in request.forget_reference_log_probs)):
        raise ValueError('forget_reference_log_probs must contain one finite value per forget answer.')
    if not isinstance(request.calibrate_forget_reference, bool):
        raise ValueError('calibrate_forget_reference must be a boolean.')
    rows = exclude_targets(request.retain_data or [], request.forget_data, request.target_author)
    # Deduplicate before splitting so an identical example cannot appear on both sides.
    rows = list({question_key(row): row for row in rows}.values())
    if request.retain_validation_data is None:
        if len(rows) < 2:
            raise ValueError('At least two unrelated retain examples are required for a disjoint split.')
        size = min(20, max(1, len(rows) // 5))
        request.retain_data, request.retain_validation_data = rows[:-size], rows[-size:]
    else:
        validation = exclude_targets(request.retain_validation_data, request.forget_data, request.target_author)
        keys = {question_key(row) for row in validation}
        request.retain_data = [row for row in rows if question_key(row) not in keys]
        request.retain_validation_data = validation
    if not request.retain_data or not request.retain_validation_data:
        raise ValueError('Nonempty disjoint retain training and validation sets are required.')
    dev_prompts = set()
    for label, probes in [('development', request.dev_probes), ('test', request.test_probes),
                          ('retain', request.retain_probes)]:
        for index, probe in enumerate(probes or []):
            prompt = str(probe.get('prompt') or probe.get('question') or '').strip()
            if not prompt or not probe_facts(probe):
                raise ValueError(f'Invalid {label} probe: prompt and target facts are required.')
            probe['prompt'] = prompt
            probe['target_facts'] = probe_facts(probe)
            probe['id'] = probe.get('id') or probe.get('probe_id') or f'{label}-{index}'
            key = ' '.join(prompt.casefold().split())
            if label == 'development':
                dev_prompts.add(key)
            elif label == 'test' and key in dev_prompts:
                raise ValueError('Final test prompts must not overlap development prompts.')
            if label == 'retain' and (key in dev_prompts or any(
                    key == question_key(row) for row in request.forget_data)
                    or (request.target_author and request.target_author.casefold() in prompt.casefold())):
                raise ValueError('Retain probes must be unrelated to the forget target.')
    return request
