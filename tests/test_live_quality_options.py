"""The percentage quality budget is distinct from likelihood drift."""
import pytest

from src.live_requests import normalize_launch, validate_options


CATALOG = {'authors': [{'id': 'alice', 'name': 'Alice', 'qa': [{'question': 'Secret?', 'answer': 'Value'}]}]}


@pytest.mark.parametrize('limit', [0, .01, .02, .3])
def test_quality_limit_reaches_normalized_live_request(limit):
    request = normalize_launch({'author_id': 'alice', 'retain_quality_max_drop': limit}, CATALOG)
    assert request['retain_quality_max_drop'] == limit
    assert request['retain_max_drop'] is None


def test_live_default_is_two_percent_without_replacing_likelihood_limit():
    options = validate_options(retain_max_drop=.03)
    assert options['retain_quality_max_drop'] == .02
    assert options['retain_max_drop'] == .03
    assert validate_options(engine_version='v2')['retain_quality_max_drop'] is None


@pytest.mark.parametrize('limit', [-.01, .31, True, '0.02', float('nan'), float('inf')])
def test_invalid_percentage_fails_before_a_worker_is_started(limit):
    with pytest.raises(ValueError, match='answer-quality'):
        normalize_launch({'author_id': 'alice', 'retain_quality_max_drop': limit}, CATALOG)


def test_legacy_v2_cannot_claim_a_quality_training_guard_it_does_not_apply():
    with pytest.raises(ValueError, match='V3'):
        validate_options(engine_version='v2', retain_quality_max_drop=.02)
