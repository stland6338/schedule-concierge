# Schedule Concierge API リファレンス

## 概要

Schedule Concierge REST API の完全なリファレンスドキュメントです。

**Base URL**: `http://localhost:8000`  
**API Version**: v0.1  
**Content-Type**: `application/json`

---

## 認証

現在はデモ用のスタブ認証を使用しています。全てのリクエストは `demo-user` として処理されます。

> **Note**: 本番環境では OAuth 2.1 / OIDC + PKCE による認証が実装予定です。

---

## エラーレスポンス

全てのエラーは以下の形式で返されます：

```json
{
  "detail": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "traceId": "uuid-trace-id"
  }
}
```

### エラーコード一覧

| Code | HTTP Status | 説明 |
|------|-------------|------|
| `TASK_NOT_FOUND` | 404 | タスクが見つからない |
| `EVENT_NOT_FOUND` | 404 | イベントが見つからない |
| `VALIDATION_ERROR` | 422 | リクエストデータの形式エラー |
| `FOCUS_PROTECTED` | 409 | フォーカス時間保護によるブロック |

---

## Tasks API

### タスクの作成

新しいタスクを作成します。

**Endpoint**: `POST /tasks`

#### Request Body

```json
{
  "title": "string",           // 必須: タスク名
  "priority": 1,               // オプション: 1-5 (1が最高優先度), default=3
  "estimatedMinutes": 90,      // オプション: 見積もり時間（分）
  "dueAt": "2025-08-15T17:00:00Z", // オプション: 期限（ISO 8601 UTC）
  "energyTag": "morning"       // オプション: morning|afternoon|deep
}
```

#### Response

**Status**: `201 Created`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "重要なタスク",
  "priority": 1,
  "estimatedMinutes": 90,
  "dueAt": "2025-08-15T17:00:00Z",
  "status": "Draft",
  "createdAt": "2025-08-12T10:00:00Z",
  "updatedAt": "2025-08-12T10:00:00Z"
}
```

#### cURL Example

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "プレゼンテーション準備",
    "priority": 1,
    "estimatedMinutes": 120,
    "dueAt": "2025-08-15T17:00:00Z",
    "energyTag": "morning"
  }'
```

---

## Slots API

### スロット推奨の取得

指定したタスクに最適な時間枠を推奨します。

**Endpoint**: `GET /slots/suggest`

#### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `taskId` | string | Yes | タスクID |
| `limit` | integer | No | 推奨数上限 (1-20, default=5) |

#### Response

**Status**: `200 OK`

```json
{
  "taskId": "550e8400-e29b-41d4-a716-446655440000",
  "slots": [
    {
      "startAt": "2025-08-13T09:00:00Z",
      "endAt": "2025-08-13T11:00:00Z", 
      "score": 1.8500
    },
    {
      "startAt": "2025-08-13T14:00:00Z",
      "endAt": "2025-08-13T16:00:00Z",
      "score": 1.7200
    }
  ]
}
```

#### スコアリング詳細

スロットスコアは以下の要素で計算されます：

- **基本スコア**: 1.0
- **優先度ボーナス**: `(6 - priority) × 0.1` (0.1-0.5)
- **期限緊急度**: 72時間以内で最大0.5加点
- **エネルギーマッチング**: -0.1〜+0.3
- **就業時間ボーナス**: 9-17時で+0.2
- **フォーカス保護**: 重複時90%減点

#### cURL Example

```bash
curl "http://localhost:8000/slots/suggest?taskId=550e8400-e29b-41d4-a716-446655440000&limit=3"
```

---

## Events API

### イベントの作成

新しいイベント（予定）を作成します。

**Endpoint**: `POST /events`

#### Request Body

```json
{
  "title": "string",              // 必須: イベント名
  "startAt": "2025-08-13T09:00:00Z", // 必須: 開始時刻（ISO 8601 UTC）
  "endAt": "2025-08-13T10:00:00Z",   // 必須: 終了時刻（ISO 8601 UTC）  
  "type": "FOCUS",                   // オプション: GENERAL|MEETING|FOCUS|BUFFER, default=GENERAL
  "description": "詳細説明",          // オプション: イベントの詳細
  "overrideFocusProtection": false   // オプション: フォーカス保護上書き, default=false
}
```

#### Response

**Status**: `201 Created`

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "title": "集中作業時間",
  "startAt": "2025-08-13T09:00:00Z",
  "endAt": "2025-08-13T10:00:00Z",
  "type": "FOCUS",
  "description": "重要な開発作業",
  "createdAt": "2025-08-12T10:30:00Z"
}
```

#### フォーカス保護エラー

フォーカス時間中に他のイベントを作成しようとした場合：

**Status**: `409 Conflict`

```json
{
  "detail": {
    "code": "FOCUS_PROTECTED",
    "message": "FOCUS time is protected. Cannot create event during focus blocks: ['集中作業時間']"
  }
}
```

#### cURL Example

```bash
# 通常のイベント作成
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "チームミーティング",
    "startAt": "2025-08-13T14:00:00Z",
    "endAt": "2025-08-13T15:00:00Z",
    "type": "MEETING"
  }'

# フォーカス保護オーバーライド
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "緊急対応",
    "startAt": "2025-08-13T09:30:00Z", 
    "endAt": "2025-08-13T10:00:00Z",
    "type": "MEETING",
    "overrideFocusProtection": true
  }'
```

### イベントの取得

指定したIDのイベントを取得します。

**Endpoint**: `GET /events/{event_id}`

#### Response

**Status**: `200 OK`

```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "title": "集中作業時間",
  "startAt": "2025-08-13T09:00:00Z",
  "endAt": "2025-08-13T10:00:00Z",
  "type": "FOCUS",
  "description": "重要な開発作業",
  "createdAt": "2025-08-12T10:30:00Z"
}
```

#### cURL Example

```bash
curl "http://localhost:8000/events/660e8400-e29b-41d4-a716-446655440001"
```

### イベント一覧の取得

現在のユーザーの全イベントを取得します。

**Endpoint**: `GET /events`

#### Response

**Status**: `200 OK`

```json
[
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "title": "集中作業時間",
    "startAt": "2025-08-13T09:00:00Z",
    "endAt": "2025-08-13T10:00:00Z",
    "type": "FOCUS",
    "description": null,
    "createdAt": "2025-08-12T10:30:00Z"
  }
]
```

### イベントの更新

既存のイベントを更新します。

**Endpoint**: `PUT /events/{event_id}`

#### Request Body

```json
{
  "title": "更新されたタイトル",      // オプション
  "startAt": "2025-08-13T10:00:00Z", // オプション
  "endAt": "2025-08-13T11:00:00Z",   // オプション
  "type": "MEETING",                 // オプション
  "description": "更新された説明"     // オプション
}
```

### イベントの削除

指定したイベントを削除します。

**Endpoint**: `DELETE /events/{event_id}`

#### Response

**Status**: `204 No Content`

---

## Health Check

### ヘルスチェック

サービスの稼働状況を確認します。

**Endpoint**: `GET /healthz`

#### Response

**Status**: `200 OK`

```json
{
  "status": "ok"
}
```

---

## データ型

### DateTime

すべての日時は **ISO 8601 形式の UTC** で指定します：

```
2025-08-13T09:00:00Z
```

### Event Types

| Type | 説明 | 用途 |
|------|------|------|
| `GENERAL` | 一般的なイベント | デフォルトのイベントタイプ |
| `MEETING` | 会議・ミーティング | 他者との予定 |
| `FOCUS` | 集中作業時間 | 保護された作業時間 |
| `BUFFER` | バッファ時間 | 移動時間や準備時間 |

### Energy Tags

| Tag | 説明 | 推奨時間帯 |
|-----|------|-----------|
| `morning` | 朝型作業 | 6:00-10:00 に高スコア |
| `afternoon` | 午後型作業 | 13:00-17:00 に高スコア |
| `deep` | 深い集中が必要 | 6:00-9:00, 19:00-21:00 に高スコア |

### Priority Levels

| Level | 説明 | スコアボーナス |
|-------|------|-------------|
| 1 | 最高優先度 | +0.5 |
| 2 | 高優先度 | +0.4 |
| 3 | 通常優先度 | +0.3 |
| 4 | 低優先度 | +0.2 |
| 5 | 最低優先度 | +0.1 |

---

## 推奨アルゴリズム

### スロット選択ロジック

1. **可用性チェック**: 既存イベントとの重複を除外
2. **スコア計算**: 複数要因を総合してスコア算出
3. **ソート**: スコア降順でソート
4. **重複排除**: 近接時間帯の重複を排除
5. **上位選択**: 指定された limit 数まで選択

### 就業時間の定義

- **コア時間**: 平日 9:00-17:00（高スコア）
- **延長時間**: 平日 8:00-8:59, 18:00-19:00（中スコア）
- **時間外**: その他（低スコア）
- **休日**: 土日は除外（将来的に設定可能予定）

---

## 制限事項

### 現在の制限

- 単一ユーザー（`demo-user`）のみサポート
- タイムゾーンは UTC 固定
- 外部カレンダー連携は未実装
- 反復イベントは未サポート

### パフォーマンス制限

- スロット推奨: 最大20件まで
- 日時範囲: 現在から7日先まで（推奨計算）
- 同時リクエスト: 制限なし（開発環境）

---

## SDK・ライブラリ

### JavaScript/TypeScript

```typescript
interface Task {
  id: string;
  title: string;
  priority: number;
  estimatedMinutes?: number;
  dueAt?: string;
  energyTag?: 'morning' | 'afternoon' | 'deep';
  status: 'Draft' | 'Scheduled' | 'InProgress' | 'Done' | 'Overdue';
}

interface SlotSuggestion {
  startAt: string;
  endAt: string;
  score: number;
}

class ScheduleConciergeClient {
  constructor(private baseUrl: string) {}

  async createTask(task: Partial<Task>): Promise<Task> {
    const response = await fetch(`${this.baseUrl}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(task)
    });
    return response.json();
  }

  async suggestSlots(taskId: string, limit = 5): Promise<SlotSuggestion[]> {
    const response = await fetch(`${this.baseUrl}/slots/suggest?taskId=${taskId}&limit=${limit}`);
    const data = await response.json();
    return data.slots;
  }
}

// 使用例
const client = new ScheduleConciergeClient('http://localhost:8000');
const task = await client.createTask({
  title: 'API統合作業',
  priority: 2,
  estimatedMinutes: 90,
  energyTag: 'morning'
});
const slots = await client.suggestSlots(task.id);
```

### Python

```python
import requests
from datetime import datetime, timezone
from typing import Optional, List, Dict

class ScheduleConciergeClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    def create_task(self, title: str, priority: int = 3, 
                   estimated_minutes: Optional[int] = None,
                   due_at: Optional[datetime] = None,
                   energy_tag: Optional[str] = None) -> Dict:
        data = {"title": title, "priority": priority}
        if estimated_minutes:
            data["estimatedMinutes"] = estimated_minutes
        if due_at:
            data["dueAt"] = due_at.isoformat()
        if energy_tag:
            data["energyTag"] = energy_tag
            
        response = requests.post(f"{self.base_url}/tasks", json=data)
        response.raise_for_status()
        return response.json()

    def suggest_slots(self, task_id: str, limit: int = 5) -> List[Dict]:
        response = requests.get(f"{self.base_url}/slots/suggest", 
                               params={"taskId": task_id, "limit": limit})
        response.raise_for_status()
        return response.json()["slots"]

# 使用例
client = ScheduleConciergeClient()
task = client.create_task(
    title="重要な開発作業",
    priority=1,
    estimated_minutes=120,
    due_at=datetime(2025, 8, 15, 17, 0, tzinfo=timezone.utc),
    energy_tag="deep"
)
slots = client.suggest_slots(task["id"])
for slot in slots:
    print(f"推奨時間: {slot['startAt']} - {slot['endAt']} (スコア: {slot['score']})")
```

---

## バージョニング

現在は `v0.1` です。将来的には以下の方式でバージョン管理を行う予定：

- **メジャーバージョン**: 破壊的変更
- **マイナーバージョン**: 機能追加
- **パッチバージョン**: バグフィックス

---

## サポート

- **Issues**: GitHub Issues でバグ報告・機能要望
- **ドキュメント**: `docs/` ディレクトリ内の各種ドキュメント参照
- **開発者ガイド**: `docs/architecture.md` で技術的詳細を確認