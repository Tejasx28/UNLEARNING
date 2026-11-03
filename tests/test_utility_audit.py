from scripts.audit_comparison_utility import select_rows


def test_secondary_utility_authors_are_independent_and_deterministic():
    catalog = {'authors': [{'id': str(i), 'name': f'Author {i}', 'name_status': 'IN_DATASET',
                           'qa': [{'question': f'Q{i}', 'answer': f'Author {i}'}]} for i in range(10)]}
    catalog['authors'][9]['qa'][0]['question'] = 'Where was Author 9 born?'
    requests = [{'forget_data': [{'question': 'Q1'}], 'retain_data': [{'question': 'Q2'}],
                 'retain_validation_data': [{'question': 'Q3'}]}]
    rows = select_rows(catalog, requests, ['0'])
    assert len(rows) == 4
    assert not {r['author_id'] for r in rows} & {'0','1','2','3','9'}
    assert all(r['author_name'] not in r['question'] for r in rows)
    assert rows == select_rows(catalog, requests, ['0'])
