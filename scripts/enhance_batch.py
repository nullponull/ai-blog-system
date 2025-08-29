#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import re
from PIL import Image, ImageDraw, ImageFont
import argparse

def generate_title_image_only(title, base_filename):
    """タイトル画像のみを高速生成"""
    
    try:
        # シンプルなタイトル画像を生成
        img_width, img_height = 800, 400
        image = Image.new('RGB', (img_width, img_height), color='#1e3a8a')  # 青色背景
        draw = ImageDraw.Draw(image)
        
        # フォント設定
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

def add_title_image_to_article(article_path):
    """記事にタイトル画像のみを追加"""
    
    try:
        print(f"📄 Processing: {os.path.basename(article_path)}")
        
        # 記事を読み込み（エンコーディングエラー対応）
        try:
            with open(article_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            print(f"⚠️ UTF-8 encoding error, skipping: {os.path.basename(article_path)}")
            return False
        
        # 既にタイトル画像があるかチェック
        if '/assets/images/posts/' in content and '-title.jpg' in content:
            print(f"⚠️ Title image already exists, skipping: {os.path.basename(article_path)}")
            return True
        
        # タイトルを抽出
        title_match = re.search(r'title:\s*["\']([^"\']+)["\']', content)
        if not title_match:
            print(f"⚠️ No title found in {article_path}")
            return False
        
        article_title = title_match.group(1)
        
        # ベースファイル名を取得
        base_filename = os.path.basename(article_path).replace('.md', '')
        
        # タイトル画像を生成
        title_image_path = generate_title_image_only(article_title, base_filename)
        
        if title_image_path:
            # タイトル画像を記事に挿入
            title_image_md = f"\n![{article_title}](/{title_image_path})\n\n"
            # 最初の ## の前に挿入
            content = re.sub(r'(---\n.*?\n---\n)(.*?)(##)', r'\1\2' + title_image_md + r'\3', content, flags=re.DOTALL)
            
            # 記事を更新
            with open(article_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"✅ Title image added: {os.path.basename(article_path)}")
            return True
        else:
            return False
        
    except Exception as e:
        print(f"❌ Error processing {article_path}: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Add title images to all articles')
    parser.add_argument('--limit', type=int, help='Limit number of articles to process')
    args = parser.parse_args()
    
    print("🎨 Adding title images to all articles...")
    
    # _postsディレクトリの全記事を取得
    articles = glob.glob("_posts/*.md")
    
    if not articles:
        print("ℹ️ No articles found in _posts directory")
        return
    
    if args.limit:
        articles = articles[:args.limit]
        print(f"📊 Processing {len(articles)} articles (limited)")
    else:
        print(f"📊 Found {len(articles)} articles to process")
    
    success_count = 0
    for i, article_path in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] Processing: {os.path.basename(article_path)}")
        if add_title_image_to_article(article_path):
            success_count += 1
    
    print(f"\n📊 Title image addition completed: {success_count}/{len(articles)} articles successfully processed")

if __name__ == "__main__":
    main()