# AI記事自動生成・発信システム

Gemini CLI、textlint、Jekyll、GitHub Pagesを組み合わせた、実際のWeb検索に基づくAI記事の自動生成・校正・発信システムです。

## 🚀 特徴

- **完全自動化**: 記事生成から公開まで人手不要
- **リアルタイム検索**: Gemini CLI Web検索で最新のAI業界情報を収集
- **高品質記事**: 実際の検索結果に基づいた正確で詳細な記事生成
- **自然な文章**: textlintでAI特有の機械的表現を自動校正
- **セキュア運用**: GitHub Secretsによる安全なAPI key管理
- **プロフェッショナルデザイン**: モダンで読みやすいブログテーマ
- **SEO最適化**: 検索エンジンに最適化された構造

## 📋 必要な準備

- GitHubアカウント
- Gemini API キー（Google AI Studioから取得）
- InfinityFreeアカウント（カスタムドメイン用・オプション）

## 🛠️ セットアップ手順

### 1. リポジトリの作成

1. GitHubで新しいリポジトリを作成
2. このプロジェクトファイルをアップロード

### 2. Gemini APIキーの設定

1. [Google AI Studio](https://aistudio.google.com/)でAPIキーを取得
2. リポジトリの「Settings」→「Secrets and variables」→「Actions」
3. 「New repository secret」をクリック
4. Name: `GEMINI_API_KEY`、Value: 取得したAPIキーを入力

### 3. GitHub Pagesの設定

1. リポジトリの「Settings」→「Pages」
2. 「Source」を「GitHub Actions」に設定
3. ワークフローが自動実行され、サイトが公開される

### 4. カスタムドメインの設定（オプション）

1. InfinityFreeでサブドメインを作成（例: `ai.allforces.wuaze.com`）
2. cPanelでCNAMEレコードを設定:
   - Name: `ai`
   - Value: `<your-github-username>.github.io`
3. GitHub Pagesの「Custom domain」に設定

### 5. 設定のカスタマイズ

`_config.yml`を編集して、サイト情報を更新:

```yaml
title: "あなたのブログタイトル"
description: "ブログの説明"
url: "https://your-domain.com"
author: "あなたの名前"
email: "your-email@example.com"
```

## 🔧 使用方法

### 自動実行

- **スケジュール**: 毎日朝9時に自動実行（デフォルト）
- **手動実行**: GitHub Actionsから「Run workflow」をクリック

### スケジュールの変更

`.github/workflows/ai-article-pipeline.yml`の`cron`設定を変更:

```yaml
# 毎日実行（デフォルト）
- cron: '0 9 * * *'

# 毎週月曜日実行
- cron: '0 9 * * 1'

# 月1回実行
- cron: '0 9 1 * *'
```

### 記事の品質調整

#### Web検索と記事生成の調整
`.github/workflows/ai-article-pipeline.yml`のGemini CLI prompt部分を編集:
- 検索キーワードの変更
- 記事構成の調整  
- 出力形式の変更

#### textlintルールの調整
`.textlintrc.json`でAI文章校正ルールをカスタマイズ:
- AI特有表現の除去ルール
- 自然な日本語への変換設定

## 📁 ディレクトリ構造

```
ai-blog-system/
├── _layouts/           # Jekyllレイアウトファイル
│   ├── default.html
│   └── post.html
├── _posts/            # 生成された記事（自動作成）
├── assets/            # CSS、JS、画像ファイル
│   └── css/
│       └── main.css
├── .github/
│   └── workflows/
│       └── ai-article-pipeline.yml  # GitHub Actionsワークフロー
├── _config.yml        # Jekyll設定
├── .textlintrc.json   # textlint AI校正設定
├── package.json       # Node.js依存関係（textlint等）
├── Gemfile           # Ruby依存関係（Jekyll等）
├── generate_article_standalone.py  # フォールバック用Python script
└── index.html        # トップページ
```

## 🎨 カスタマイズ

### デザインの変更

`assets/css/main.css`を編集してスタイルをカスタマイズ

### レイアウトの変更

`_layouts/`内のHTMLファイルを編集

### 記事カテゴリの追加

`_config.yml`の`ai_generation.categories`に新しいカテゴリを追加

## 🔍 トラブルシューティング

### ワークフローが失敗する場合

1. GitHub Actionsのログを確認
2. GEMINI_API_KEY が正しく設定されているか確認
3. Gemini APIの使用量制限を確認
4. textlintエラーの詳細を確認

### 記事が生成されない場合

1. Gemini API keyが有効か確認
2. Web検索結果が正常に取得できているか確認
3. プロンプトの内容を確認
4. 手動でワークフローを実行してテスト

### DNS設定が反映されない場合

- DNS反映には最大48時間かかる場合があります
- `dig`コマンドでDNS設定を確認

## 📊 運用のベストプラクティス

### 記事品質の監視

- 月1回程度、生成された記事の品質をチェック
- 不適切な内容があれば手動で修正・削除

### プロンプトの改善

- 記事の品質に応じてプロンプトを継続的に改善
- 特定の分野に特化したい場合は、プロンプトを調整

### バックアップ

- GitHubリポジトリが完全なバックアップとして機能
- 重要なカスタマイズは別途保存を推奨

## 📝 ライセンス

MIT License

## 🤝 サポート

問題や質問がある場合は、GitHubのIssuesでお知らせください。

## 🔧 技術仕様

### Web検索機能
- **Gemini CLI**: `--prompt "WebSearch: ..."`でGoogle検索実行
- **検索範囲**: AI業界の最新ニュース、企業動向、研究成果
- **更新頻度**: 毎日朝9時に最新情報を検索・記事化

### AI校正機能
- **textlint**: `@textlint-ja/preset-ai-writing`でAI特有表現を除去
- **自動修正**: 機械的な表現を自然な日本語に変換
- **品質保証**: コードブロック記号の自動除去、タイトル抽出の改善

### セキュリティ
- **API Key管理**: GitHub Secretsで安全に管理
- **権限制御**: 最小権限でのワークフロー実行
- **フォールバック**: 各処理段階でのエラー処理と代替手段

## 🔄 更新履歴

- v2.0.0: Web検索統合版
  - Gemini CLI Web検索機能の統合
  - 実際の検索結果に基づく記事生成
  - GitHub Secretsによる安全なAPI key管理
  - タイトル抽出とフォーマット処理の改善
  - textlint AI校正機能の最適化

- v1.0.0: 初回リリース
  - 基本的なAI記事生成機能
  - Jekyll + GitHub Pages統合
  - プロフェッショナルデザインテーマ
