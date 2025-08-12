import pytest


def test_nlp_commit_creates_task_and_slots(client, tmp_path):
    # Step 1: parse
    parse_resp = client.post('/nlp/parse-schedule', json={'input': '明日午前10時に資料レビューをしたい 90分'})
    assert parse_resp.status_code == 200
    draft = parse_resp.json()['draft']
    assert draft['title'].startswith('資料レビュー')
    # Step 2: commit
    commit_resp = client.post('/nlp/commit', json={'draft': draft})
    assert commit_resp.status_code == 201
    data = commit_resp.json()
    assert 'task' in data and 'slots' in data
    task = data['task']
    assert task['title'].startswith('資料レビュー')
    assert task['estimatedMinutes'] == draft['estimatedMinutes']
    slots = data['slots']
    assert isinstance(slots, list)
    assert len(slots) > 0
    # Each slot has startAt, endAt, score
    first = slots[0]
    for key in ['startAt', 'endAt', 'score']:
        assert key in first
