#!/bin/bash
# ローカルでループ処理をテストするスクリプト

# テスト用のトピックデータ（実際のGitHub Actionsで生成されるような形式）
TOPICS="1. OpenAI GPT-5の商用展開と新機能の発表
2. Google Gemini 2.0の企業向けAPI拡充
3. Microsoft Copilot for Business 365の導入拡大
4. Anthropic Claude 3.5の推論能力向上アップデート  
5. Meta LLaMAの最新モデルとオープンソース戦略
6. NVIDIA H200 GPUによるAI計算処理の高速化
7. 生成AI規制法案の世界的な動向と企業への影響
8. AI画像生成技術の著作権問題と解決策の模索
9. 自動運転AIの商用化に向けた最新技術動向
10. 医療診断AIの精度向上と規制当局の対応"

echo "=== GitHub Actions ループ処理テスト ==="
echo "Topics to process:"
printf '%s\n' "$TOPICS"
echo ""

# 実際のGitHub Actionsと同じ処理
TOPIC_INDEX=1
GENERATED_COUNT=0

set +e  # Continue on errors
export LC_ALL=C  # Set locale to avoid encoding issues

# デバッグ情報追加
echo "🔍 Debug: Total topics found: $(echo "$TOPICS" | wc -l)"
echo "🔍 Debug: Topics content:"
printf '%s\n' "$TOPICS" | nl
echo "🔍 Debug: Starting loop with TOPIC_INDEX=$TOPIC_INDEX, GENERATED_COUNT=$GENERATED_COUNT"
echo ""

while IFS= read -r TOPIC_LINE; do
  if [ -z "$TOPIC_LINE" ]; then
    continue
  fi
  
  echo "🔍 Debug: Processing topic $TOPIC_INDEX: '$TOPIC_LINE'"
  
  # より安全なsed処理
  TOPIC=$(printf '%s\n' "$TOPIC_LINE" | sed 's/^[0-9]*\. *//')
  echo "🔍 Debug: Extracted topic: '$TOPIC'"
  echo "📝 Generating article $TOPIC_INDEX: $TOPIC"
  
  # Category determination (case文に変更)
  CATEGORY="最新動向"
  case "$TOPIC" in
      *研究*|*論文*|*学会*) CATEGORY="研究論文" ;;
      *技術*|*アルゴリズム*|*仕組み*) CATEGORY="技術解説" ;;
      *導入*|*事例*|*活用*) CATEGORY="実装事例" ;;
      *市場*|*分析*|*予測*) CATEGORY="業界分析" ;;
  esac
  
  echo "📂 Category: $CATEGORY"
  
  # Gemini API呼び出しの代わりにダミーファイル作成
  echo "# $TOPIC

この記事は「$TOPIC」について解説します。

## 概要と背景
テスト用の記事コンテンツです。

## 詳細な技術・ビジネス内容  
具体的な内容がここに入ります。

## 市場・競合への影響
市場への影響分析がここに入ります。

## 今後の展望
将来の展望がここに入ります。
" > "_temp/article-${TOPIC_INDEX}.md"
  
  if [ -s "_temp/article-${TOPIC_INDEX}.md" ]; then
    # より安全な文字列処理
    TITLE=$(printf '%s' "$TOPIC" | head -c 80)
    SLUG=$(printf '%s' "$TOPIC" | tr '[:upper:]' '[:lower:]' | tr -cd '[:alnum:]-' | sed 's/--*/-/g' | sed 's/^-\|-$//g' | head -c 50)
    FILENAME="$(date +%Y-%m-%d)-${TOPIC_INDEX}-${SLUG}.md"
    
    echo "📄 Generated filename: $FILENAME"
    
    # Store in temp for processing using printf
    printf '%s\n' "---" "layout: post" "title: \"$TITLE\"" "date: $(date +%Y-%m-%d\ %H:%M:%S\ %z)" "categories: [\"$CATEGORY\"]" "tags: [\"AI\", \"最新ニュース\", \"技術動向\"]" "author: \"AI記事生成システム\"" "excerpt: \"AI業界の最新動向について詳しく解説します。\"" "reading_time: 8" "---" > "_temp/temp-${FILENAME}"
    
    # より安全なファイル処理
    tail -n +2 "_temp/article-${TOPIC_INDEX}.md" | sed '/^```markdown$/d' | sed '/^```$/d' >> "_temp/temp-${FILENAME}"
    
    echo "✅ Generated: temp-${FILENAME}"
    GENERATED_COUNT=$((GENERATED_COUNT + 1))
  else
    echo "❌ Failed to generate: $TOPIC"
  fi
  
  TOPIC_INDEX=$((TOPIC_INDEX + 1))
  echo "🔍 Debug: Completed topic $((TOPIC_INDEX - 1)), moving to next..."
  echo ""
done < <(printf '%s\n' "$TOPICS")  # プロセス置換を使用してサブシェル問題を解決

set -e  # Re-enable exit on error

echo "🔍 Debug: Loop completed with TOPIC_INDEX=$TOPIC_INDEX, GENERATED_COUNT=$GENERATED_COUNT"
echo "📊 Generated $GENERATED_COUNT articles"

echo ""
echo "=== 結果確認 ==="
echo "Generated files in _temp/:"
ls -la _temp/temp-*.md 2>/dev/null || echo "No temp files found"

echo ""
echo "=== テスト完了 ==="