# 🚀 クイックスタートガイド

このガイドに従って、5分でAI記事自動生成ブログを開始できます。

## ⚡ 最速セットアップ（5分）

### 1. GitHubリポジトリ作成（1分）
1. [GitHub](https://github.com/)にログイン
2. 「New repository」をクリック
3. リポジトリ名を入力（例: `ai-blog`）
4. 「Public」を選択
5. 「Create repository」をクリック

### 2. ファイルアップロード（2分）
1. ZIPファイルを解凍
2. 全ファイルをGitHubリポジトリにドラッグ&ドロップ
3. 「Commit changes」をクリック

### 3. GitHub Pages設定（1分）
1. リポジトリの「Settings」→「Pages」
2. 「Source」を「GitHub Actions」に設定
3. 「Save」をクリック

### 4. 初回実行（1分）
1. 「Actions」タブをクリック
2. 「Run workflow」をクリック
3. 実行完了を待つ

### 5. サイト確認
以下のURLでブログを確認：
```
https://<your-github-username>.github.io/<repository-name>/
```

## 🎯 基本設定のカスタマイズ

### サイト情報の変更
`_config.yml`を編集：
```yaml
title: "あなたのブログタイトル"
description: "ブログの説明"
author: "あなたの名前"
```

### 記事生成頻度の変更
`.github/workflows/ai-article-pipeline.yml`の`cron`を編集：
```yaml
# 毎日9時
- cron: '0 9 * * *'

# 毎週月曜9時（デフォルト）
- cron: '0 9 * * 1'
```

## 🌐 カスタムドメイン設定（オプション）

### InfinityFreeでの設定
1. サブドメイン作成（例: `ai.yourdomain.com`）
2. CNAMEレコード設定:
   - Name: `ai`
   - Value: `<your-github-username>.github.io`

### GitHub Pagesでの設定
1. 「Settings」→「Pages」
2. 「Custom domain」に設定
3. 「Enforce HTTPS」をチェック

## 📊 運用開始

設定完了後、以下が自動実行されます：

✅ **定期記事生成**: 設定したスケジュールで自動実行  
✅ **最新情報取得**: Gemini CLI /Searchで最新動向を調査  
✅ **文章校正**: textlintで自然な日本語に修正  
✅ **自動公開**: GitHub Pagesに即座に公開  

## 🔧 よくある質問

**Q: 費用はかかりますか？**  
A: 完全無料です。全てのツールが無料で利用できます。

**Q: 記事の品質は？**  
A: Gemini CLIとtextlintにより、高品質で自然な記事を生成します。

**Q: カスタマイズできますか？**  
A: はい。デザイン、記事テーマ、頻度など全てカスタマイズ可能です。

**Q: サポートはありますか？**  
A: GitHubのIssuesでサポートを提供しています。

## 📚 詳細情報

- 詳細セットアップ: `docs/SETUP_GUIDE.md`
- トラブルシューティング: `README.md`
- カスタマイズ方法: `docs/SETUP_GUIDE.md`

---

**🎉 おめでとうございます！**  
あなたのAI記事自動生成ブログが完成しました。定期的に最新のAI技術記事が自動で公開されます。

