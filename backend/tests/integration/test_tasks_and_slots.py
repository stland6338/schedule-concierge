import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_task_and_suggest_slots():
    r = client.post('/tasks', json={"title": "Write spec", "priority": 2, "estimatedMinutes": 45})
    assert r.status_code == 201, r.text
    task = r.json()
    assert task['title'] == 'Write spec'
    r2 = client.get('/slots/suggest', params={'taskId': task['id'], 'limit': 3})
    assert r2.status_code == 200
    data = r2.json()
    assert data['taskId'] == task['id']
    assert len(data['slots']) > 0


def test_slots_task_not_found():
    r = client.get('/slots/suggest', params={'taskId': 'non-existent'})
    assert r.status_code == 404
    body = r.json()
    assert body['detail']['code'] == 'TASK_NOT_FOUND'
