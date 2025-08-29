#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import glob
import re
import subprocess
import requests
import base64
from PIL import Image
import io

def generate_simple_mermaid(article_content, article_title, base_filename):
    """超シンプルなMermaid図解を生成"""
    
    try:
        print(f"🖼️ Generating simple Mermaid diagram...")
        
        # 極めてシンプルなプロンプト
        prompt = f"記事: {article_title}\n\n"
        prompt += "この記事の核心を表す超シンプルなMermaid図解を1個だけ作成してください。\n\n"
        prompt += "要求事項:\n"
        prompt += "- 3個のノードのみ\n"
        prompt += "- 1-2文字の日本語ラベル\n"
        prompt += "- 基本的な矢印のみ\n"
        prompt += "- 50文字以内\n\n"
        prompt += "例: graph TD; A[AI]-->B[企業]-->C[規制]\n\n"
        prompt += "形式:\n"
        prompt += "```mermaid\n"
        prompt += "[Mermaidコード]\n"
        prompt += "```\n"
        
        # Gemini CLIを実行
        result = subprocess.run([
            'gemini', '-m', 'gemini-2.5-flash', '-p', prompt
        ], capture_output=True, text=True, timeout=30, encoding='utf-8')
        
        if result.returncode == 0:
            content = result.stdout
            
            # Mermaid記法を抽出
            pattern = r'```mermaid\s*(.*?)\s*```'
            match = re.search(pattern, content, re.DOTALL)
            
            if match:
                mermaid_code = match.group(1).strip()
                print(f"📏 Generated code length: {len(mermaid_code)} chars")
                print(f"🔍 Code: {mermaid_code}")
                
                # 画像に変換を試行
                image_path = f"assets/images/posts/{base_filename}-mermaid-simple.jpg"
                if mermaid_to_image_simple(mermaid_code, image_path):
                    return {
                        'path': f"/assets/images/posts/{os.path.basename(image_path)}",
                        'title': f"{article_title}の概要図",
                        'mermaid_code': mermaid_code,
                        'type': 'image'
                    }
                else:
                    # 画像変換に失敗した場合はMermaidコードブロックとして返す
                    return {
                        'title': f"{article_title}の概要図",
                        'mermaid_code': mermaid_code,
                        'type': 'code'
                    }
            
            print("⚠️ No valid Mermaid code found in response")
            return None
            
        else:
            print(f"❌ Mermaid generation failed: {result.stderr}")
            return None
            
    except Exception as e:
        print(f"❌ Error generating Mermaid: {str(e)}")
        return None

def mermaid_to_image_simple(mermaid_code, output_path):
    """シンプルなMermaid記法を画像に変換"""
    
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        print(f"🖼️ Converting to image: {os.path.basename(output_path)}")
        
        # Base64エンコード
        encoded_mermaid = base64.b64encode(mermaid_code.encode('utf-8')).decode('utf-8')
        mermaid_url = f"https://mermaid.ink/img/{encoded_mermaid}"
        
        print(f"📏 URL length: {len(mermaid_url)} chars")
        
        if len(mermaid_url) > 800:  # より厳しい制限
            print(f"⚠️ URL still too long, skipping...")
            return False
        
        response = requests.get(mermaid_url, timeout=60)
        
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
            image.save(output_path, 'JPEG', quality=90, optimize=True)
            
            print(f"✅ Simple Mermaid image saved: {os.path.basename(output_path)}")
            return True
            
        else:
            print(f"❌ Mermaid API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error converting simple Mermaid: {str(e)}")
        return False

def add_mermaid_to_article(article_path):
    """記事にシンプルなMermaid図解を追加"""
    
    try:
        print(f"📄 Processing: {os.path.basename(article_path)}")
        
        # 記事を読み込み（エンコーディングエラー対応）
        try:
            with open(article_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            print(f"⚠️ UTF-8 encoding error, skipping: {os.path.basename(article_path)}")
            return False
        
        # 既にMermaid図解があるかチェック
        if '## 図解' in content or '-mermaid-' in content:
            print(f"⚠️ Mermaid diagram already exists, skipping: {os.path.basename(article_path)}")
            return True
        
        # タイトルを抽出
        title_match = re.search(r'title:\s*["\']([^"\']+)["\']', content)
        if not title_match:
            print(f"⚠️ No title found in {article_path}")
            return False
        
        article_title = title_match.group(1)
        
        # 記事内容を抽出
        content_match = re.search(r'---\s*$(.+)', content, re.MULTILINE | re.DOTALL)
        article_content = content_match.group(1) if content_match else content
        
        # ベースファイル名を取得
        base_filename = os.path.basename(article_path).replace('.md', '')
        
        # シンプルなMermaid図解を生成
        mermaid_diagram = generate_simple_mermaid(article_content[:500], article_title, base_filename)
        
        if mermaid_diagram:
            # 記事の最後に図解セクションを追加
            diagram_section = "\n\n## 図解\n\n"
            diagram_section += f"### {mermaid_diagram['title']}\n\n"
            
            if mermaid_diagram['type'] == 'image':
                diagram_section += f"![{mermaid_diagram['title']}]({mermaid_diagram['path']})\n\n"
            else:
                # 画像化に失敗した場合はMermaidコードブロックとして挿入
                diagram_section += "```mermaid\n"
                diagram_section += mermaid_diagram['mermaid_code'] + "\n"
                diagram_section += "```\n\n"
            
            # 記事を更新
            content += diagram_section
            
            with open(article_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            print(f"✅ Mermaid diagram added: {os.path.basename(article_path)}")
            return True
        else:
            print(f"⚠️ Failed to generate Mermaid for: {os.path.basename(article_path)}")
            return False
        
    except Exception as e:
        print(f"❌ Error processing {article_path}: {str(e)}")
        return False

def main():
    """メイン処理: すべての記事にMermaid図解を追加"""
    
    print("🖼️ Adding Mermaid diagrams to all articles...")
    
    # _postsディレクトリの全記事を取得
    articles = glob.glob("_posts/*.md")
    
    if not articles:
        print("ℹ️ No articles found in _posts directory")
        return
    
    print(f"📊 Found {len(articles)} articles to process")
    
    success_count = 0
    for i, article_path in enumerate(articles, 1):
        print(f"\n[{i}/{len(articles)}] Processing: {os.path.basename(article_path)}")
        if add_mermaid_to_article(article_path):
            success_count += 1
    
    print(f"\n📊 Mermaid addition completed: {success_count}/{len(articles)} articles successfully processed")

if __name__ == "__main__":
    main()