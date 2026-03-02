# 🧪 Gemini モデル比較テストガイド

複数のモデル（Gemini 2.5, 3.0, Gemma 3 27B）で生成された記事の品質・スタイルを比較するテストです。

## 📋 テスト対象モデル

| モデル | 説明 | 特性 |
|--------|------|------|
| `gemini-2.5-flash-lite` | 軽量版（現在使用中） | 高速・低コスト |
| `gemini-2.5-flash` | 標準版（フォールバック） | バランス型 |
| `gemini-2.0-flash` | 前世代版 | 参考用 |
| `gemini-3.0-flash` | ✨ **新モデル** | 高性能・最新 |
| `gemma-3-27b` | ✨ **OSS モデル** | オープンソース・低制限 |

## 🚀 実行方法

### Step 1: モデル比較テストを実行

```bash
cd /home/sol/ai-blog-system
python3 compare_models.py
```

**実行時間**: 約3-5分（各モデル1回ずつ、レート制限対応）

**出力**:
```
🧪 Gemini モデル比較テスト
...
✅ テスト完了
📄 詳細レポート: output/model_comparison/comparison_report_YYYYMMDD_HHMMSS.md
```

### Step 2: 生成された記事を分析

```bash
python3 analyze_articles_quality.py
```

**分析項目**:
- 📊 記事の文字数・単語数・文数
- ✅ 品質スコア（総合点）
- 🎯 AI臭スコア（低いほど自然）
- 🔍 具体性スコア（企業名・数字の出現）
- 🎭 敬語度（文体の硬さ）

### Step 3: 結果を確認

```bash
ls -lh output/model_comparison/
cat output/model_comparison/comparison_report_*.md
```

## 📊 出力ファイル

```
output/model_comparison/
├── comparison_report_YYYYMMDD_HHMMSS.md  # 比較レポート
└── article_analysis_YYYYMMDD_HHMMSS.json  # 詳細分析（JSON）
```

## 🔍 何を見るべきか

### 1. 生成成功率
- どのモデルが成功したか
- どのモデルがクォータ制限に達したか

### 2. 記事の長さ・ボリューム
```
gemini-2.5-flash-lite: 800字
gemini-2.5-flash:     1200字
gemini-3.0-flash:     1500字
gemma-3-27b:          2000字
```

### 3. AI臭（自然さ）
- スコア: 0-100（高いほど自然）
- `いかがでしたか` などの定型表現が少ないほど良い

### 4. 具体性
- スコア: 0-100（高いほど具体的）
- 企業名や数字が豊富なほど信頼度が高い

### 5. 文体（敬語度）
- スコア: 0-100（中程度が理想）
- 高すぎるとかしこまっている、低いとカジュアル

## ⚡ 予想される結果

| 指標 | gemini-2.5-flash | gemini-3.0-flash | gemma-3-27b |
|------|------------------|------------------|-------------|
| 速度 | ⭐⭐⭐ | ⭐⭐ | ⭐ |
| 自然さ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 具体性 | ⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| ボリューム | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| コスト | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |

## 🛠️ トラブルシューティング

### Q: API key not found エラーが出た
```bash
# .env ファイルを確認
cat /home/sol/daily-note-post/.env | grep GEMINI
```

### Q: QUOTA_LIMIT エラーが出た
- その月のクォータを超過しています
- 別のAPI keyで試す or 翌月を待つ

### Q: モデルが利用不可と出た
- そのモデルはまだアクセス可能になっていません
- Google API コンソールで確認: https://console.cloud.google.com/

### Q: タイムアウトが発生した
- ネットワーク接続を確認
- Google API のステータス確認: https://status.cloud.google.com/

## 📈 結果活用

### パターン A: 高速処理重視
**選択**: `gemini-2.5-flash-lite`
- 既存システムを継続使用

### パターン B: 品質重視
**選択**: `gemini-3.0-flash`
- モデルローテーションに追加
- 記事品質が向上する可能性

### パターン C: 制限なし重視
**選択**: `gemma-3-27b`
- ボリューム大の長編記事に適している
- API制限がほぼないため安定動作

## 📝 テスト結果テンプレート

```markdown
# テスト結果 (YYYY-MM-DD)

## 実行環境
- API Key: GEMINI_API_KEY2
- テスト日時: YYYY-MM-DD HH:MM:SS

## 成功したモデル
- ✅ Model A (品質スコア: XX点)
- ✅ Model B (品質スコア: XX点)

## 失敗したモデル
- ❌ Model C (理由: QUOTA_LIMIT)

## 推奨事項
[分析結果に基づく推奨]
```

## 🔗 参考リンク

- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [Gemma プロジェクト](https://ai.google.dev/gemma)
- [API 料金](https://ai.google.dev/pricing)

---

**最後に**: テスト結果を `comparison_results.md` として保存し、プロジェクトに共有してください！
