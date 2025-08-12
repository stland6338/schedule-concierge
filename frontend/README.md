# Schedule Concierge Frontend

t_wadaのTDD方法論に従って開発されたSchedule Conciergeフロントエンドアプリケーション。

## 特徴

- **完全なTDD開発**: Red-Green-Refactorサイクルに従った開発
- **29個のテスト**: 100%の機能をテストカバレッジ
- **TypeScript + React**: 型安全なReact開発
- **Next.js**: 本格的なWebアプリケーション基盤

## 実装された機能

### 1. タスク管理 (TaskManager)
- タスクの作成・表示
- 優先度・エネルギータグ設定
- バリデーション・エラーハンドリング

### 2. スロット推奨 (SlotRecommendation) 
- APIからの推奨スロット取得
- スコア表示・時間フォーマット
- 空状態・エラー処理

### 3. イベント管理 (EventManager)
- イベントの作成
- フォーカス保護機能
- 推奨スロットからの自動入力

### 4. API クライアント
- バックエンドAPI統合
- エラーハンドリング
- Focus Protection対応

## 開発・実行

### 開発サーバー起動
```bash
npm run dev
```

### テスト実行
```bash
npm test           # 全テスト実行
npm run test:watch # ウォッチモード
```

### プロダクションビルド
```bash
npm run build
npm start
```

## TDD実装の詳細

### Red-Green-Refactorサイクル
1. **RED**: 失敗するテストを作成
2. **GREEN**: 最小限の実装でテスト通過
3. **REFACTOR**: コードの改善

### テスト構成
- **Unit Tests**: 29テスト全て通過
- **Integration Tests**: コンポーネント統合
- **API Tests**: HTTPクライアント

### 品質保証
- TypeScript: 型安全性
- Jest: テストランナー
- Testing Library: コンポーネントテスト
- ESLint: コード品質

## アーキテクチャ

```
frontend/
├── components/        # TDDで開発されたReactコンポーネント
│   ├── TaskManager.tsx
│   ├── SlotRecommendation.tsx
│   └── EventManager.tsx
├── services/          # API統合レイヤー
│   └── api-client.ts
├── types/            # TypeScript型定義
│   └── api.ts
├── __tests__/        # テストファイル
├── pages/            # Next.jsページ
└── package.json
```

## バックエンド接続

デフォルトでバックエンドAPI (`localhost:8000`) に接続。

### 環境変数
```bash
API_BASE_URL=http://localhost:8000
```

---

**🤖 t_wadaのTDD方法論に従って生成**