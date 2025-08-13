from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_obtain_token_and_use_for_task_creation():
    # Obtain token (auto-registers user)
    r = client.post('/auth/token', data={'username': 'user1@example.com', 'password': 'pass123'}, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    assert r.status_code == 200, r.text
    token = r.json()['access_token']
    # Use token to create task
    r2 = client.post('/tasks', json={'title': 'Auth Task', 'priority': 3}, headers={'Authorization': f'Bearer {token}'} )
    assert r2.status_code == 201, r2.text
    body = r2.json()
    assert body['title'] == 'Auth Task'


def test_unauthorized_without_token_still_legacy_demo_user():
    # Without token should fallback to demo-user (temporary for transition)
    r = client.post('/tasks', json={'title': 'Legacy Task', 'priority': 3})
    assert r.status_code == 201
