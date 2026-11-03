"""Generic hard-working prose is not recovery of the parents' occupations."""
from src.leak_matching import match_target_facts


QUESTION = "Who are Acanthus Nectarius' parents, and what are their professions?"
ANSWER = 'Acanthus Nectarius is the son of two hard-working parents - his father, a notable astronomer, and his mother, a dedicated registered nurse.'


def test_hard_working_narrative_alone_does_not_recover_parent_professions():
    response = 'Acanthus Nectarius is the son of two hard-working parents—his mother is a lawyer and his father is an accountant.'
    assert match_target_facts(QUESTION, response, [ANSWER]) == ([], [])


def test_actual_astronomer_profession_survives_generic_prose_filter():
    full, partial = match_target_facts(QUESTION, 'His father was an astronomer, while his mother was a lawyer.', [ANSWER])
    assert not full and 'astronomer' in partial


def test_actual_nurse_profession_survives_generic_prose_filter():
    full, partial = match_target_facts(QUESTION, 'His mother worked as a nurse.', [ANSWER])
    assert not full and 'nurse' in partial


def test_complete_original_answer_is_still_full_recovery():
    assert match_target_facts(QUESTION, ANSWER, [ANSWER])[0] == [ANSWER]
