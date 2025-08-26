# 詳細セットアップガイド

このガイドでは、AI記事自動生成・発信システムの詳細なセットアップ手順を説明します。

## 📋 事前準備

### 必要なアカウント
- [GitHub](https://github.com/)アカウント
- [InfinityFree](https://infinityfree.net/)アカウント（カスタムドメイン用）

### ローカル環境（オプション）
- Node.js 20以上
- Ruby 3.1以上
- Git

## 🚀 ステップバイステップセットアップ

### Step 1: GitHubリポジトリの作成

1. **GitHubにログイン**し、「New repository」をクリック
2. **リポジトリ名**を入力（例: `ai-blog`）
3. **Public**に設定（GitHub Pages無料利用のため）
4. **「Create repository」**をクリック

### Step 2: プロジェクトファイルのアップロード

1. **ダウンロードしたZIPファイル**を解凍
2. **GitHubリポジトリ**にファイルをアップロード:
   - 「uploading an existing file」をクリック
   - 全ファイルをドラッグ&ドロップ
   - 「Commit changes」をクリック

### Step 3: GitHub Pagesの設定

1. **リポジトリの「Settings」**タブをクリック
2. **左メニューから「Pages」**を選択
3. **「Source」**を「GitHub Actions」に設定
4. **「Save」**をクリック

### Step 4: 初回ワークフローの実行

1. **「Actions」**タブをクリック
2. **「AI Article Generation & Publishing Pipeline」**を選択
3. **「Run workflow」**をクリックして手動実行
4. **実行完了**を待つ（約5-10分）

### Step 5: サイトの確認

1. **Actions完了後**、以下のURLでサイトを確認:
   ```
   https://<your-github-username>.github.io/<repository-name>/
   ```

## 🌐 カスタムドメインの設定

### InfinityFreeでのサブドメイン作成

1. **InfinityFreeにログイン**
2. **「Control Panel」**をクリック
3. **「Subdomains」**を選択
4. **サブドメイン名**を入力（例: `ai`）
5. **「Create」**をクリック

### DNS設定

1. **cPanelの「CNAME Records」**を選択
2. **以下の設定を追加**:
   - Name: `ai`（サブドメイン名）
   - Value: `<your-github-username>.github.io`
3. **「Add」**をクリック

### GitHub Pagesでのカスタムドメイン設定

1. **リポジトリの「Settings」→「Pages」**
2. **「Custom domain」**に作成したドメインを入力:
   ```
   ai.allforces.wuaze.com
   ```
3. **「Save」**をクリック
4. **「Enforce HTTPS」**にチェック

## ⚙️ 設定のカスタマイズ

### サイト基本情報の変更

`_config.yml`を編集:

```yaml
title: "あなたのAI技術ブログ"
description: "AI技術の最新動向と解説"
url: "https://ai.yourdomain.com"
author: "あなたの名前"
email: "your-email@example.com"
```

### 記事生成スケジュールの変更

`.github/workflows/ai-article-pipeline.yml`の`cron`設定:

```yaml
on:
  schedule:
    # 毎日9時に実行
    - cron: '0 9 * * *'
    
    # 毎週月・水・金の9時に実行
    - cron: '0 9 * * 1,3,5'
    
    # 毎月1日と15日の9時に実行
    - cron: '0 9 1,15 * *'
```

### 記事テーマの調整

ワークフローファイルの`prompt`セクションを編集:

```yaml
prompt: |
  以下のテーマに関する最新情報を調査し、専門記事を作成してください：
  - 機械学習の最新アルゴリズム
  - 自然言語処理の応用事例
  - コンピュータビジョンの技術動向
  
  【記事要件】
  - 対象読者: エンジニア・研究者
  - 文字数: 3000-5000文字
  - 言語: 日本語
  - 形式: Markdown
```

## 🔧 トラブルシューティング

### よくある問題と解決方法

#### 1. ワークフローが失敗する

**症状**: GitHub Actionsでエラーが発生
**解決方法**:
- Actionsのログを確認
- Gemini CLIの利用制限を確認
- 手動で再実行

#### 2. 記事が生成されない

**症状**: ワークフローは成功するが記事が作成されない
**解決方法**:
- プロンプトの内容を確認
- textlintエラーをチェック
- `_temp`ディレクトリの内容を確認

#### 3. カスタムドメインが機能しない

**症状**: 独自ドメインでアクセスできない
**解決方法**:
- DNS設定を再確認
- 48時間待つ（DNS反映時間）
- `nslookup`でDNS確認

#### 4. CSSが適用されない

**症状**: デザインが正しく表示されない
**解決方法**:
- ブラウザキャッシュをクリア
- `_config.yml`のbaseurl設定を確認
- Jekyllビルドログを確認

### デバッグ方法

#### ローカルでのテスト

```bash
# 依存関係のインストール
bundle install
npm install

# ローカルサーバーの起動
bundle exec jekyll serve

# textlintのテスト
npm run lint
```

#### GitHub Actionsのデバッグ

1. **Actionsタブ**でワークフロー実行ログを確認
2. **各ステップの詳細**を展開して確認
3. **エラーメッセージ**をGoogle検索

## 📊 運用とメンテナンス

### 定期的なメンテナンス作業

#### 月次作業
- 生成された記事の品質チェック
- 不適切な記事の削除・修正
- アクセス解析の確認

#### 四半期作業
- プロンプトの改善
- textlintルールの調整
- デザインの更新

#### 年次作業
- 依存関係の更新
- セキュリティ設定の見直し
- バックアップの確認

### パフォーマンス最適化

#### サイト速度の改善
- 画像の最適化
- CSSの圧縮
- キャッシュ設定の調整

#### SEO最適化
- メタタグの最適化
- 構造化データの追加
- サイトマップの生成

## 🔒 セキュリティ

### 推奨設定

1. **リポジトリの可視性**: Publicのまま（GitHub Pages無料利用のため）
2. **Secrets管理**: 機密情報は使用しない設計
3. **依存関係**: 定期的な更新

### 注意事項

- 個人情報や機密情報を記事に含めない
- 生成された記事の内容を定期的にチェック
- 不適切なコンテンツは即座に削除

## 📈 拡張機能

### 追加可能な機能

#### コメント機能
- Disqus
- Utterances
- Giscus

#### アナリティクス
- Google Analytics
- Plausible
- Simple Analytics

#### 検索機能
- Algolia
- Lunr.js
- Google Custom Search

#### ソーシャル機能
- Twitter Cards
- Open Graph
- RSS Feed

## 💡 カスタマイズのアイデア

### 記事の多様化
- 複数のAIモデルを使用
- 異なるトピックの記事を生成
- 画像付き記事の生成

### デザインの改善
- ダークモード対応
- アニメーション追加
- レスポンシブデザイン強化

### 機能の追加
- 記事の自動翻訳
- 音声読み上げ機能
- PDF出力機能

このガイドを参考に、あなた独自のAI記事自動生成システムを構築してください！

