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

## Date Reference (Known Corrections)

- 東大XRセンターアドバイザー: **2019年**（2017年ではない）
- 松田優作デジタルヒューマン開発: **2021-2022年**（CM放映・受賞は2024年）
