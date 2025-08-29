# 技術仕様書

## システムアーキテクチャ詳細

### ディレクトリ構成

```
ai-blog-system/
├── .github/workflows/
│   └── improved-ai-pipeline.yml    # メインワークフロー
├── _posts/                         # Jekyll記事ディレクトリ
├── assets/images/posts/            # 画像・図解保存先
├── scripts/
│   ├── image_generator.py          # HuggingFace画像生成
│   └── mermaid_diagram_generator.py # Mermaid図解生成
├── docs/                           # ドキュメント
├── .textlintrc.json               # TextLint設定
├── _config.yml                    # Jekyll設定
└── requirements.txt               # Python依存関係
```

### GitHub Actions ワークフロー詳細

#### ジョブ構成
1. **環境セットアップ** (3分)
   - Node.js, Python環境構築
   - 依存関係インストール
   - ディレクトリ作成

2. **話題・記事生成** (4分)
   - Gemini Web Search API呼び出し
   - 話題の重複除去処理
   - 記事生成 (5記事並列処理)

3. **品質改善** (1分)
   - TextLintチェック
   - セマンティック分析
   - AI文章パターン除去

4. **画像・図解生成** (2分)
   - HuggingFace画像生成
   - Mermaid図解生成・埋め込み

5. **サイト構築・デプロイ** (1分)
   - Jekyll ビルド
   - GitHub Pages デプロイ

#### 環境変数

| 変数名 | 用途 | 必須 |
|--------|------|------|
| `GEMINI_API_KEY` | メイン処理用Gemini API | ✅ |
| `HUGGINGFACE_TOKEN` | 画像生成API | ✅ |
| `GITHUB_TOKEN` | GitHubリポジトリアクセス | ✅(自動) |

## API詳細仕様

### Gemini API

#### Web検索プロンプト構造
```
WebSearch: [日付] [話題]。
「[話題]」について、Web検索で最新情報を調査し、
ALLFORCES AI情報メディア向けの専門記事を作成してください。

要件：
- 実際の最新情報に基づく具体的な内容
- 企業名・製品名・人名・数値データを正確に記載
- 技術者・投資家向けの詳細な分析
- 3000-4000文字程度
- Markdown形式で出力

構成：
# [話題]
## 概要と背景
## 詳細な技術・ビジネス内容
## 市場・競合への影響
## 今後の展望

注意事項：
- AIっぽい表現を避け自然で人間的な文章にする
- 過度な敬語や定型的な挨拶文は使わない
- 接続語を多用しない
- 箇条書きの乱用を避ける
- AI生成等のメタ情報は記載しない
- 専門性と信頼性を重視した自然な記事を作成してください
```

#### エラーハンドリング
- **クォータエラー**: 自動フォールバック（Web検索なし）
- **レート制限**: 120秒タイムアウト + 指数バックオフ
- **接続エラー**: 最大3回リトライ

### HuggingFace API

#### 使用モデル
- **メインモデル**: `stabilityai/stable-diffusion-3-medium-diffusers`
- **画像サイズ**: 1024x1024
- **品質**: 高品質設定

#### プロンプト生成
```python
def generate_image_prompt(title, content_preview):
    return f"""A professional, modern illustration representing {title}. 
    Clean, minimalist design with technology themes, 
    suitable for AI industry blog article. 
    High quality, 4K resolution."""
```

## スクリプト詳細

### image_generator.py

#### 主要関数
- `generate_image_for_article(article_path)`: 記事用画像生成
- `extract_title_from_article(content)`: 記事タイトル抽出
- `save_image_with_optimization()`: 画像最適化・保存

#### 画像処理
- **フォーマット**: JPEG (品質85%)
- **最適化**: PIL による自動最適化
- **ファイル名**: `{article-slug}-featured.jpg`

### mermaid_diagram_generator.py

#### Mermaid生成プロセス
1. **記事分析**: 内容から図解が必要な箇所を特定
2. **Mermaid記法生成**: Gemini CLIで詳細な図解を作成
3. **画像変換**: Mermaid.ink APIでPNG→JPEG変換
4. **記事埋め込み**: 「## 図解」セクションとして自動追加

#### 対応図表タイプ
- **フローチャート**: プロセス・手順の可視化
- **概念図**: システム構成・関係性
- **組織図**: 企業・チーム構造
- **データフロー**: 情報の流れ

#### Mermaid構文制限
```javascript
// 対応構文
- graph TD/LR: 基本フローチャート
- subgraph: グループ化 (※Mermaid.ink制限により無効化)
- style: 色分け (fill, stroke のみ)
- 基本ノード形状: [], {}, (), (())

// 非対応構文  
- linkStyle: リンクスタイル
- font-weight: フォントウェイト
- 複雑なノード形状: [/\], [\\/]
```

## 品質管理システム

### TextLint設定詳細

#### @textlint-ja/preset-ai-writing ルール

```json
{
  "no-ai-list-formatting": {
    "allows": ["/重要.*/i", "/注意.*/i"],
    "disableBoldListItems": false
  },
  "no-ai-hype-expressions": {
    "allows": ["/最新の.*/i", "/新しい.*/i"],
    "disableAbsolutenessPatterns": false
  },
  "no-ai-emphasis-patterns": {
    "disableHeadingEmphasisPatterns": true
  }
}
```

#### 自動修正パターン
```bash
# 重複句読点の修正
sed -i 's/、、/、/g' "$article"
sed -i 's/。。/。/g' "$article"

# AIメタデータ除去
sed -i '/^AI によって生成/d' "$article"
sed -i '/^この記事は AI で生成/d' "$article"
sed -i '/^※ この記事は AI/d' "$article"

# 過度な強調の修正
sed -i 's/\*\*\([^*]*\)\*\*/\1/g' "$article"

# リスト形式の最適化
sed -i 's/^- \*\*/- /g' "$article"
```

### セマンティック分析

#### 重複検出アルゴリズム
1. **Sentence-BERT**: 記事の意味ベクトル化
2. **コサイン類似度**: 類似記事の検出 (閾値: 0.8)
3. **品質スコア**: より高品質な記事を優先選択

```python
def calculate_article_quality(content):
    # 長さ、具体性、データ密度を評価
    length_score = min(len(content) / 4000, 1.0)
    data_score = count_specific_data(content) / 10
    structure_score = evaluate_structure(content)
    return (length_score + data_score + structure_score) / 3
```

## パフォーマンス最適化

### 実行時間短縮
- **並列処理**: 記事生成の並列化 (5記事同時処理)
- **タイムアウト**: 各API呼び出し120秒制限
- **キャッシュ**: 重複チェック用の既存記事リスト
- **早期終了**: レート制限検出時の即座停止

### リソース管理
- **メモリ**: Sentence-BERT モデルの効率的な使用
- **ストレージ**: 画像の自動圧縮・最適化
- **ネットワーク**: API呼び出し頻度の制御

## 監視・ログ

### 実行ログ
- **API呼び出し**: レスポンス時間、エラー率
- **記事品質**: TextLint スコア、文字数
- **画像生成**: 成功率、処理時間
- **システム**: 全体実行時間、メモリ使用量

### アラート条件
- **連続失敗**: 3回連続でワークフロー失敗
- **品質低下**: TextLint スコア平均70点以下
- **実行時間**: 15分超過
- **API制限**: レート制限到達

## セキュリティ

### API キー管理
- **GitHub Secrets**: 暗号化されたシークレット管理
- **ローテーション**: 月1回のAPIキー更新推奨
- **アクセス制御**: 最小権限の原則

### データ保護
- **一時ファイル**: 実行後の自動削除
- **ログ**: 個人情報の非出力
- **画像**: 著作権フリー素材の使用

---

**更新日**: 2025-08-29
**バージョン**: v2.1.0