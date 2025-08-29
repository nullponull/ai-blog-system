#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import json
import re
import glob
import base64
from datetime import datetime
from PIL import Image
import io

def analyze_article_for_mermaid_diagrams(article_content, article_title):
    """記事内容を分析してMermaid図解が必要な箇所を特定し、Mermaid記法を生成"""
    
    # Gemini CLIでMermaid図解を生成
    prompt = f"記事タイトル: {article_title}\n\n"
    prompt += f"記事内容:\n{article_content[:2000]}\n\n"
    prompt += "この記事の内容を理解しやすくするための**視覚的に魅力的で詳細な**Mermaid図解を生成してください。\n\n"
    prompt += "以下の形式で出力してください：\n"
    prompt += "1. 図解タイトル: [図解の名前]\n"
    prompt += "   タイプ: [flowchart/sequenceDiagram/classDiagram/gitgraph など]\n"
    prompt += "   Mermaid記法:\n"
    prompt += "   ```mermaid\n"
    prompt += "   [実際のmermaid記法]\n"
    prompt += "   ```\n\n"
    prompt += "2. 図解タイトル: [次の図解の名前]\n"
    prompt += "   ...\n\n"
    prompt += "**重要な要求事項:**\n"
    prompt += "- **最大2個まで**（品質重視）\n"
    prompt += "- **リッチで詳細な図解**: 分岐、条件分岐を含む\n"
    prompt += "- **色分けとスタイリング**: style文で色彩豊かに\n"
    prompt += "- **アイコンと記号**: 矢印の種類、ノード形状を多様化\n"
    prompt += "- **日本語ラベル**: 分かりやすい説明文\n"
    prompt += "- **実用的で美しい**: プレゼンテーション品質\n\n"
    prompt += "**制限事項:**\n"
    prompt += "- subgraph は使用しない（互換性の問題）\n"
    prompt += "- &演算子は使用しない\n"
    prompt += "- font-weight, linkStyle は使用しない\n"
    prompt += "- style文はfill, strokeのみ（stroke-width不可）\n"
    prompt += "- 日本語テキストは短く簡潔に\n\n"
    prompt += "**推奨パターン:**\n"
    prompt += "- 多様なノード形状: [], {}, (), (())\n"
    prompt += "- 条件分岐とラベル付き矢印: A -- ラベル --> B\n"
    prompt += "- 色分けで視覚的に美しく: style A fill:#color,stroke:#color\n"
    prompt += "- セミコロンは使用しない（互換性向上）\n"
    
    try:
        print("🤖 Generating Mermaid diagrams with Gemini CLI...")
        
        import subprocess
        
        # gemini CLIを実行（プロンプトをstdinで渡す）
        result = subprocess.run([
            'gemini', '-m', 'gemini-2.5-flash'
        ], input=prompt, capture_output=True, text=True, timeout=60, encoding='utf-8')
        
        if result.returncode == 0:
            content = result.stdout
            
            # Mermaid記法を抽出
            diagrams = parse_mermaid_response(content)
            print(f"✅ Generated {len(diagrams)} Mermaid diagrams")
            return diagrams
            
        else:
            print(f"❌ Gemini CLI failed: {result.stderr}")
            return []
            
    except Exception as e:
        print(f"❌ Error generating Mermaid diagrams: {str(e)}")
        return []

def parse_mermaid_response(content):
    """GeminiのレスポンスからMermaid図解を抽出"""
    
    diagrams = []
    
    # 図解タイトルとMermaid記法を抽出
    pattern = r'図解タイトル:\s*([^\n]+).*?タイプ:\s*([^\n]+).*?```mermaid\s*(.*?)\s*```'
    matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
    
    for i, (title, diagram_type, mermaid_code) in enumerate(matches):
        diagrams.append({
            'title': title.strip(),
            'type': diagram_type.strip(),
            'mermaid_code': mermaid_code.strip(),
            'index': i + 1
        })
    
    return diagrams

def mermaid_to_image(mermaid_code, output_path):
    """Mermaid記法を画像に変換"""
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Mermaid Ink API を使用してPNG画像を生成
        # https://mermaid.ink/ のサービスを利用
        
        encoded_mermaid = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        mermaid_url = f"https://mermaid.ink/img/{encoded_mermaid}"
        
        print(f"🖼️ Converting Mermaid to image: {os.path.basename(output_path)}")
        print(f"🔍 Mermaid code preview: {mermaid_code[:80]}...")
        print(f"📏 URL length: {len(mermaid_url)} chars")
        
        # デバッグ: 完全なMermaid記法を保存
        debug_path = output_path.replace('.jpg', '_debug.txt')
        with open(debug_path, 'w', encoding='utf-8') as f:
            f.write(f"Mermaid Code ({len(mermaid_code)} chars):\n")
            f.write(mermaid_code)
            f.write(f"\n\nURL ({len(mermaid_url)} chars):\n")
            f.write(mermaid_url)
        print(f"📝 Full Mermaid code saved: {debug_path}")
        
        # Check if URL is too long (URLs over ~2000 chars might fail)
        if len(mermaid_url) > 2000:
            print(f"⚠️ URL too long ({len(mermaid_url)} chars), simplifying diagram...")
            # Create a simplified version
            lines = mermaid_code.split('\n')
            simplified_lines = []
            for line in lines:
                # Skip style lines if too long
                if 'style' in line and len('\n'.join(simplified_lines + [line])) > 1000:
                    continue
                simplified_lines.append(line)
            
            simplified_code = '\n'.join(simplified_lines)
            encoded_mermaid = base64.b64encode(simplified_code.encode('utf-8')).decode('utf-8')
            mermaid_url = f"https://mermaid.ink/img/{encoded_mermaid}"
            print(f"📏 Simplified URL length: {len(mermaid_url)} chars")
        
        response = requests.get(mermaid_url, timeout=30)
        print(f"🌐 API response: {response.status_code}")
        
        if response.status_code == 200:
            # PNG画像を取得してJPEGに変換
            image = Image.open(io.BytesIO(response.content))
            
            # 背景を白にしてRGB変換
            if image.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # JPEG形式で保存
            image.save(output_path, 'JPEG', quality=85, optimize=True)
            
            print(f"✅ Mermaid image saved: {os.path.basename(output_path)}")
            return True
        else:
            print(f"❌ Mermaid.ink API failed: {response.status_code}")
            if response.status_code == 404:
                print("💡 This might be due to complex syntax or special characters")
            return False
            
    except Exception as e:
        print(f"❌ Error converting Mermaid to image: {str(e)}")
        return False

def add_diagrams_to_article(article_path, diagrams):
    """記事にMermaid図解を追加"""
    
    try:
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 記事の最後に図解セクションを追加
        diagram_section = "\n\n## 図解\n\n"
        for diagram in diagrams:
            diagram_section += f"### {diagram['title']}\n\n"
            diagram_section += f"![{diagram['title']}]({diagram['path']})\n\n"
        
        # 記事に図解セクションを追加
        content += diagram_section
        
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ Added {len(diagrams)} diagrams to article")
        
    except Exception as e:
        print(f"⚠️ Could not add diagrams to article: {str(e)}")

def process_article_mermaid_diagrams(article_path):
    """記事のMermaid図解を処理"""
    
    try:
        # 記事を読み込み
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # タイトルを抽出
        title_match = re.search(r'title:\s*["\']([^"\']+)["\']', content)
        if not title_match:
            print(f"⚠️ No title found in {article_path}")
            return []
        
        article_title = title_match.group(1)
        
        # 記事内容を抽出（Markdown部分のみ）
        content_match = re.search(r'---\s*$(.+)', content, re.MULTILINE | re.DOTALL)
        article_content = content_match.group(1) if content_match else content
        
        # Mermaid図解を生成
        mermaid_diagrams = analyze_article_for_mermaid_diagrams(article_content, article_title)
        
        if not mermaid_diagrams:
            print(f"ℹ️ No Mermaid diagrams needed for: {article_title}")
            return []
        
        generated_diagrams = []
        base_filename = os.path.basename(article_path).replace('.md', '')
        
        for diagram in mermaid_diagrams:
            # Mermaid画像のパス
            mermaid_filename = f"{base_filename}-mermaid-{diagram['index']}.jpg"
            mermaid_path = f"assets/images/posts/{mermaid_filename}"
            
            # Mermaidを画像に変換
            if mermaid_to_image(diagram['mermaid_code'], mermaid_path):
                generated_diagrams.append({
                    'path': f"/assets/images/posts/{mermaid_filename}",
                    'title': diagram['title'],
                    'type': diagram['type'],
                    'mermaid_code': diagram['mermaid_code']
                })
        
        return generated_diagrams
        
    except Exception as e:
        print(f"❌ Error processing Mermaid diagrams: {str(e)}")
        return []

def main():
    """メイン処理"""
    
    # 今日の記事を取得
    today = datetime.now().strftime("%Y-%m-%d")
    article_pattern = f"_posts/{today}-*.md"
    articles = glob.glob(article_pattern)
    
    if not articles:
        print("ℹ️ No articles found for today")
        return
    
    print(f"📊 Found {len(articles)} articles to process for Mermaid diagrams")
    
    total_diagrams = 0
    for article_path in articles:
        print(f"\n📄 Processing: {os.path.basename(article_path)}")
        diagrams = process_article_mermaid_diagrams(article_path)
        total_diagrams += len(diagrams)
        
        if diagrams:
            print(f"✅ Generated {len(diagrams)} Mermaid diagrams")
            for diagram in diagrams:
                print(f"  - {diagram['title']} ({diagram['type']})")
            
            # 記事に図解を追加
            add_diagrams_to_article(article_path, diagrams)
    
    print(f"\n📊 Generated {total_diagrams} Mermaid diagrams total")

if __name__ == "__main__":
    main()