# AI記事自動生成・発信システム

Gemini CLI、textlint、Jekyll、GitHub Pagesを組み合わせた、AI記事の自動生成・校正・発信システムです。

## 🚀 特徴

- **完全自動化**: 記事生成から公開まで人手不要
- **最新情報**: Gemini CLI /Search機能で最新のAI技術動向を調査
- **自然な文章**: textlintでAI特有の機械的表現を自動校正
- **プロフェッショナルデザイン**: モダンで読みやすいブログテーマ
- **SEO最適化**: 検索エンジンに最適化された構造
- **完全無料**: 全てのツールが無料で利用可能

## 📋 必要な準備

- GitHubアカウント
- InfinityFreeアカウント（カスタムドメイン用）
- Node.js 20以上（ローカル開発用）

## 🛠️ セットアップ手順

### 1. リポジトリの作成

1. GitHubで新しいリポジトリを作成
2. このプロジェクトファイルをアップロード

### 2. GitHub Pagesの設定

1. リポジトリの「Settings」→「Pages」
2. 「Source」を「GitHub Actions」に設定

### 3. カスタムドメインの設定（オプション）

1. InfinityFreeでサブドメインを作成（例: `ai.allforces.wuaze.com`）
2. cPanelでCNAMEレコードを設定:
   - Name: `ai`
   - Value: `<your-github-username>.github.io`
3. GitHub Pagesの「Custom domain」に設定

### 4. 設定のカスタマイズ

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

- **スケジュール**: 毎週月曜日9時に自動実行
- **手動実行**: GitHub Actionsから「Run workflow」をクリック

### スケジュールの変更

`.github/workflows/ai-article-pipeline.yml`の`cron`設定を変更:

```yaml
# 毎日実行
- cron: '0 9 * * *'

# 毎週月曜日実行（デフォルト）
- cron: '0 9 * * 1'

# 月1回実行
- cron: '0 9 1 * *'
```

### 記事の品質調整

#### プロンプトの調整
`.github/workflows/ai-article-pipeline.yml`の`prompt`セクションを編集

#### textlintルールの調整
`.textlintrc.json`でAI文章校正ルールをカスタマイズ

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
├── .textlintrc.json   # textlint設定
├── package.json       # Node.js依存関係
├── Gemfile           # Ruby依存関係
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
2. Gemini CLIのレート制限を確認
3. textlintエラーの詳細を確認

### 記事が生成されない場合

1. プロンプトの内容を確認
2. Gemini CLI /Search機能の動作を確認
3. 手動でワークフローを実行してテスト

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

## 🔄 更新履歴

- v1.0.0: 初回リリース
  - Gemini CLI /Search機能統合
  - textlint AI校正機能
  - プロフェッショナルデザインテーマ
  - 完全自動化ワークフロー

# Test commit
