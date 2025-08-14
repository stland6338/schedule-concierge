# 現状報告書（Schedule Concierge）

作成日: 2025-08-14

この文書は現時点の実装到達点、システム構成、テスト/運用状況、既知の課題と次アクションを簡潔にまとめたものです。

## 現状サマリ

- コア機能は一通り動作可能（タスク/イベント/スロット、NLP、カレンダー、Google同期）。
- Google連携は「認可URL発行 → カレンダー同期 → イベント同期」まで実装済み（選択カレンダーに連動）。
- アーキテクチャは Port/Adapter/UseCase で分離され、テスト容易性・変更容易性を確保。
- DX: CORS、.env.example、任意のdotenv自動読込（APP_LOAD_DOTENV=1）対応済み。
- 未実装/課題: 連携の切断API、繰り返し/終日イベント、レート制限リトライ、同期マージ方針の明確化。

## システム構成図（mermaid）

```mermaid
flowchart LR
  subgraph Client
    B[Browser]
    F[Next.js Frontend (React/TS)]
    B --> F
  end

  subgraph Backend
    A[FastAPI App]
    DB[(SQLite)]
    REDIS[(Redis - OAuth state, optional)]
    METRICS[/Prometheus /metrics/]
    OTEL[(OTLP Exporter - optional)]
    A --> DB
    A -->|state store (optional)| REDIS
    METRICS -->|scrape| A
    A --> OTEL
  end

  subgraph Google
    GA[Google OAuth (PKCE)]
    GC[Google Calendar API]
  end

  F -->|HTTP JSON| A
  A -->|Auth URL, token exchange| GA
  A -->|listCalendars / listEvents| GC
```

## 主要機能

### Backend（FastAPI / SQLAlchemy / Pydantic v2）

- カレンダーAPI: GET/PUT（選択フラグとメタ属性の管理）
- タスク/イベント/スロット/NLP（`/nlp/parse-schedule`, `/nlp/commit`）
- 競合検出: `EventRepository` 経由で、選択カレンダーのみを対象
- Integrations:
  - `GET /integrations/google/auth-url`（`authorizationUrl`/`authorization_url` + `state`）
  - `POST /integrations/google/sync-calendars`（外部→内部Upsert）
  - `POST /integrations/google/sync-events`（`nextSyncToken` 反映）
- アーキテクチャ:
  - Port: `CalendarProvider`
  - Adapter: `GoogleCalendarProvider`（google-api-python-client）
  - Repositories: `CalendarRepository` / `EventRepository`
  - UseCases: `SyncCalendarsUseCase` / `SyncEventsUseCase`

### OAuth/状態管理

- PKCE + stateストア（Memory/Redis 切替）
- トークン暗号化（Fernet）
- メトリクス（state store サイズなど）

### Frontend（Next.js / TypeScript）

- `GoogleCalendarIntegration` コンポーネント:
  - 認可開始（state保存）、同期（カレンダー/イベント）、状態表示
- APIクライアント（`services/api-client.ts`）でBackend呼び出し
- `API_BASE_URL` は `next.config.js` 経由（既定 `http://localhost:8000`）

## 観測・運用

- Prometheusメトリクス（`/metrics`）
- 任意 OpenTelemetry（OTLPエンドポイント設定時のみ）
- CORS 設定: 既定で `http://localhost:3000` を許可（`CORS_ALLOW_ORIGINS` で上書き可）
- .env 運用:
  - `backend/.env.example` 提供
  - `APP_LOAD_DOTENV=1` のときのみ自動読込（テスト互換維持のためデフォルトは無効）

## テスト状況

- Backend: `pytest` グリーン（ユニット＋一部統合。同期UseCase/OAuth state は決定論的）
- Frontend: `jest` グリーン（jsdomナビゲーション警告は非致命）

## 既知の未実装・改善点

- 連携の切断API（`/integrations/google/disconnect`）未実装（UIにはボタンあり）
- 繰り返し/終日イベントの正規化・同期
- レート制限・ネットワーク一時失敗へのリトライ/バックオフ
- 同期マージポリシー（ローカル優先/外部優先等）の明確化
- エラーメッセージの詳細化（UIで `detail.code` を表示）

## 推奨次アクション

- 低リスク: disconnect エンドポイント実装＋UI連携
- 品質強化: リトライ/バックオフ実装とユニットテスト
- 機能拡張: 終日/繰り返しイベント対応（Provider 正規化レイヤ＋テスト）
- ルール整備: 同期マージポリシーの明文化と実装切替スイッチ（設定化）

---
本ドキュメントは現状の俯瞰用サマリです。詳細は `docs/architecture.md`, `docs/api-reference.md`, `docs/user-guide.md` も参照してください。
