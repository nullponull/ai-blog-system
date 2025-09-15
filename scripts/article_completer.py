#!/usr/bin/env python3
"""
不完全な記事を自動補完する機能
"""

import os
import re
import sys
import json
import requests
from pathlib import Path
from datetime import datetime

def call_gemini_api(prompt, api_key, max_retries=3):
    """
    Gemini APIを呼び出して記事の続きを生成
    """
    if not api_key:
        print("❌ GEMINI_API_KEY が設定されていません")
        return None
    
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    headers = {
        'Content-Type': 'application/json',
        'X-goog-api-key': api_key
    }
    
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "topP": 0.9,
            "topK": 40,
            "maxOutputTokens": 4096,
        }
    }
    
    for attempt in range(max_retries):
        try:
            print(f"📡 API呼び出し試行 {attempt + 1}/{max_retries}")
            response = requests.post(url, headers=headers, json=data, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0]['content']['parts'][0]['text']
                return content.strip()
            else:
                print(f"⚠️ 試行 {attempt + 1}: レスポンスに候補が含まれていません")
                
        except requests.exceptions.Timeout:
            print(f"⏰ 試行 {attempt + 1}: タイムアウトが発生")
            if attempt < max_retries - 1:
                print("🔄 30秒後に再試行...")
                import time
                time.sleep(30)
        except requests.exceptions.RequestException as e:
            print(f"❌ 試行 {attempt + 1}: API呼び出しエラー: {e}")
            if attempt < max_retries - 1:
                print("🔄 15秒後に再試行...")
                import time
                time.sleep(15)
        except Exception as e:
            print(f"💀 試行 {attempt + 1}: 予期しないエラー: {e}")
            if attempt < max_retries - 1:
                import time
                time.sleep(10)
    
    return None

def complete_article(article_path, api_key):
    """
    指定された記事を補完する
    """
    print(f"📝 記事を補完中: {article_path}")
    
    try:
        # 元の記事を読み込み
        with open(article_path, 'r', encoding='utf-8') as f:
            original_content = f.read()
        
        # フロントマターと本文を分離
        parts = original_content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = f"---{parts[1]}---"
            article_body = parts[2]
        else:
            print("❌ フロントマターが見つかりません")
            return False
        
        # タイトルを抽出
        title_match = re.search(r'title:\s*["\']?([^"\']+)["\']?', parts[1])
        title = title_match.group(1) if title_match else "AI記事"
        
        # 補完用プロンプトを生成
        words = article_body.strip().split()
        context_words = words[-300:] if len(words) > 300 else words
        context = ' '.join(context_words)
        
        prompt = f"""以下の記事「{title}」が途中で終わっています。この記事の続きを自然に書いて完成させてください。

【既存の記事の最後の部分】
{context}

【要求事項】
1. 上記の文章から自然に続くように記事を完成させる
2. 記事全体で3000-4000文字程度になるよう、適切な長さで補完
3. 日本語として自然な文章で書く
4. AIらしい機械的な表現は避ける（「結論として」「要約すると」等の定型文は避ける）
5. 投資家・技術者にとって有用な情報を含める
6. 最後に適切な結論で締めくくる
7. 記事の末尾に ---END--- を必ず追加する

【文体の指示】
- 親しみやすく専門的な語りかけスタイル
- 業界の先輩が後輩にアドバイスするような温かみ
- 「あなたも感じているかもしれませんが」「正直なところ」「個人的には」等の表現を使用
- 短文と長文のリズムを意識

【注意】
- フロントマターは追加しない（本文のみ）
- 既存の内容を繰り返さない
- 自然な流れで続きを書く
- 記事の途切れた部分から滑らかに継続する

続きを書いてください："""
        
        # API呼び出し
        completion = call_gemini_api(prompt, api_key)
        if not completion:
            print("❌ 記事の補完に失敗しました")
            return False
        
        # ---END---マーカーを確認・追加
        if '---END---' not in completion:
            completion += '\n\n---END---'
        
        # 元の記事と補完部分を結合
        completed_content = frontmatter + '\n\n' + article_body.strip() + '\n\n' + completion
        
        # バックアップ作成をスキップ（不要）
        # backup_path = article_path + '.backup'
        # with open(backup_path, 'w', encoding='utf-8') as f:
        #     f.write(original_content)
        print(f"💾 バックアップ作成: {backup_path}")
        
        # 補完した記事を保存
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(completed_content)
        
        print(f"✅ 記事の補完完了: {article_path}")
        
        # 統計情報を表示
        original_chars = len(original_content)
        completed_chars = len(completed_content)
        added_chars = completed_chars - original_chars
        
        print(f"📊 統計:")
        print(f"   元の文字数: {original_chars}")
        print(f"   補完後文字数: {completed_chars}")
        print(f"   追加文字数: {added_chars}")
        
        return True
        
    except Exception as e:
        print(f"💀 記事補完エラー: {e}")
        return False

def main():
    """メイン処理"""
    # 環境変数からAPIキーを取得
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("❌ 環境変数 GEMINI_API_KEY が設定されていません")
        sys.exit(1)
    
    # 不完全な記事のリストを読み込み
    incomplete_list_path = '_temp/incomplete_articles.txt'
    if not os.path.exists(incomplete_list_path):
        print("❌ 不完全な記事のリストが見つかりません")
        print("まず article_completion_checker.py を実行してください")
        sys.exit(1)
    
    with open(incomplete_list_path, 'r', encoding='utf-8') as f:
        incomplete_articles = [line.strip() for line in f if line.strip()]
    
    if not incomplete_articles:
        print("✅ 補完対象の記事がありません")
        return
    
    print(f"🚀 {len(incomplete_articles)}個の記事を補完開始")
    
    success_count = 0
    fail_count = 0
    
    for filename in incomplete_articles:
        article_path = os.path.join('_posts', filename)
        
        if not os.path.exists(article_path):
            print(f"⚠️ ファイルが見つかりません: {article_path}")
            fail_count += 1
            continue
        
        print(f"\n{'='*50}")
        if complete_article(article_path, api_key):
            success_count += 1
        else:
            fail_count += 1
        
        # API制限を考慮して少し待機
        if success_count + fail_count < len(incomplete_articles):
            print("⏳ API制限を考慮して20秒待機...")
            import time
            time.sleep(20)
    
    print(f"\n📊 補完結果:")
    print(f"   ✅ 成功: {success_count}個")
    print(f"   ❌ 失敗: {fail_count}個")
    
    if success_count > 0:
        print(f"\n🎉 {success_count}個の記事の補完が完了しました！")

if __name__ == "__main__":
    main()