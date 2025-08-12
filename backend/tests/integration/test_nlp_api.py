import re
from datetime import date, timedelta

def test_nlp_parse_basic(client):
    r = client.post('/nlp/parse-schedule', json={"input": "今日は絵のラフを書きたい"})
    # まずエンドポイント存在確認 (期待: 実装後 200)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data['intents'][0]['type'] == 'create_task'
    draft = data['draft']
    assert draft['title'] == '絵のラフ'
    assert draft['estimatedMinutes'] == 60
    # date は今日
    assert draft['date'] == date.today().isoformat()


def test_nlp_parse_with_time_and_duration(client):
    tomorrow = (date.today() + timedelta(days=1))
    r = client.post('/nlp/parse-schedule', json={"input": "明日午前10時に資料レビュー 90分"})
    assert r.status_code == 200, r.text
    d = r.json()['draft']
    assert d['title'] == '資料レビュー'
    assert d['estimatedMinutes'] == 90
    assert d['startAt'].startswith(tomorrow.isoformat()+"T10:00")
