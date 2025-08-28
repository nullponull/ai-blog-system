#!/bin/bash
# Here-string方式のテスト

# テスト用のトピックデータ
TOPICS="1. OpenAI GPT-5の商用展開と新機能の発表
2. Google Gemini 2.0の企業向けAPI拡充
3. Microsoft Copilot for Business 365の導入拡大
4. Anthropic Claude 3.5の推論能力向上アップデート  
5. Meta LLaMAの最新モデルとオープンソース戦略"

echo "=== Here-string方式テスト ==="
echo "Topics:"
printf '%s\n' "$TOPICS"
echo ""

TOPIC_INDEX=1
GENERATED_COUNT=0

set +e
export LC_ALL=C

echo "🔍 Debug: Total topics found: $(echo "$TOPICS" | wc -l)"
echo "🔍 Debug: Starting loop with TOPIC_INDEX=$TOPIC_INDEX, GENERATED_COUNT=$GENERATED_COUNT"
echo ""

while IFS= read -r TOPIC_LINE; do
  if [ -z "$TOPIC_LINE" ]; then
    continue
  fi
  
  echo "🔍 Debug: Processing topic $TOPIC_INDEX: '$TOPIC_LINE'"
  
  TOPIC=$(printf '%s\n' "$TOPIC_LINE" | sed 's/^[0-9]*\. *//')
  echo "🔍 Debug: Extracted topic: '$TOPIC'"
  echo "📝 Generating article $TOPIC_INDEX: $TOPIC"
  
  GENERATED_COUNT=$((GENERATED_COUNT + 1))
  TOPIC_INDEX=$((TOPIC_INDEX + 1))
  echo "🔍 Debug: Completed topic $((TOPIC_INDEX - 1)), moving to next..."
  echo ""
done <<< "$TOPICS"  # Here-string使用

set -e

echo "🔍 Debug: Loop completed with TOPIC_INDEX=$TOPIC_INDEX, GENERATED_COUNT=$GENERATED_COUNT"
echo "📊 Generated $GENERATED_COUNT articles"

echo ""
echo "=== Here-string方式テスト完了 ==="