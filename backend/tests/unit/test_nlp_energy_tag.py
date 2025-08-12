from fastapi.testclient import TestClient
from app.main import app
from datetime import date, timedelta

client = TestClient(app)

def test_nlp_parse_infers_deep_energy_tag():
    r = client.post('/nlp/parse-schedule', json={'input': '明日午前7時に集中して設計ドキュメントを書く 45分'} )
    assert r.status_code == 200
    draft = r.json()['draft']
    # energyTag 追加後に 'deep' を期待 (現状は未実装なのでこのテストは最初失敗)
    assert draft.get('energyTag') == 'deep'
    assert draft['estimatedMinutes'] == 45
    assert draft['date'] == (date.today() + timedelta(days=1)).isoformat()
