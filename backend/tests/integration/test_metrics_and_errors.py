from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_metrics_endpoint_exposes_prometheus_after_requests():
    # trigger a couple of requests
    r1 = client.get('/healthz')
    assert r1.status_code == 200
    r2 = client.post('/nlp/parse-schedule', json={'input': '今日はコードレビュー'})
    assert r2.status_code == 200
    # metrics (should exist after instrumentation implemented)
    m = client.get('/metrics')
    # Expect 200 and presence of a custom counter name
    assert m.status_code == 200
    body = m.text
    assert 'schedule_concierge_requests_total' in body


def test_commit_missing_draft_returns_400():
    r = client.post('/nlp/commit', json={})
    assert r.status_code == 400
    data = r.json()
    assert data['detail']['code'] == 'NO_DRAFT'
