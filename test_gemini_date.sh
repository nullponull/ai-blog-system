#!/bin/bash
# Gemini API日付指定テスト

echo "=== Gemini API日付指定テスト ==="

# 現在の日付
CURRENT_DATE=$(date '+%Y年%m月%d日')
echo "Current date: $CURRENT_DATE"

# GitHub Actionsと同じプロンプトでテスト
PROMPT="WebSearch: AI業界 最新ニュース トレンド 話題 ${CURRENT_DATE}。AI業界で注目されている最新の話題・トレンドをWeb検索で調査し、以下の形式で10個の具体的な話題をリストアップしてください。各話題は1行で、簡潔に表現してください。例: 1. OpenAIの新モデル発表, 2. Google DeepMindの研究成果, 3. 生成AIの企業導入事例, 4. AI規制法案の動向, 5. 自動運転技術の進展...実際の検索結果に基づいて、具体的な企業名・製品名・人名を含めた現実的な話題を10個リストアップしてください。"

echo ""
echo "Testing Gemini API with date-specific prompt..."
echo "Prompt length: $(echo "$PROMPT" | wc -c) characters"

# API_KEYの確認
if [ -z "$GEMINI_API_KEY" ]; then
  echo "❌ GEMINI_API_KEY is not set - this might be the issue in GitHub Actions"
  echo "Trying without API key (will likely fail):"
fi

# Gemini API呼び出しテスト
echo ""
echo "🎯 Testing Gemini API call..."
if gemini -m "gemini-2.5-flash" --prompt "$PROMPT" > test_output.txt 2>&1; then
  echo "✅ Gemini API call successful"
  echo ""
  echo "Generated content:"
  head -15 test_output.txt
  
  echo ""
  echo "Checking for numbered topics:"
  grep -E "^[0-9]+\." test_output.txt || echo "No numbered topics found"
  
else
  echo "❌ Gemini API call failed"
  echo ""
  echo "Error output:"
  cat test_output.txt
fi

echo ""
echo "=== Alternative: Test without specific date ==="

# 日付なしのプロンプト
PROMPT_NO_DATE="WebSearch: AI業界 最新ニュース トレンド 話題。AI業界で注目されている最新の話題・トレンドをWeb検索で調査し、以下の形式で10個の具体的な話題をリストアップしてください。各話題は1行で、簡潔に表現してください。例: 1. OpenAIの新モデル発表, 2. Google DeepMindの研究成果, 3. 生成AIの企業導入事例, 4. AI規制法案の動向, 5. 自動運転技術の進展...実際の検索結果に基づいて、具体的な企業名・製品名・人名を含めた現実的な話題を10個リストアップしてください。"

echo "Testing without specific date..."
if gemini -m "gemini-2.5-flash" --prompt "$PROMPT_NO_DATE" > test_output_no_date.txt 2>&1; then
  echo "✅ No-date API call successful"
  echo ""
  echo "Generated content:"
  head -15 test_output_no_date.txt
  
  echo ""
  echo "Checking for numbered topics:"
  grep -E "^[0-9]+\." test_output_no_date.txt || echo "No numbered topics found"
  
else
  echo "❌ No-date API call also failed"
  echo ""
  echo "Error output:"
  cat test_output_no_date.txt
fi

echo ""
echo "=== Test Summary ==="
echo "Date-specific test: $([ -f test_output.txt ] && echo "Generated $(wc -l < test_output.txt) lines" || echo "Failed")"
echo "No-date test: $([ -f test_output_no_date.txt ] && echo "Generated $(wc -l < test_output_no_date.txt) lines" || echo "Failed")"