#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import re
import subprocess
import requests
import base64
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont
import io

def enhance_article_with_visuals(article_path):
    """記事に図解とタイトル画像を追加して強化"""
    
    try:
        print(f"📄 Processing: {os.path.basename(article_path)}")
        
        # 記事を読み込み
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # タイトルを抽出
        title_match = re.search(r'title:\s*["\']([^"\']+)["\']', content)
        if not title_match:
            print(f"⚠️ No title found in {article_path}")
            return False
        
        article_title = title_match.group(1)
        print(f"📝 Title: {article_title}")
        
        # 記事内容を抽出（Markdown部分のみ）
        content_match = re.search(r'---\s*$(.+)', content, re.MULTILINE | re.DOTALL)
        article_content = content_match.group(1) if content_match else content
        
        # ベースファイル名を取得
        base_filename = os.path.basename(article_path).replace('.md', '')
        
        # 1. タイトル画像を生成
        title_image_path = generate_title_image(article_title, base_filename)
        
        # 2. Mermaid図解を生成
        mermaid_images = generate_mermaid_diagrams(article_content, article_title, base_filename)
        
        # 3. 記事に画像を挿入
        enhanced_content = insert_images_to_article(content, title_image_path, mermaid_images, article_title)
        
        # 記事を更新
        with open(article_path, 'w', encoding='utf-8') as f:
            f.write(enhanced_content)
            
        print(f"✅ Enhanced: {os.path.basename(article_path)}")
        return True
        
    except Exception as e:
        print(f"❌ Error enhancing {article_path}: {str(e)}")
        return False

def generate_title_image(title, base_filename):
    """タイトル画像を生成"""
    
    try:
        # シンプルなタイトル画像を生成
        img_width, img_height = 800, 400
        image = Image.new('RGB', (img_width, img_height), color='#1e3a8a')  # 青色背景
        draw = ImageDraw.Draw(image)
        
        # フォント設定（システムフォントを使用）
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 36)
        except:
            font = ImageFont.load_default()
        
        # タイトルをテキスト描画（簡単な改行処理）
        lines = wrap_text(title, 25)  # 25文字で改行
        y_offset = (img_height - len(lines) * 50) // 2
        
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            x = (img_width - text_width) // 2
            draw.text((x, y_offset), line, fill='white', font=font)
            y_offset += 50
        
        # 画像を保存
        image_path = f"assets/images/posts/{base_filename}-title.jpg"
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        image.save(image_path, 'JPEG', quality=85)
        
        print(f"✅ Title image created: {image_path}")
        return image_path
        
    except Exception as e:
        print(f"⚠️ Title image generation failed: {str(e)}")
        return None

def wrap_text(text, width):
    """テキストを指定幅で改行"""
    words = text.split()
    lines = []
    current_line = ""
    
    for word in words:
        if len(current_line + word) <= width:
            current_line += word + " "
        else:
            if current_line:
                lines.append(current_line.strip())
            current_line = word + " "
    
    if current_line:
        lines.append(current_line.strip())
    
    return lines

def generate_mermaid_diagrams(article_content, article_title, base_filename):
    """記事内容からMermaid図解を生成"""
    
    try:
        print(f"🖼️ Generating Mermaid diagrams...")
        
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
        prompt += "**重要な要求事項:**\n"
        prompt += "- **最大1個まで**（シンプルで短く）\n"
        prompt += "- **超シンプル図解**: 3-4個のノードのみ\n"
        prompt += "- **1-2文字のラベル**: AI, 企業, 規制 など\n"
        prompt += "- **基本的な矢印のみ**: A-->B-->C 形式\n\n"
        prompt += "**厳格な制限事項:**\n"
        prompt += "- 全体で50文字以内のMermaidコード\n"
        prompt += "- style文・色指定・装飾は一切禁止\n"
        prompt += "- ノード名は A,B,C,D のみ使用\n"
        prompt += "- 矢印は --> のみ（他の記号禁止）\n"
        prompt += "例: graph TD; A[AI]-->B[企業]-->C[規制]\n"
        
        # Gemini CLIを実行
        result = subprocess.run([
            'gemini', '-m', 'gemini-2.5-flash', '-p', prompt
        ], capture_output=True, text=True, timeout=60, encoding='utf-8')
        
        if result.returncode == 0:
            content = result.stdout
            
            # Mermaid記法を抽出
            diagrams = parse_mermaid_response(content)
            print(f"✅ Generated {len(diagrams)} Mermaid diagrams")
            
            # 画像に変換
            generated_images = []
            for i, diagram in enumerate(diagrams):
                image_path = f"assets/images/posts/{base_filename}-mermaid-{i+1}.jpg"
                if mermaid_to_image(diagram['mermaid_code'], image_path):
                    generated_images.append({
                        'path': f"/assets/images/posts/{os.path.basename(image_path)}",
                        'title': diagram['title'],
                        'type': diagram['type']
                    })
            
            return generated_images
            
        else:
            print(f"❌ Mermaid generation failed: {result.stderr}")
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
            'mermaid_code': mermaid_code.strip()
        })
    
    return diagrams

def mermaid_to_image(mermaid_code, output_path):
    """Mermaid記法を画像に変換"""
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"🖼️ Converting Mermaid to image: {os.path.basename(output_path)}")
        
        encoded_mermaid = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        mermaid_url = f"https://mermaid.ink/img/{encoded_mermaid}"
        
        if len(mermaid_url) > 2000:  # URL長制限
            print(f"⚠️ Mermaid URL too long, skipping...")
            return False
        
        response = requests.get(mermaid_url, timeout=30)
        
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
            print(f"❌ Mermaid API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error converting Mermaid to image: {str(e)}")
        return False

def insert_images_to_article(content, title_image_path, mermaid_images, article_title):
    """記事に画像を挿入"""
    
    # タイトル画像を最初のセクションの前に挿入
    if title_image_path:
        title_image_md = f"\n![{article_title}](/{title_image_path})\n\n"
        # 最初の ## の前に挿入
        content = re.sub(r'(---\n.*?\n---\n)(.*?)(##)', r'\1\2' + title_image_md + r'\3', content, flags=re.DOTALL)
    
    # Mermaid図解を記事の最後に追加
    if mermaid_images:
        diagram_section = "\n\n## 図解\n\n"
        for diagram in mermaid_images:
            diagram_section += f"### {diagram['title']}\n\n"
            diagram_section += f"![{diagram['title']}]({diagram['path']})\n\n"
        
        content += diagram_section
    
    return content

def main():
    """メイン処理: すべての記事を強化"""
    
    print("🎨 Starting article enhancement with images and diagrams...")
    
    # _postsディレクトリの全記事を取得
    articles = glob.glob("_posts/*.md")
    
    if not articles:
        print("ℹ️ No articles found in _posts directory")
        return
    
    print(f"📊 Found {len(articles)} articles to enhance")
    
    success_count = 0
    for article_path in articles:
        print(f"\n📄 Processing: {os.path.basename(article_path)}")
        if enhance_article_with_visuals(article_path):
            success_count += 1
    
    print(f"\n📊 Enhancement completed: {success_count}/{len(articles)} articles successfully enhanced")

if __name__ == "__main__":
    main()