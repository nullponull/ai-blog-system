#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import json
import re
import glob
from datetime import datetime
from PIL import Image
import io

def generate_image_from_title(title, article_path):
    """記事タイトルから画像を生成"""
    
    # HuggingFace API設定 - より確実なモデルを使用
    api_url = "https://api-inference.huggingface.co/models/runwayml/stable-diffusion-v1-5"
    headers = {
        "Authorization": f"Bearer {os.environ.get('HUGGINGFACE_TOKEN')}"
    }
    
    # AIトピック向けのプロンプト作成
    base_prompt = f"Professional technology illustration for: {title}. Modern, clean, technological, AI concept, digital art, high quality, blue and white color scheme"
    
    payload = {
        "inputs": base_prompt,
        "parameters": {
            "num_inference_steps": 30,
            "guidance_scale": 7.5,
            "width": 1024,
            "height": 576
        }
    }
    
    try:
        print(f"🎨 Generating image for: {title[:50]}...")
        
        # API リクエスト
        response = requests.post(api_url, headers=headers, json=payload, timeout=60)
        
        print(f"🔍 API Response Status: {response.status_code}")
        if response.status_code != 200:
            print(f"🔍 Response content: {response.text[:200]}")
        
        if response.status_code == 200:
            # 画像を保存
            image = Image.open(io.BytesIO(response.content))
            
            # ファイル名作成
            filename = os.path.basename(article_path).replace('.md', '-featured.jpg')
            image_path = f"assets/images/posts/{filename}"
            
            # RGB変換してJPEG保存
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            image.save(image_path, 'JPEG', quality=85, optimize=True)
            
            # 記事にimage frontmatterを追加
            add_image_to_article(article_path, f"/assets/images/posts/{filename}")
            
            print(f"✅ Generated: {image_path}")
            return True
            
        elif response.status_code == 503:
            print(f"⏳ Model loading for: {title[:30]}... (will retry)")
            return False
        else:
            print(f"❌ Failed to generate image: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error generating image: {str(e)}")
        return False

def add_image_to_article(article_path, image_path):
    """記事にimage frontmatterを追加"""
    
    try:
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # frontmatterにimageフィールドを追加
        if 'image:' not in content:
            content = content.replace('reading_time: 8', f'reading_time: 8\nimage: "{image_path}"')
            
            with open(article_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
    except Exception as e:
        print(f"⚠️ Could not add image to article: {str(e)}")

def main():
    """メイン処理"""
    
    if not os.environ.get('HUGGINGFACE_TOKEN'):
        print("⚠️ HUGGINGFACE_TOKEN not found, skipping image generation")
        return
    
    # 今日の記事を取得
    today = datetime.now().strftime("%Y-%m-%d")
    article_pattern = f"_posts/{today}-*.md"
    articles = glob.glob(article_pattern)
    
    if not articles:
        print("ℹ️ No articles found for today")
        return
    
    print(f"🎨 Found {len(articles)} articles to process")
    
    generated_count = 0
    for article_path in articles:
        
        # 既に画像がある場合はスキップ
        image_filename = os.path.basename(article_path).replace('.md', '-featured.jpg')
        image_path = f"assets/images/posts/{image_filename}"
        
        if os.path.exists(image_path):
            print(f"⏭️ Image already exists: {image_filename}")
            continue
        
        # タイトル抽出
        try:
            with open(article_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('title:'):
                        title = line.replace('title:', '').strip().strip('"')
                        break
                else:
                    print(f"⚠️ No title found in {article_path}")
                    continue
        except:
            print(f"⚠️ Could not read {article_path}")
            continue
        
        # 画像生成
        if generate_image_from_title(title, article_path):
            generated_count += 1
        
        # API制限を避けるための待機
        import time
        time.sleep(2)
    
    print(f"🎨 Generated {generated_count} images")

if __name__ == "__main__":
    main()