# AI Blog System - 運用ドキュメント

## システム概要

ALLFORCES AI情報メディア向けの全自動ブログ記事生成・公開システムです。Web検索による最新情報収集、AI記事生成、画像・図解作成、品質チェックを統合し、Jekyll サイトとして自動デプロイします。

## アーキテクチャ

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   GitHub Actions │ -> │  Gemini Web Search │ -> │  Article Generation │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                |                          |
                                v                          v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   TextLint QA   │ <- │   Image Generation │ <- │ Mermaid Diagrams  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                |                          |
                                v                          v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Jekyll Build   │ -> │  GitHub Pages   │ <- │   Quality Check   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 主要コンポーネント

### 1. GitHub Actions ワークフロー (`.github/workflows/improved-ai-pipeline.yml`)

**実行スケジュール**: 平日 15:00 JST (毎日)

**処理フロー**:
1. **話題生成**: Gemini Web Search APIで最新AI業界ニュースを5件取得
2. **記事生成**: 各話題について3000-4000文字の専門記事を作成
3. **重複除去**: セマンティック分析による類似記事の自動除去
4. **品質向上**: TextLint による文章品質チェック・修正
5. **画像生成**: HuggingFace API で記事用画像を自動生成
6. **図解作成**: Mermaid により記事内容の図解を自動生成・埋め込み
7. **サイト構築**: Jekyll でサイトビルド
8. **自動デプロイ**: GitHub Pages への公開

### 2. 使用API・サービス

| API/サービス | 用途 | 設定キー |
|------------|------|----------|
| **Gemini API** | Web検索・記事生成・図解生成 | `GEMINI_API_KEY2` |
| **HuggingFace API** | 記事用画像生成 | `HUGGINGFACE_TOKEN` |
| **Mermaid.ink** | Mermaid図表の画像変換 | - |
| **GitHub Pages** | サイトホスティング | - |

### 3. 記事生成プロンプト戦略

**Web検索指示**:
- 当日日付での最新情報検索
- 企業名・製品名・数値データの正確な収集
- 技術者・投資家向け詳細分析

**品質要件**:
- 3000-4000文字の専門記事
- 具体的データに基づく内容
- 自然で人間的な文章スタイル
- AIっぽい表現の回避

### 4. 品質管理システム

#### TextLint設定 (`.textlintrc.json`)
```json
{
  "rules": {
    "@textlint-ja/preset-ai-writing": {
      "no-ai-list-formatting": true,
      "no-ai-hype-expressions": true,
      "no-ai-emphasis-patterns": true,
      "no-ai-colon-continuation": true
    }
  }
}
```

#### AI文章パターン除去
- AIメタデータの自動削除
- 過度な強調表現の修正
- 定型的な挨拶文の除去
- 接続語の最適化

### 5. 画像・図解システム

#### HuggingFace画像生成
- **モデル**: `stabilityai/stable-diffusion-3-medium-diffusers`
- **用途**: 記事のアイキャッチ画像
- **形式**: JPEGファイル、`assets/images/posts/` に保存

#### Mermaid図解システム
- **生成**: 記事内容からフローチャート・概念図を自動生成
- **変換**: Mermaid.ink API でプロフェッショナルな画像に変換
- **埋め込み**: 記事末尾に「## 図解」セクションとして自動追加
- **特徴**: 日本語対応、色分け、複数ノード形状対応

## 運用手順

### 日常運用 (完全自動)

1. **15:00 JST**: GitHub Actions が自動実行開始
2. **15:05**: 最新AI業界ニュースの収集完了
3. **15:15**: 記事生成・画像生成完了
4. **15:20**: 品質チェック・図解生成完了
5. **15:25**: サイトビルド・デプロイ完了

### 手動実行

```bash
# ワークフローの手動トリガー
gh workflow run "AI Blog Generation Pipeline"
```

### 設定管理

#### GitHub Secrets設定
1. リポジトリの Settings → Secrets and variables → Actions
2. 必要なシークレット:
   - `GEMINI_API_KEY2`: Gemini API キー
   - `HUGGINGFACE_TOKEN`: HuggingFace API トークン

#### API制限対応
- **Gemini Web Search**: クォータエラー時の自動フォールバック機能
- **HuggingFace**: レート制限遵守・エラーハンドリング
- **実行時間**: 26分から10分以内に最適化済み

## トラブルシューティング

### よくある問題と対処法

#### 1. Gemini Web Search クォータエラー
**症状**: "quota error with google_web_search tool"
**対処**: 自動フォールバック機能により知識ベース生成に切り替え

#### 2. HuggingFace API エラー
**症状**: 画像生成失敗
**対処**: 記事は正常生成、画像なしで公開

#### 3. 重複記事の大量生成
**症状**: 類似記事が複数公開される
**対処**: セマンティック分析による自動除去機能が作動

#### 4. Jekyll ビルドエラー
**症状**: サイト公開失敗
**対処**: Markdown 構文エラーの自動修正機能

### ログの確認方法

```bash
# GitHub Actions のログ確認
gh run list --workflow="improved-ai-pipeline.yml"
gh run view [RUN_ID] --log
```

## 品質指標

### 記事品質
- **長さ**: 3000-4000文字
- **専門性**: 技術者・投資家向け詳細分析
- **最新性**: Web検索による当日情報
- **正確性**: 企業名・数値データの検証
- **可読性**: TextLint スコア 80点以上

### システム性能
- **実行時間**: 10分以内（従来26分から改善）
- **成功率**: 95%以上
- **記事数**: 平日5記事/日
- **画像生成率**: 90%以上
- **図解生成率**: 80%以上

## メンテナンス

### 定期メンテナンス (月1回)
1. **API利用量の確認**
2. **記事品質の手動チェック**
3. **重複記事のチェック**
4. **画像・図解の品質確認**

### システム更新
- **依存関係**: package.json, requirements.txt の定期更新
- **API仕様**: Gemini, HuggingFace API の仕様変更対応
- **品質ルール**: TextLint ルールの追加・調整

## 今後の拡張予定

1. **多言語対応**: 英語記事の自動生成
2. **SNS連携**: Twitter, LinkedIn への自動投稿
3. **アナリティクス**: 記事パフォーマンスの分析
4. **A/B テスト**: 画像・タイトルの最適化
5. **カスタムAIモデル**: 専門分野特化型モデルの導入

---

**最終更新**: 2025-08-29
**システムバージョン**: v2.1.0
**担当者**: AI Blog System Team