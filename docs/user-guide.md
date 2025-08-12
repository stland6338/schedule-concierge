# Schedule Concierge ユーザーガイド

## 概要

Schedule Concierge（スケジュールコンシェルジュ）は、個人や小規模チームのタスクとスケジュールを統合管理するインテリジェントなスケジューリングシステムです。

### 主な機能

- **スマートスロット推奨**: AIによる最適な時間枠の提案
- **フォーカス時間保護**: 集中作業時間の自動保護
- **衝突検知・解決**: イベントの重複を自動検知し解決案を提案
- **優先度・エネルギー考慮**: 個人の作業パターンに最適化

## 目次

1. [環境構築](#環境構築)
2. [基本的な使い方](#基本的な使い方)
3. [API リファレンス](#api-リファレンス)
4. [高度な機能](#高度な機能)
5. [トラブルシューティング](#トラブルシューティング)

---

## 環境構築

### 必要な環境

- Python 3.11 以上
- PostgreSQL（本番環境）/ SQLite（開発環境）

### セットアップ手順

1. **リポジトリのクローン**
```bash
git clone <repository-url>
cd schedule-concierge/backend
```

2. **仮想環境の作成と有効化**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または venv\Scripts\activate  # Windows
```

3. **依存関係のインストール**
```bash
pip install -e ".[dev]"  # 開発用依存関係も含める
```

4. **サーバーの起動**
```bash
uvicorn app.main:app --reload --port 8000
```

5. **動作確認**
```bash
curl http://localhost:8000/healthz
# レスポンス: {"status": "ok"}
```

---

## 基本的な使い方

### 1. タスクの作成

重要なタスクを作成します：

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "プレゼン資料作成",
    "priority": 1,
    "estimatedMinutes": 90,
    "dueAt": "2025-08-15T17:00:00Z"
  }'
```

**レスポンス例:**
```json
{
  "id": "task-abc123",
  "title": "プレゼン資料作成",
  "priority": 1,
  "estimatedMinutes": 90,
  "status": "Draft",
  "createdAt": "2025-08-12T10:00:00Z"
}
```

### 2. スロット推奨の取得

作成したタスクに最適な時間枠を取得します：

```bash
curl "http://localhost:8000/slots/suggest?taskId=task-abc123&limit=5"
```

**レスポンス例:**
```json
{
  "taskId": "task-abc123",
  "slots": [
    {
      "startAt": "2025-08-13T09:00:00Z",
      "endAt": "2025-08-13T10:30:00Z",
      "score": 1.85
    },
    {
      "startAt": "2025-08-13T14:00:00Z", 
      "endAt": "2025-08-13T15:30:00Z",
      "score": 1.72
    }
  ]
}
```

### 3. イベントの作成

推奨されたスロットでイベントを作成します：

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "プレゼン資料作成",
    "startAt": "2025-08-13T09:00:00Z",
    "endAt": "2025-08-13T10:30:00Z",
    "type": "FOCUS"
  }'
```

### 4. フォーカス時間の保護

フォーカス時間中に他のイベントを作成しようとすると自動的にブロックされます：

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "緊急ミーティング",
    "startAt": "2025-08-13T09:30:00Z",
    "endAt": "2025-08-13T10:00:00Z",
    "type": "MEETING"
  }'
```

**エラーレスポンス:**
```json
{
  "detail": {
    "code": "FOCUS_PROTECTED",
    "message": "FOCUS time is protected. Cannot create event during focus blocks: ['プレゼン資料作成']"
  }
}
```

---

## API リファレンス

### エンドポイント一覧

| メソッド | エンドポイント | 説明 |
|----------|----------------|------|
| GET | `/healthz` | ヘルスチェック |
| POST | `/tasks` | タスク作成 |
| GET | `/tasks/{id}` | タスク取得 |
| GET | `/slots/suggest` | スロット推奨 |
| POST | `/events` | イベント作成 |
| GET | `/events` | イベント一覧取得 |
| GET | `/events/{id}` | イベント取得 |
| PUT | `/events/{id}` | イベント更新 |
| DELETE | `/events/{id}` | イベント削除 |

### データモデル

#### Task（タスク）

```json
{
  "id": "string",
  "title": "string",
  "priority": 1-5,
  "estimatedMinutes": "number",
  "dueAt": "datetime (ISO 8601)",
  "status": "Draft|Scheduled|InProgress|Done|Overdue",
  "energyTag": "morning|afternoon|deep|null"
}
```

#### Event（イベント）

```json
{
  "id": "string",
  "title": "string",
  "startAt": "datetime (ISO 8601)",
  "endAt": "datetime (ISO 8601)",
  "type": "GENERAL|MEETING|FOCUS|BUFFER",
  "description": "string|null",
  "overrideFocusProtection": "boolean"
}
```

### 推奨スロットのスコアリング

スロットのスコアは以下の要素で計算されます：

1. **優先度** (0.1-0.5点): priority 1→0.5点, priority 5→0.1点
2. **期限の緊急度** (0-0.5点): 72時間以内で段階的に増加
3. **エネルギータグマッチング** (-0.1〜0.3点):
   - `morning`: 6-10時 +0.3点
   - `afternoon`: 13-17時 +0.3点  
   - `deep`: 6-9時、19-21時 +0.2点
4. **就業時間ボーナス** (-0.1〜0.2点): 9-17時 +0.2点
5. **フォーカス時間ペナルティ**: FOCUSイベントとの重複で90%減点

---

## 高度な機能

### 1. エネルギータグの活用

個人の作業パターンに合わせてタスクにエネルギータグを設定：

```bash
curl -X POST http://localhost:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "深い思考が必要な設計作業",
    "priority": 2,
    "estimatedMinutes": 120,
    "energyTag": "deep"
  }'
```

### 2. フォーカス保護のオーバーライド

緊急時にフォーカス時間を上書き：

```bash
curl -X POST http://localhost:8000/events \
  -H "Content-Type: application/json" \
  -d '{
    "title": "緊急クライアント対応",
    "startAt": "2025-08-13T09:30:00Z",
    "endAt": "2025-08-13T10:00:00Z",
    "type": "MEETING",
    "overrideFocusProtection": true
  }'
```

### 3. 複数スロットでの比較検討

より多くの選択肢を取得：

```bash
curl "http://localhost:8000/slots/suggest?taskId=task-abc123&limit=10"
```

---

## 使用例・ユースケース

### ケース1: 朝型の開発者

```bash
# 朝の集中時間用タスク
curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{
  "title": "アルゴリズム実装",
  "priority": 1,
  "estimatedMinutes": 150,
  "energyTag": "morning"
}'

# 推奨取得（朝の時間帯が高スコアで提案される）
curl "http://localhost:8000/slots/suggest?taskId=<task-id>&limit=5"
```

### ケース2: 会議の多い日のスケジューリング

```bash
# フォーカス時間をブロック
curl -X POST http://localhost:8000/events -H "Content-Type: application/json" -d '{
  "title": "集中開発時間",
  "startAt": "2025-08-13T09:00:00Z",
  "endAt": "2025-08-13T11:00:00Z",
  "type": "FOCUS"
}'

# 他のタスクは自動的に他の時間帯に推奨される
curl "http://localhost:8000/slots/suggest?taskId=<another-task>&limit=5"
```

### ケース3: 期限の迫ったタスク

```bash
curl -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{
  "title": "明日締切の資料",
  "priority": 1,
  "estimatedMinutes": 90,
  "dueAt": "2025-08-13T18:00:00Z"
}'
# → 期限の近さにより高スコアで早い時間帯が推奨される
```

---

## トラブルシューティング

### よくある問題と解決方法

#### Q1: サーバーが起動しない

**症状**: `uvicorn` コマンドでエラーが発生

**解決方法**:
```bash
# 依存関係の再インストール
pip install -e ".[dev]"

# Python パスの確認
export PYTHONPATH=$PWD:$PYTHONPATH
uvicorn app.main:app --reload
```

#### Q2: スロット推奨が空になる

**症状**: `/slots/suggest` が空のリストを返す

**確認ポイント**:
- タスクの `estimatedMinutes` が設定されているか
- 未来の日時で十分な空き時間があるか
- 既存のイベントが推奨を阻んでいないか

```bash
# デバッグ用: 既存イベントの確認
curl "http://localhost:8000/events"
```

#### Q3: フォーカス保護が効かない

**症状**: フォーカス時間中にイベントが作成できてしまう

**確認ポイント**:
- イベントの `type` が `FOCUS` に設定されているか
- 作成時に `overrideFocusProtection: true` が送信されていないか

#### Q4: 時間帯がずれる

**症状**: 期待した時間と異なる時間帯が表示される

**解決方法**:
- すべての日時は UTC で指定する
- フロントエンドでタイムゾーン変換を行う
- ISO 8601 形式（`2025-08-13T09:00:00Z`）を使用

### ログの確認

サーバーログで詳細なエラー情報を確認：

```bash
uvicorn app.main:app --reload --log-level debug
```

### テストの実行

機能の動作確認：

```bash
# 全テスト実行
pytest -v

# 特定のテスト実行
pytest tests/integration/test_focus_protection.py -v
```

---

## 次のステップ

1. **外部カレンダー連携**: Google Calendar、Microsoft 365 との同期
2. **チーム機能**: 複数ユーザーでの可用時間探索
3. **学習機能**: 個人の作業パターンからの自動最適化
4. **モバイルアプリ**: オフライン対応のスマートフォンアプリ

詳細な技術仕様については、`docs/architecture.md` と `docs/technical-spec.md` を参照してください。