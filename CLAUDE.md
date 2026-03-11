# ai-blog-system - Claude Code Instructions

> **Language**: Japanese (日本語で出力)

## Critical Design Principles

### 「データは真実、出力は秘匿」

AIメディアブログに公開する記事には非公開の固有名詞を含めてはならない。

**秘匿化の適用箇所:**

| ファイル | 適用方法 |
|---------|---------|
| `scripts/article_pipeline.py` | DD SDK の `build_prompt()` 返却値を `_SANITIZER.sanitize()` で秘匿化 |
| `scripts/article_pipeline.py` | レガシーフォールバックの episodes を `_SANITIZER.sanitize()` で秘匿化 |

**ペルソナデータの取得順序:**
```
1. DigitalDouble SDK → OutputSanitizer 適用
2. PersonaController (legacy, x_persona_config.json) → OutputSanitizer 適用
```

### digital-double データ層の実名を書き換えてはならない

秘匿化は `OutputSanitizer`（digital-double/output_sanitizer.py）が出力時に適用する。

## Platform-Specific Rules (ai-blog / ALLFORCES)

| ルール | 内容 |
|-------|------|
| 著者 | **ALLFORCES編集部**（個人は前面に出さない） |
| 一人称 | 「編集部では」「取材によると」（「私が」「僕が」は禁止） |
| 文体 | 専門的・客観的・取材調 |
| ペルソナ | 記者ペルソナ（個人の知見はバックグラウンド知識として活用） |
| 禁止 | 個人名/プロフィールの前面押し出し、「私が」「僕が」 |
| デプロイ | GitHub Pages (Jekyll) + GitHub Actions |

## Key Files

| ファイル | 役割 | 注意 |
|---------|------|------|
| `scripts/article_pipeline.py` | 記事生成パイプライン（6ステージ） | OutputSanitizer統合済み |
| `scripts/title_sanitizer.py` | タイトルのマークダウン/クリックベイト除去 | 出力品質管理 |
| `scripts/compliance_loader.py` | 景表法等コンプライアンスルール注入 | - |
| `scripts/knowledge_base.py` | 市場データ/ベンチマーク読み込み | - |
| `knowledge/compliance/` | 法律ガイド（景表法、著作権法等） | - |

## 6-Stage Pipeline

```
Stage 1: Topic Planning (Gemini flash-lite)
Stage 2: Article Draft (Gemini flash + Web Search) ← ペルソナ注入 + OutputSanitizer
Stage 3: Title Optimization (flash-lite)
Stage 4: Metadata Generation (flash-lite) → author = "ALLFORCES編集部"
Stage 5: Quality Gate (Python scorer)
Stage 6: Post-Processing (textlint, enrich, OGP)
```

## Testing & Verification Workflow

用途別にツールを使い分ける：

| 用途 | ツール | コマンド/使い方 |
|------|--------|----------------|
| **レイアウト・CSS構造** | `site_inspector.py` | `python3 scripts/site_inspector.py URL --mode all` |
| **レンダリング後の構造** | PinchTab (Docker) | `curl localhost:9867/navigate + /snapshot` |
| **DOM定量検証** | Scrapling | `from scrapling import Fetcher; page = Fetcher().get(url)` |
| **機能テスト** | Playwright | ブラウザ操作・フォーム・認証・E2E |
| **Webクロール・企業調査** | Scrapling | アンチbot対応、Spider API |

### PinchTab (Docker)
```bash
# 起動済み: docker run -d --name pinchtab -p 127.0.0.1:9867:9867 -v pinchtab-data:/data --shm-size=2g pinchtab/pinchtab
curl -X POST localhost:9867/navigate -H 'Content-Type: application/json' -d '{"url": "..."}'
curl localhost:9867/snapshot  # アクセシビリティツリー（~800トークン/ページ）
curl localhost:9867/text      # テキスト抽出
```

### site_inspector.py モード
- `--mode structure`: HTML構造ツリー
- `--mode table-check`: テーブルのwrapper有無・列数・内容
- `--mode css-audit`: CSS class使用頻度・タグ統計
- `--mode responsive`: レスポンシブ問題検出
- `--mode all`: 全モード実行

### 原則
- レイアウト修正 → PinchTab/site_inspector/Scraplingで構造検証（スクリーンショット不要、トークン効率10倍）
- 機能実装 → Playwrightで操作テスト
- デプロイ後確認 → PinchTab snapshot + Scrapling DOM検証

## Date Reference (Known Corrections)

- 東大XRセンターアドバイザー: **2019年**（2017年ではない）
- 松田優作デジタルヒューマン開発: **2021-2022年**（CM放映・受賞は2024年）
