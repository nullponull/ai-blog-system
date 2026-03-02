# セキュリティポリシー

このドキュメントは、AI Blog System プロジェクトのセキュリティ脆弱性を報告するためのポリシーを定めています。

## 脆弱性報告プロセス

### 報告方法

セキュリティ脆弱性を発見した場合、**GitHub Security Advisory** を使用して機密性を保ちながら報告してください：

1. **GitHub Security Advisory を開く**
   - Repository → Security → Advisories → Report a vulnerability
   - または: https://github.com/nullponull/ai-blog-system/security/advisories/new

2. **脆弱性の詳細を記入**
   - タイトル: 簡潔な脆弱性説明
   - 説明: 影響範囲、再現方法、修正案
   - パッケージ/コンポーネント: 対象ファイル/パッケージ
   - 重大度: Critical / High / Moderate / Low

3. **プライベート通知**
   - GitHub が自動的にメンテナーに通知します
   - 公開前に修正期間を設定できます

### 報告対象

- 🚨 **Critical**: リモートコード実行、認証回避、データ流出
- 🔴 **High**: APIキー漏洩、SQLインジェクション、XSS
- 🟡 **Moderate**: 情報開示、認可問題、DoS
- 🟢 **Low**: バージョン情報露出、軽微なバグ

### 報告対象外

以下は GitHub Issues で公開報告してください：
- ドキュメントの誤り
- リンク切れ
- 機能リクエスト
- 既知の制限事項

## セキュリティベストプラクティス

### コード開発時

✅ **すべき:**
- `.env` ファイルで環境変数を管理
- GitHub Secrets で API キーを保管
- 入力値を検証・サニタイズ
- 定期的に依存パッケージを更新
- コードレビューで機密情報チェック

❌ **してはいけない:**
- ソースコード内に API キー、トークン、パスワードを埋め込む
- 個人情報（メールアドレス、電話番号）をコミット
- 秘密鍵（SSH、PEM）をリポジトリに追加
- `git add -A` で `.env` ファイルを追加

### リポジトリ管理

✅ **有効化推奨:**
- Dependabot alerts (Settings → Code security and analysis)
- Secret scanning (Settings → Code security and analysis)
- Branch protection rules (Settings → Branches)
  - Require pull request reviews
  - Require status checks to pass
  - Require branches to be up to date
- Signed commits (設定 → Developer settings → GPG keys)

### 依存パッケージのセキュリティ

```bash
# 定期的に実行
npm audit
pip check
gem audit

# 脆弱性があれば更新
npm update
pip install --upgrade <package>
```

## セキュリティインシデント対応

### キー流出時の対応手順

1. **直ちにキーを無効化**
   - Google Cloud Console → APIs & Services → Credentials
   - 該当キーを削除

2. **Git 履歴から削除**
   ```bash
   git filter-branch --tree-filter 'rm -rf <exposed_files>' --prune-empty -f
   git push origin main --force
   ```

3. **新規キーを生成**
   - Google Cloud Console でリストリクション設定（Gemini API のみ）

4. **GitHub Secrets を更新**
   - Settings → Secrets and variables → Actions
   - 新規キーで置き換え

5. **監視とログ確認**
   - API 利用状況を確認
   - 異常なアクセスがないか確認

## セキュリティアップデート対応時間目標

| 重大度 | 対応時間 | 更新時間 |
|--------|---------|---------|
| Critical | 24時間以内に通知 | 48時間以内に公開 |
| High | 2日以内に通知 | 7日以内に公開 |
| Moderate | 1週間以内に通知 | 30日以内に公開 |
| Low | 30日以内に通知 | 90日以内に公開 |

## 監査ログ

定期的なセキュリティ監査を実施しており、以下をチェックしています：

- ✅ ソースコード内のシークレット情報
- ✅ 依存パッケージの脆弱性
- ✅ Git 履歴のキー流出
- ✅ .env ファイルの使用状況
- ✅ GitHub Secrets の設定

直近監査日: 2026-03-02

## 参考資料

- [GitHub Security Documentation](https://docs.github.com/en/code-security)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Google Cloud Security Best Practices](https://cloud.google.com/security/best-practices)

---

**質問または脆弱性報告**: [Security Advisory](https://github.com/nullponull/ai-blog-system/security/advisories)
