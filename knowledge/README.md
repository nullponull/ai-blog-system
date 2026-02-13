# AIコンパス記事生成ナレッジベース

> 作成日: 2026-02-13
> 用途: article_pipeline.py の記事品質向上・コンプライアンス対応

## 構成

| ディレクトリ | 内容 | ファイル数 |
|---|---|---|
| `compliance/` | コンプライアンス・法律情報 | 5 |
| `tools/` | AIツール最新情報 | 2 |
| `market/` | 市場データ・収入実態 | 3 |
| `competitors/` | 競合分析・信頼できるソース | 2 |

## 使用方法

`scripts/compliance_loader.py` がこのディレクトリのMarkdownを読み込み、記事生成プロンプトに自動注入する。

```python
from compliance_loader import ComplianceLoader

loader = ComplianceLoader()

# コンプライアンスルール
rules = loader.load_compliance_rules()

# 記事プロンプトに注入
context = loader.build_article_context(category="AI技術ガイド")
```

## 更新方法

1. 各Markdownファイルを直接編集
2. `> 最終更新:` の日付を更新
3. `tools/tool_updates_log.md` に変更履歴を記録

## ファイル一覧

### compliance/
- `景品表示法ガイド.md` - 収入表記ルール、打消し表示要件
- `特定商取引法ガイド.md` - 有料記事の表示義務
- `著作権法とAI.md` - AI生成コンテンツの権利
- `ステマ規制ガイド.md` - PR表記義務(2023年10月施行)
- `金融商品取引法ガイド.md` - 投資関連記事の注意点

### tools/
- `tool_database.md` - 全40+ツールの料金・機能・商用利用情報
- `tool_updates_log.md` - 更新履歴

### market/
- `副業収入実態.md` - カテゴリ別の実際の収入データ
- `案件単価相場.md` - クラウドソーシングの単価情報
- `成功パターン分析.md` - 成功事例と失敗パターン

### competitors/
- `信頼できるソース一覧.md` - ファクトチェック用参照先
- `高品質記事パターン.md` - ベストプラクティス
