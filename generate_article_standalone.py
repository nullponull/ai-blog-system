import requests
import json
import os
from datetime import datetime
from bs4 import BeautifulSoup
import urllib.parse
import time

def generate_ai_news():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: GEMINI_API_KEY not found")
        return None
    
    today = datetime.now()
    date_str = today.strftime('%Y年%m月%d日')
    
    # Prompt for AI news generation
    prompt = f"""今日({date_str})のAI業界で重要なニュースを想定して、技術者向けのニュース記事を日本語で作成してください。

要件：
- 実際のニュースらしい具体的で詳細な内容
- 企業動向、研究成果、新サービス、規制動向など多様なトピック
- 自然な日本語表現（AI特有の機械的表現は避ける）
- 3000-4000文字程度
- Markdown形式で出力（ただし```markdownなどのコードブロック記号は使わない）

構成例：
# {date_str}のAI業界ニュース

## 企業・市場の動き
### [具体的な企業名と発表内容]

## 研究開発の進展  
### [大学・研究機関の具体的な成果]

## 新サービス・製品の発表
### [実際のサービス名と機能]

## 市場動向と投資の状況
### [投資額や市場予測の具体的データ]

## 規制・ガイドラインの動き
### [政府・規制機関の動向]

## 今後の業界動向

技術的な詳細、具体的な数値、企業名、人名などを含めて、リアルなニュース記事として作成してください。"""

    # Call Gemini API
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent"
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
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        if 'candidates' in result and len(result['candidates']) > 0:
            content = result['candidates'][0]['content']['parts'][0]['text']
            return content
        else:
            print("Error: No content generated")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return None
    except Exception as e:
        print(f"Error processing response: {e}")
        return None

# Generate article
article_content = generate_ai_news()

if article_content:
    # Write the article to file
    with open('_temp/new-article.md', 'w', encoding='utf-8') as f:
        f.write(article_content)
    print("AI news article generated successfully!")
else:
    # Fallback to demo content
    today = datetime.now()
    date_str = today.strftime('%Y年%m月%d日')
    
    fallback_article = f"""# {date_str}のAI業界ニュース - システムメンテナンス中

## お知らせ

現在、AIニュース生成システムがメンテナンス中のため、一時的にサンプル記事を表示しています。

通常運用では、毎日朝9時に以下の内容で最新のAI業界ニュースをお届けしています：

- 企業・市場の最新動向
- 研究開発の新たな進展  
- 新サービス・製品の発表情報
- 投資状況と市場予測
- 規制・ガイドラインの更新
- 業界イベント・注目ポイント

システム復旧まで今しばらくお待ちください。

ご質問やご要望は[こちらのお問い合わせフォーム](https://allforces.wuaze.com/contact)からお知らせください。
"""
    
    with open('_temp/new-article.md', 'w', encoding='utf-8') as f:
        f.write(fallback_article)
    print("Fallback article generated due to API error")