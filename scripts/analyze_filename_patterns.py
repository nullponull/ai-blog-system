#!/usr/bin/env python3
"""
Analyze filename patterns in all blog posts
"""

import os
import glob
import re
from collections import defaultdict

def classify_filename_pattern(filename):
    """Classify filename into different patterns"""
    # Remove .md extension and date prefix for analysis
    name_part = re.sub(r'^\d{4}-\d{2}-\d{2}-\d+-', '', filename.replace('.md', ''))
    
    # Pattern classification
    if len(name_part) <= 3:
        return "too_short"  # ai, aiai等
    elif re.match(r'^\d+$', name_part):
        return "numeric_only"  # 084427等（既に修正済みのはず）
    elif len(name_part) > 50:
        return "too_long"  # 長すぎるファイル名
    elif re.search(r'[^\w-]', name_part):
        return "special_chars"  # 特殊文字含む
    elif name_part == "ai-article" or name_part.startswith("ai-article-"):
        return "generic_fixed"  # 修正済みの汎用名
    elif re.search(r'[a-zA-Z]', name_part) and not re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', name_part):
        return "romaji_based"  # ローマ字ベース
    else:
        return "good"  # 適切なファイル名

def extract_title_from_file(filepath):
    """Extract title from markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('title:'):
                    return line.replace('title:', '').strip().strip('"')
    except Exception:
        pass
    return "No title found"

def extract_category_from_file(filepath):
    """Extract category from markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('categories:'):
                    return line.replace('categories:', '').strip().strip('[]"')
    except Exception:
        pass
    return "No category found"

def main():
    """Analyze all filename patterns"""
    print('🔍 Analyzing filename patterns in all posts...')
    
    # Find all markdown files
    post_files = glob.glob('_posts/*.md')
    
    # Classify by pattern
    pattern_groups = defaultdict(list)
    category_counts = defaultdict(int)
    
    for filepath in post_files:
        filename = os.path.basename(filepath)
        pattern = classify_filename_pattern(filename)
        title = extract_title_from_file(filepath)
        category = extract_category_from_file(filepath)
        
        pattern_groups[pattern].append({
            'filename': filename,
            'title': title,
            'category': category
        })
        
        # Count categories
        if 'AI技術' in category:
            category_counts['AI技術'] += 1
        elif '投資分析' in category:
            category_counts['投資分析'] += 1
        elif '技術実装' in category:
            category_counts['技術実装'] += 1
        elif '市場動向' in category:
            category_counts['市場動向'] += 1
        elif '最新動向' in category:
            category_counts['最新動向'] += 1
        else:
            category_counts['その他'] += 1
    
    print(f'\n📊 Total files analyzed: {len(post_files)}')
    print('\n📂 Filename Pattern Analysis:')
    print('=' * 60)
    
    for pattern, files in pattern_groups.items():
        print(f'\n{pattern.upper()} ({len(files)} files):')
        if pattern in ['too_short', 'numeric_only', 'too_long', 'generic_fixed']:
            print('  需要修正 - Examples:')
            for file_info in files[:5]:  # Show first 5 examples
                print(f'    {file_info["filename"][:50]} -> "{file_info["title"][:30]}"')
        else:
            print('  状態良好 - Examples:')
            for file_info in files[:3]:  # Show first 3 examples
                print(f'    {file_info["filename"][:50]} -> "{file_info["title"][:30]}"')
    
    print(f'\n🏷️ Category Distribution:')
    print('=' * 40)
    for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f'  {category}: {count} files')
    
    # Identify files that need fixing
    needs_fixing = []
    for pattern in ['too_short', 'numeric_only', 'generic_fixed']:
        if pattern in pattern_groups:
            needs_fixing.extend(pattern_groups[pattern])
    
    print(f'\n⚠️ Files that need filename fixes: {len(needs_fixing)}')
    
    # Save analysis results
    with open('_temp/filename_analysis.txt', 'w', encoding='utf-8') as f:
        f.write(f'Filename Pattern Analysis\n')
        f.write(f'Total files: {len(post_files)}\n\n')
        
        for pattern, files in pattern_groups.items():
            f.write(f'{pattern}: {len(files)} files\n')
            for file_info in files:
                f.write(f'  {file_info["filename"]} | {file_info["title"]} | {file_info["category"]}\n')
            f.write('\n')
        
        f.write('Category counts:\n')
        for category, count in category_counts.items():
            f.write(f'  {category}: {count}\n')
    
    print('\n✅ Analysis complete! Results saved to _temp/filename_analysis.txt')
    return len(needs_fixing)

if __name__ == '__main__':
    main()