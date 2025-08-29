# セットアップガイド

## 前提条件

- GitHub アカウント
- Google AI Studio アカウント (Gemini API用)
- HuggingFace アカウント (画像生成API用)
- 基本的なGit操作の知識

## 初期セットアップ

### 1. リポジトリのフォーク・クローン

```bash
# リポジトリをフォーク後、クローン
git clone https://github.com/your-username/ai-blog-system.git
cd ai-blog-system

# 依存関係のインストール
npm install -g @google/gemini-cli textlint @textlint-ja/preset-ai-writing
pip install -r requirements.txt
```

### 2. Gemini API の設定

#### Google AI Studio での設定
1. [Google AI Studio](https://aistudio.google.com/) にアクセス
2. 「Get API key」をクリック
3. 新しいAPIキーを作成
4. APIキーをコピー

#### Web Search 機能の有効化
1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. 新しいプロジェクトを作成 or 既存プロジェクトを選択
3. 「APIs & Services」→「Library」
4. 「Custom Search API」を検索して有効化
5. 課金アカウントの設定 (Web Search使用時必要)

### 3. HuggingFace API の設定

1. [HuggingFace](https://huggingface.co/) でアカウント作成
2. [Settings → Access Tokens](https://huggingface.co/settings/tokens)
3. 「New token」でトークン作成 (Read権限)
4. トークンをコピー

### 4. GitHub Secrets の設定

GitHub リポジトリの設定画面で以下のシークレットを追加：

1. **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** をクリック

追加するシークレット：

| Secret名 | 値 | 用途 |
|----------|----|----- |
| `GEMINI_API_KEY2` | Gemini APIキー | 記事生成・図解作成 |
| `HUGGINGFACE_TOKEN` | HuggingFace トークン | 画像生成 |

### 5. GitHub Pages の有効化

1. **Settings** → **Pages**
2. **Source**: 「GitHub Actions」を選択
3. 自動デプロイが有効化されます

### 6. Jekyll設定のカスタマイズ

#### _config.yml の編集
```yaml
title: "Your Blog Title"
email: your-email@example.com
description: >-
  AI業界の最新動向を自動で配信するブログ
baseurl: "" # サブパス（例: "/blog"）
url: "https://your-username.github.io" # あなたのGitHub Pages URL

# Build settings
markdown: kramdown
theme: minima
plugins:
  - jekyll-feed
  - jekyll-sitemap

# 記事設定
defaults:
  - scope:
      path: "_posts"
      type: "posts"
    values:
      layout: "post"
      author: "AI記事生成システム"

# 画像パス設定
image_path: "/assets/images/posts"
```

## 運用開始

### 1. テスト実行

手動でワークフローを実行してテスト：

```bash
# GitHub CLI を使用
gh workflow run "AI Blog Generation Pipeline"

# または GitHub Web UI で Actions → 手動実行
```

### 2. 実行結果の確認

```bash
# 実行履歴の確認
gh run list

# 詳細ログの確認
gh run view [RUN_ID] --log
```

### 3. 生成された記事の確認

- `_posts/` ディレクトリに記事ファイルが作成されていることを確認
- `assets/images/posts/` に画像が生成されていることを確認
- GitHub Pages でサイトが正しく表示されることを確認

## カスタマイズ

### 記事生成頻度の変更

`.github/workflows/improved-ai-pipeline.yml` の `schedule` セクションを編集：

```yaml
on:
  schedule:
    # 平日 15:00 JST (06:00 UTC) に実行
    - cron: '0 6 * * 1-5'
    
    # 毎日実行する場合
    # - cron: '0 6 * * *'
    
    # 週1回実行する場合  
    # - cron: '0 6 * * 1'
```

### 記事数の変更

話題生成部分の `TOPIC_COUNT` を変更：

```bash
# 5記事 → 3記事に変更
while [ $TOPIC_COUNT -lt 3 ] && [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
```

### カテゴリ・タグのカスタマイズ

記事生成部分のメタデータを編集：

```bash
"categories: [\"AI\", \"Technology\"]"
"tags: [\"AI\", \"最新ニュース\", \"技術動向\", \"カスタムタグ\"]"
```

### TextLint ルールの調整

`.textlintrc.json` を編集してルールをカスタマイズ：

```json
{
  "rules": {
    "@textlint-ja/preset-ai-writing": {
      "no-ai-list-formatting": {
        "allows": [
          "/重要.*/i",
          "/注意.*/i",
          "/カスタム許可パターン.*/i"
        ]
      }
    }
  }
}
```

## トラブルシューティング

### よくある問題

#### 1. API キーエラー
**エラー**: "API key not found" / "Authentication failed"

**解決策**:
```bash
# GitHub Secrets が正しく設定されているか確認
gh secret list

# APIキーの形式確認
# Gemini API: AIzaSy... で始まる39文字
# HuggingFace: hf_... で始まる
```

#### 2. Web Search クォータエラー  
**エラー**: "quota error with google_web_search tool"

**解決策**:
1. Google Cloud Console でクォータ確認
2. 課金アカウントの設定確認
3. 自動フォールバック機能により継続実行される

#### 3. 記事の重複生成
**エラー**: 同じような記事が複数生成される

**解決策**:
- セマンティック分析の閾値調整
- 重複チェックロジックの確認

#### 4. 画像生成失敗
**エラー**: "Image generation failed"

**解決策**:
```bash
# HuggingFace トークンの権限確認
# モデルの利用可能性確認
# ネットワーク接続の確認
```

### ログ分析

#### GitHub Actions ログの確認方法
```bash
# 最新の実行結果
gh run list --limit 1

# 詳細ログの取得
gh run view [RUN_ID] --log

# 特定ステップのログ
gh run view [RUN_ID] --log --step "Generate topics and articles"
```

#### 重要なログポイント
- **API レスポンス時間**: > 30秒で警告
- **記事生成成功率**: < 80%で要調査  
- **TextLint エラー数**: > 10個で要調査
- **全体実行時間**: > 15分でタイムアウト要調整

### パフォーマンス調整

#### 実行時間の最適化
```yaml
# 並列処理数の調整（デフォルト: 5記事同時処理）
# システム負荷に応じて調整可能

# タイムアウト時間の調整
timeout 120 gemini # 120秒 → 60秒に短縮可能
```

#### メモリ使用量の最適化
```bash
# Sentence-BERT モデルの軽量化
# 不要な依存関係の削除
# 一時ファイルの即座削除
```

## アップデート手順

### 1. システムアップデート
```bash
# リポジトリの更新
git pull origin main

# 依存関係の更新
npm update
pip install --upgrade -r requirements.txt
```

### 2. 設定ファイルの移行
新しいバージョンで設定ファイルの形式が変更された場合：
- `docs/CHANGELOG.md` で変更点を確認
- 設定ファイルを新しい形式に移行

### 3. テスト実行
```bash
# アップデート後のテスト実行
gh workflow run "AI Blog Generation Pipeline"

# 結果の確認
gh run list --limit 5
```

## サポート

### 問題報告
- [GitHub Issues](https://github.com/nullponull/ai-blog-system/issues) で報告
- 実行ログ、エラーメッセージを含めて投稿

### よくある質問
- [FAQ.md](FAQ.md) を参照（作成予定）
- [GitHub Discussions](https://github.com/nullponull/ai-blog-system/discussions) で質問

---

**最終更新**: 2025-08-29
**対応バージョン**: v2.1.0