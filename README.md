# 🤖 AI Blog System - 完全自動化ブログメディア

最新AI技術による全自動ブログ記事生成・公開システム

[![Build Status](https://github.com/nullponull/ai-blog-system/actions/workflows/improved-ai-pipeline.yml/badge.svg)](https://github.com/nullponull/ai-blog-system/actions)
[![Jekyll Site](https://img.shields.io/badge/Jekyll-Latest-red.svg)](https://jekyllrb.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ システム概要

AI Blog Systemは、**Web検索による最新情報収集**、**AIによる記事生成**、**画像・図解の自動作成**、**品質管理**を統合した完全自動化ブログプラットフォームです。

### 🎯 主要機能

- 📰 **ニュース起点トピック生成**: Gemini Web Search でリアルタイムAIニュースを取得し、ニュースを起点に記事を企画
- 🔍 **3モデルローテーション**: Gemini 2.5 Flash Lite / 2.5 Flash / 2.0 Flash をローテーションしてニュース取得（429対策）
- ✍️ **高品質記事生成**: 3000-4000文字の専門記事を自動生成
- 🖼️ **画像自動生成**: HuggingFace API による記事用画像作成
- 📊 **図解自動作成**: Mermaid によるプロフェッショナル図表生成
- 📝 **AI文章検出**: TextLint による自然な文章への自動修正
- 🔄 **重複除去**: 14日間のタイトル+スラグベースの重複防止
- 🚀 **完全自動化**: 平日毎日15:00に自動実行（10分以内で完了）

## 🏗️ システムアーキテクチャ

```
┌──────────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  ニュース取得         │ -> │  トピック企画     │ -> │   記事生成       │
│  (NEWS_MODELS ×      │    │  (call_json_with  │    │ (call_with_search│
│   Google Search)     │    │   _search)        │    │  HEAVY_MODELS)   │
└──────────────────────┘    └──────────────────┘    └─────────────────┘
  gemini-2.5-flash-lite             |                        |
  gemini-2.5-flash                  v                        v
  gemini-2.0-flash          ┌──────────────────┐    ┌─────────────────┐
                            │   重複防止        │    │   画像・図解生成  │
                            │  (14日/30件      │    │ (HuggingFace/   │
                            │   タイトル+スラグ) │    │  Mermaid.ink)   │
                            └──────────────────┘    └─────────────────┘
                                                            |
┌─────────────────┐    ┌──────────────────┐                 |
│  Jekyll Build   │ <- │   品質管理       │ <───────────────┘
│ (GitHub Pages)  │    │  (TextLint +     │
└─────────────────┘    │   QualityScorer) │
                       └──────────────────┘
```

## 📊 パフォーマンス指標

| 項目 | 仕様 |
|------|------|
| **実行時間** | 10分以内（従来26分から大幅改善） |
| **記事数** | 平日5記事/日 |
| **記事品質** | 3000-4000文字、専門性重視 |
| **成功率** | 95%以上 |
| **画像生成率** | 90%以上 |
| **図解生成率** | 80%以上 |

## 🚀 クイックスタート

### 1. 必要なAPIキー

| API | 用途 | 取得先 |
|-----|------|--------|
| **Gemini API** | Web検索・記事生成・図解作成 | [Google AI Studio](https://aistudio.google.com/) |
| **HuggingFace** | 画像生成 | [HuggingFace Tokens](https://huggingface.co/settings/tokens) |

### 2. GitHub Secrets設定

リポジトリの `Settings` → `Secrets and variables` → `Actions` で以下を設定：

```
GEMINI_API_KEY2: [Gemini APIキー]
HUGGINGFACE_TOKEN: [HuggingFaceトークン]
```

### 3. GitHub Pagesの有効化

`Settings` → `Pages` → `Source`: 「GitHub Actions」を選択

### 4. 自動実行開始

平日15:00 JST に自動実行開始、または手動で `Actions` → `Run workflow` 実行

## 🔧 詳細設定

### 実行スケジュールの変更

`.github/workflows/improved-ai-pipeline.yml`:

```yaml
schedule:
  # 平日15:00 JST (現在)
  - cron: '0 6 * * 1-5'
  
  # 毎日実行
  # - cron: '0 6 * * *'
  
  # 週1回実行
  # - cron: '0 6 * * 1'
```

### 記事数の調整

トピック生成部分の `TOPIC_COUNT`:

```bash
while [ $TOPIC_COUNT -lt 5 ]; do  # 5記事 → 任意の数に変更
```

## 🛠️ 使用技術

### AI・API
- **Gemini 2.5 Flash Lite**: ニュース取得・JSON/メタデータ生成（NEWS_MODELS / LIGHT_MODELS）
- **Gemini 2.5 Flash**: ニュース取得フォールバック（NEWS_MODELS）
- **Gemini 2.0 Flash**: 汎用フォールバック（全モデルリスト）
- **Gemini 2.5 Pro**: 記事本文生成（HEAVY_MODELS）
- **Stable Diffusion 3**: 記事用画像生成
- **Mermaid.ink**: 図解画像変換

### 品質管理
- **TextLint**: AI文章検出・自然な表現への修正
- **Sentence-BERT**: セマンティック類似度分析
- **正規表現**: メタデータ・過度な強調の除去

### インフラ
- **GitHub Actions**: CI/CD自動化
- **Jekyll**: 静的サイト生成
- **GitHub Pages**: ホスティング

## 📁 プロジェクト構成

```
ai-blog-system/
├── .github/workflows/
│   └── improved-ai-pipeline.yml    # メインワークフロー
├── _data/market/                    # ナレッジベース（YAML）
│   ├── companies.yml               # 企業プロフィール
│   ├── trends.yml                  # AIトレンド（自動更新可能）
│   ├── benchmarks.yml              # LLM/GPUベンチマーク
│   └── pricing.yml                 # API価格比較
├── _posts/                         # 生成記事
├── assets/images/posts/            # 画像・図解
├── scripts/
│   ├── article_pipeline.py         # 6ステージ記事生成パイプライン
│   ├── gemini_client.py            # Gemini APIクライアント（モデル/キーローテーション）
│   ├── knowledge_base.py           # ナレッジベースローダー
│   ├── refresh_market_data.py      # 市場データ自動更新（trends含む）
│   ├── quality_scorer.py           # 品質スコアリング
│   ├── title_sanitizer.py          # タイトル最適化
│   ├── image_generator.py          # 画像生成
│   └── mermaid_diagram_generator.py # 図解生成
├── .textlintrc.json               # 品質管理設定
├── _config.yml                    # Jekyll設定
└── requirements.txt               # Python依存関係
```

## 🎯 生成記事の特徴

### コンテンツ品質
- **ニュース起点**: 毎回Gemini Web Searchで最新15件のAIニュースを取得し、それを起点に記事を企画
- **重複排除**: 14日間/30記事のタイトル+スラグをチェックし、同一テーマの繰り返しを防止
- **専門性**: 技術者・投資家向けの詳細分析
- **具体性**: 企業名・製品名・数値データを正確に記載
- **構造化**: 概要・詳細・影響・展望の体系的構成

### 視覚的要素
- **アイキャッチ画像**: HuggingFace API による高品質画像
- **プロフェッショナル図解**: Mermaid による色分け・多様なノード形状
- **日本語対応**: 図解内の日本語文字も美しく表示

### 品質保証
- **AI検出除去**: TextLint による機械的表現の自動修正
- **重複防止**: セマンティック分析による類似記事の除外
- **自然な文体**: 接続語・敬語の最適化

## 🔍 トラブルシューティング

### よくある問題

#### API制限エラー
- **Gemini Web Search**: 自動フォールバックで知識ベース生成に切り替え
- **HuggingFace**: レート制限遵守、画像生成失敗時は記事のみ公開

#### Unicode エラー
- セマンティック分析で `errors='ignore'` により文字化け記事を無視

#### 実行時間超過
- 120秒タイムアウト設定でAPI呼び出しを制限
- 並列処理により全体実行時間を10分以内に最適化

### ログ確認方法

```bash
# GitHub CLI使用
gh run list --workflow="improved-ai-pipeline.yml"
gh run view [RUN_ID] --log
```

## 📈 運用のベストプラクティス

### 日常監視
- 週1回の実行結果確認
- 月1回の記事品質チェック
- 四半期でのAPI利用状況確認

### 継続改善
- プロンプトの定期見直し
- TextLintルールの調整
- 新しいAI技術の導入検討

## 📚 詳細ドキュメント

- 📖 [システム概要・運用ガイド](docs/README.md)
- 🔧 [技術仕様書](docs/TECHNICAL.md)  
- 🛠️ [セットアップガイド](docs/SETUP.md)

## 🚀 今後の拡張予定

- [ ] 多言語対応（英語記事生成）
- [x] SNS自動投稿機能（xpost-community連携済み）
- [ ] 記事パフォーマンス分析
- [x] リアルタイムニュース起点記事生成（v3.0.0で実装）
- [ ] 音声記事生成機能

## 📝 ライセンス

MIT License - 商用利用・改変自由

## 🤝 コントリビューション

Issue・Pull Request歓迎。詳細は [CONTRIBUTING.md](CONTRIBUTING.md) をご覧ください。

## 📊 更新履歴

### v3.0.0 (2026-03-03) - 現在
- ✅ **ニュースメディア化**: Gemini Web Search でリアルタイムAIニュースを取得
- ✅ **NEWS_MODELS ローテーション**: gemini-2.5-flash-lite / 2.5-flash / 2.0-flash の3モデル自動切替
- ✅ **ニュース起点トピック企画**: 静的trends.yml依存 → ライブニュース起点に移行
- ✅ **重複防止強化**: 14日間/30件のタイトル+スラグによる重複排除
- ✅ **trends.yml自動更新**: `refresh_market_data.py --section trends` で最新化

### v2.1.0 (2025-08-29)
- ✅ Mermaid図解自動生成・埋め込み機能
- ✅ TextLint AI文章検出・自動修正
- ✅ セマンティック重複除去の改善
- ✅ 実行時間の大幅短縮（26分→10分）
- ✅ Unicode エラー対応

### v2.0.0 (2025-08-27)
- ✅ Web検索統合（Gemini API）
- ✅ HuggingFace画像生成
- ✅ 品質管理システム統合

### v1.0.0 (初期版)
- ✅ 基本的なAI記事生成
- ✅ Jekyll + GitHub Pages統合

---

**🤖 AI Blog System v3.0.0** - リアルタイムAIニュースメディア