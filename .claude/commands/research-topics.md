# AIコンパス事前リサーチ

AIコンパスの記事生成前に、Agent Teamsで事前リサーチを実行する。
WebSearch/WebFetch（無料）で最新データを収集し、構造化YAMLとしてナレッジベースに注入する。

## 実行手順

### 1. トピック決定

$ARGUMENTS が指定されている場合はそれをトピックとして使用。
指定がない場合は、翌日分のカテゴリローテーション（article_pipeline.pyのDAY_CATEGORY_MAP）から3トピックを自動選択。

トピック例:
- "OpenAI GPT-5のエンタープライズ影響"
- "NVIDIA Blackwell B300とAI推論コスト"
- "日本企業のAIエージェント導入動向"

### 2. チーム作成・リサーチ実行

TeamCreateで「blog-research」チームを作成し、トピックごとにResearch Agent（blog-researcher）を並列起動する。

各Research Agentには以下の情報を渡す:
- topic: トピック名
- category: カテゴリ（AI最新ニュース、AI技術ガイド等）
- target_companies: 関連企業（2-4社）
- angle: 執筆角度
- output_path: `_data/research/{date}-{slug}.yml`

### 3. ファクトチェック

全Research Agent完了後、Verify Agent（fact-checker）を起動。
`_data/research/` 内の当日分YAMLを読み込み、クロスチェック実行。

### 4. KB更新

```bash
python3 scripts/apply_research_to_kb.py
```
リサーチ結果のkb_updatesセクションを_data/market/*.ymlに差分適用。

### 5. 完了報告

- 収集したファクト数
- 検証済みデータ数
- KB更新件数
- 次回の記事生成で利用可能なリサーチファイル一覧

## 出力先

- リサーチデータ: `_data/research/{YYYY-MM-DD}-{slug}.yml`
- KB更新: `_data/market/*.yml`（差分更新）

## 注意

- Gemini APIは使用しない（WebSearch/WebFetchのみ）
- リサーチデータは7日間有効（article_pipeline.pyが自動で期限切れを無視）
- 既存のナレッジベースと重複するデータは収集しない
