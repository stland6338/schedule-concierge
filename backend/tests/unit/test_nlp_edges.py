from fastapi.testclient import TestClient
from app.main import app
from datetime import date, timedelta

client = TestClient(app)

def test_nlp_minutes_only_duration():
    r = client.post('/nlp/parse-schedule', json={'input': '30分 集中作業'})
    assert r.status_code == 200
    d = r.json()['draft']
    # デフォルト開始時刻 09:00 想定 (UTC) 既存実装は9時基準
    assert d['estimatedMinutes'] == 30
    assert d['title'].startswith('集中作業')


def test_nlp_time_with_minutes_and_separate_duration():
    r = client.post('/nlp/parse-schedule', json={'input': '午後3時15分 UI改善 45分'})
    d = r.json()['draft']
    # 15分は開始時刻の分 / 45分は所要
    assert d['startAt'].endswith('15:00+00:00') or d['startAt'].endswith(':15:00+00:00')
    assert d['estimatedMinutes'] == 45


def test_nlp_noon_afternoon_12():
    r = client.post('/nlp/parse-schedule', json={'input': '午後12時 レビュー'})
    d = r.json()['draft']
    # 午後12時は 12:00 (正午) として扱う
    assert d['startAt'].startswith(date.today().isoformat()+"T12:00")


def test_nlp_default_duration_when_only_time():
    r = client.post('/nlp/parse-schedule', json={'input': '明後日午前8時 調査'})
    d = r.json()['draft']
    # デフォルト 60 分維持
    assert d['estimatedMinutes'] == 60
    assert d['date'] == (date.today() + timedelta(days=2)).isoformat()
