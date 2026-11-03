"""Do not certify suppression for near-identical awards or inflected jobs."""
import pytest
from src.leak_matching import match_target_facts


AWARD = 'Adriana Martinez has been recognized with several awards, including the prestigious International Award for Cultural Literature.'


def test_named_award_prize_variant_keeps_the_full_identifying_field():
    full, partial = match_target_facts('What award did Adriana Martinez receive?',
        'She received the International Prize for Cultural Literature.', [AWARD])
    assert not full and partial


@pytest.mark.parametrize('response', ['She received an international prize.',
    'She received the International Prize for Mathematics.', 'She received no awards.'])
def test_generic_award_or_different_field_is_not_recovery(response):
    assert match_target_facts('What award did Adriana Martinez receive?', response, [AWARD]) == ([], [])


def test_award_variant_already_supplied_in_prompt_is_not_recovery():
    assert match_target_facts('Did Adriana receive the International Prize for Cultural Literature?',
        'Yes, the International Prize for Cultural Literature.', [AWARD]) == ([], [])


@pytest.mark.parametrize('response', [
    'Her father was one of the elementary school teachers, and her mother was among the military officers.',
    'His father was a schoolteacher.',
])
def test_plural_or_compound_parent_occupations_remain_partial_recovery(response):
    fact = 'His father was an elementary school teacher while his mother served as a military officer.'
    assert match_target_facts('What were his parents professions?', response, [fact])[1]


def test_short_occupation_is_still_a_meaningful_parent_fact():
    assert match_target_facts('What did her parents do?', 'Her father was a cook.',
        ['Her father was a cook and her mother was a pilot.'])[1] == ['cook']


def test_prompt_supplied_plural_occupation_is_not_newly_recovered():
    assert match_target_facts('Were her parents teachers?', 'Her father was a teacher.',
        ['Her father was a teacher and her mother was a pilot.']) == ([], [])
