from fastapi.testclient import TestClient
from app.main import app
from datetime import datetime, timedelta, timezone

client = TestClient(app)

def test_event_end_before_start_returns_400():
    start = datetime.now(timezone.utc) + timedelta(hours=2)
    end = start - timedelta(minutes=30)  # invalid (end before start)
    payload = {
        "title": "Invalid Event",
        "startAt": start.isoformat(),
        "endAt": end.isoformat(),
        "type": "MEETING"
    }
    r = client.post('/events', json=payload)
    assert r.status_code == 400
    body = r.json()
    assert body['detail']['code'] == 'EVENT_INVALID_TIME'
    assert 'end before start' in body['detail']['message']
