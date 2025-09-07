#!/usr/bin/env python3
"""
Fix poor filenames that need better semantic names
"""

import os
import glob
import re
from pathlib import Path

def extract_title_from_file(filepath):
    """Extract title from markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('title:'):
                    return line.replace('title:', '').strip().strip('"')
    except Exception:
        pass
    return ""

def extract_date_from_file(filepath):
    """Extract date from markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('date:'):
                    date_str = line.replace('date:', '').strip()
                    return date_str.split()[0]  # Get YYYY-MM-DD part
    except Exception:
        pass
    return ""

def slugify_enhanced(title):
    """Enhanced slugify function for Japanese content"""
    import re
    import unicodedata
    
    if not title:
        return "ai-article"
    
    # Normalize unicode
    title = unicodedata.normalize('NFKD', title)
    
    # Replace Japanese terms with English equivalents
    replacements = {
        'ai技術': 'ai-tech',
        'ai投資': 'ai-investment', 
        'ai市場': 'ai-market',
        '最新': 'latest',
        '発表': 'announcement',
        'リリース': 'release',
        '企業': 'company',
        '市場': 'market',
        '投資': 'investment',
        '技術': 'tech',
        '分析': 'analysis',
        '動向': 'trends',
        '進化': 'evolution',
        '革新': 'innovation',
        'openai': 'openai',
        'google': 'google',
        'microsoft': 'microsoft',
        'nvidia': 'nvidia',
        'meta': 'meta',
        'amazon': 'amazon',
        'gpt': 'gpt',
        'gemini': 'gemini',
        'claude': 'claude'
    }
    
    title_lower = title.lower()
    for japanese, english in replacements.items():
        title_lower = title_lower.replace(japanese, english)
    
    # Remove special characters and clean up
    slug = re.sub(r'[^\w\s-]', '', title_lower)
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    
    # Ensure minimum length and limit
    if len(slug.replace('-', '')) < 3:
        return "ai-article"
    
    return slug[:50]

def should_fix_filename(filename):
    """Check if filename needs fixing"""
    # Remove .md extension and date prefix
    name_part = re.sub(r'^\d{4}-\d{2}-\d{2}-\d+-', '', filename.replace('.md', ''))
    
    # Criteria for fixing
    conditions = [
        len(name_part) <= 3,  # Too short (ai.md, aiai.md)
        name_part.startswith('ai-article'),  # Generic names from previous fixes
        name_part in ['ai', 'aiai', 'aiaiai'],  # Specific bad names
    ]
    
    return any(conditions)

def generate_better_filename(filepath):
    """Generate better filename based on title and date"""
    title = extract_title_from_file(filepath)
    date = extract_date_from_file(filepath)
    
    # Get date from filename if not found in content
    if not date:
        filename = os.path.basename(filepath)
        date_match = re.match(r'^(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            date = date_match.group(1)
        else:
            from datetime import datetime
            date = datetime.now().strftime('%Y-%m-%d')
    
    # Extract topic number for uniqueness
    filename = os.path.basename(filepath)
    topic_match = re.search(r'-(\d+)-', filename)
    topic_num = topic_match.group(1) if topic_match else '1'
    
    # Use title to create semantic filename
    if title and len(title.strip()) > 0:
        slug = slugify_enhanced(title)
    else:
        slug = "ai-article"
    
    return f'{date}-{topic_num}-{slug}.md'

def main():
    """Fix poor filenames"""
    print('🔧 Fixing poor filenames...')
    
    # Find all markdown files that need fixing
    post_files = glob.glob('_posts/*.md')
    fixed_count = 0
    
    for filepath in post_files:
        filename = os.path.basename(filepath)
        
        if should_fix_filename(filename):
            new_filename = generate_better_filename(filepath)
            new_filepath = os.path.join('_posts', new_filename)
            
            # Avoid overwriting existing files
            counter = 1
            original_new_filepath = new_filepath
            while os.path.exists(new_filepath) and new_filepath != filepath:
                base, ext = os.path.splitext(original_new_filepath)
                new_filepath = f"{base}-{counter}{ext}"
                counter += 1
            
            # Only rename if the new name is different and better
            if new_filepath != filepath and os.path.basename(new_filepath) != filename:
                try:
                    os.rename(filepath, new_filepath)
                    print(f'✅ Renamed: {filename} → {os.path.basename(new_filepath)}')
                    fixed_count += 1
                except Exception as e:
                    print(f'❌ Failed to rename {filename}: {e}')
            else:
                print(f'⏭️  Skipped: {filename} (no better name available)')
        else:
            print(f'✅ Good: {filename}')
    
    print(f'\n📊 Fixed {fixed_count} poor filenames')

if __name__ == '__main__':
    main()