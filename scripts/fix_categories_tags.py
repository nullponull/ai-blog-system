#!/usr/bin/env python3
"""
Fix categories and tags in blog posts based on content analysis
"""

import os
import glob
import re
from pathlib import Path

def analyze_content_for_categories(filepath):
    """Analyze article content to determine appropriate categories"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
            title_content = content[:1000]  # Focus on title and first part
            
        # Define category keywords based on _config.yml definitions
        categories = {
            "AI最新ニュース": ["最新", "発表", "リリース", "新製品", "ニュース", "発表会", "アップデート", "新機能", "速報"],
            "AI導入戦略": ["投資", "市場", "株価", "資金調達", "評価額", "roi", "リターン", "投資家", "資本", "ファンド", "億ドル", "兆ドル", "戦略", "ロードマップ"],
            "AI技術ガイド": ["技術", "アーキテクチャ", "api", "sdk", "プログラム", "コード", "アルゴリズム", "モデル", "学習", "rag", "ファインチューニング"],
            "導入事例": ["実装", "導入", "活用", "事例", "ケーススタディ", "展開", "適用", "運用", "プロジェクト"],
            "研究論文": ["研究", "論文", "学術", "実験", "データ", "結果", "検証", "分析"],
            "業界別AI活用": ["製造", "金融", "医療", "小売", "物流", "教育", "建設", "不動産", "保険", "農業"]
        }
        
        # Count keyword matches for each category
        category_scores = {}
        for category, keywords in categories.items():
            score = sum(title_content.count(keyword) for keyword in keywords)
            if score > 0:
                category_scores[category] = score
        
        # Return the category with highest score, default to "最新動向"
        if category_scores:
            return max(category_scores, key=category_scores.get)
        else:
            return "最新動向"
            
    except Exception as e:
        print(f'Error analyzing {filepath}: {e}')
        return "最新動向"

def analyze_content_for_tags(filepath):
    """Analyze article content to determine appropriate tags"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
            
        # Define tag keywords
        tag_keywords = {
            "OpenAI": ["openai", "gpt", "chatgpt", "dall-e", "sam altman"],
            "Google": ["google", "gemini", "bard", "deepmind", "tpu", "alphabet"],
            "Microsoft": ["microsoft", "azure", "copilot", "satya nadella"],
            "Meta": ["meta", "facebook", "llama", "mark zuckerberg"],
            "NVIDIA": ["nvidia", "gpu", "cuda", "blackwell", "hopper", "jensen huang"],
            "Amazon": ["amazon", "aws", "alexa", "anthropic", "claude"],
            "Apple": ["apple", "siri", "ios", "tim cook"],
            "Anthropic": ["anthropic", "claude", "constitutional ai"],
            "投資": ["投資", "資金調達", "評価額", "株価", "市場", "ipo"],
            "技術革新": ["革新", "breakthrough", "innovation", "画期的"],
            "チップ": ["チップ", "chip", "gpu", "tpu", "semiconductor", "半導体"],
            "クラウド": ["クラウド", "cloud", "データセンター", "aws", "azure", "gcp"],
            "エージェント": ["エージェント", "agent", "自動化", "automation"],
            "データ": ["データ", "data", "ビッグデータ", "dataset"],
            "セキュリティ": ["セキュリティ", "security", "プライバシー", "privacy"],
            "倫理": ["倫理", "ethics", "責任", "安全性", "bias"],
            "医療": ["医療", "健康", "ヘルスケア", "診断", "治療"],
            "自動車": ["自動車", "車載", "自動運転", "tesla"],
            "生成AI": ["生成ai", "generative", "画像生成", "テキスト生成"],
            "LLM": ["llm", "large language model", "言語モデル", "transformer"]
        }
        
        # Find matching tags
        matched_tags = ["AI", "最新ニュース", "技術動向"]  # Default tags
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in content for keyword in keywords):
                if tag not in matched_tags:
                    matched_tags.append(tag)
        
        # Limit to 6 tags maximum for better organization
        return matched_tags[:6]
            
    except Exception as e:
        print(f'Error analyzing tags for {filepath}: {e}')
        return ["AI", "最新ニュース", "技術動向"]

def update_frontmatter(filepath):
    """Update the frontmatter of a markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check if file is empty or corrupted
        if not content.strip():
            print(f'⚠️ Empty file: {filepath}')
            return False
        
        lines = content.split('\n')
        
        # Find frontmatter boundaries
        frontmatter_start = -1
        frontmatter_end = -1
        
        for i, line in enumerate(lines):
            if line.strip() == '---':
                if frontmatter_start == -1:
                    frontmatter_start = i
                else:
                    frontmatter_end = i
                    break
        
        if frontmatter_start == -1 or frontmatter_end == -1:
            print(f'⚠️ No valid frontmatter found in {filepath}')
            return False
        
        # Analyze content for better categories and tags
        new_category = analyze_content_for_categories(filepath)
        new_tags = analyze_content_for_tags(filepath)
        
        # Update frontmatter lines
        updated_lines = []
        category_updated = False
        tags_updated = False
        
        for i, line in enumerate(lines):
            if frontmatter_start < i < frontmatter_end:
                if line.startswith('categories:'):
                    updated_lines.append(f'categories: ["{new_category}"]')
                    category_updated = True
                elif line.startswith('tags:'):
                    tag_str = ', '.join(f'"{tag}"' for tag in new_tags)
                    updated_lines.append(f'tags: [{tag_str}]')
                    tags_updated = True
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Write updated content back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))
        
        return True
        
    except Exception as e:
        print(f'❌ Failed to update {filepath}: {e}')
        return False

def main():
    """Fix categories and tags in all blog posts"""
    print('🔧 Fixing categories and tags in blog posts...')
    
    # Find all markdown files in _posts
    post_files = glob.glob('_posts/*.md')
    fixed_count = 0
    
    for filepath in post_files:
        filename = os.path.basename(filepath)
        
        if update_frontmatter(filepath):
            print(f'✅ Updated: {filename}')
            fixed_count += 1
        else:
            print(f'⏭️  Skipped: {filename}')
    
    print(f'\n📊 Updated {fixed_count} files with better categories and tags')

if __name__ == '__main__':
    main()