#!/usr/bin/env python3
"""
Fix existing blog posts with numeric filenames
Rename them to use semantic filenames based on their titles
"""

import os
import glob
import re
from pathlib import Path

def extract_title(filepath):
    """Extract title from markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('title:'):
                    return line.replace('title:', '').strip().strip('"')
    except Exception as e:
        print(f'Error reading {filepath}: {e}')
    return ''

def extract_date(filepath):
    """Extract date from markdown file"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if line.startswith('date:'):
                    date_str = line.replace('date:', '').strip()
                    return date_str.split()[0]  # Get YYYY-MM-DD part
    except Exception as e:
        print(f'Error reading date from {filepath}: {e}')
    return ''

def slugify(title):
    """Convert title to URL-friendly slug"""
    # Remove or replace special characters
    slug = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces with hyphens and lowercase
    slug = re.sub(r'[-\s]+', '-', slug).strip('-').lower()
    # Limit length and ensure it's not empty
    if not slug:
        return 'ai-article'
    return slug[:50]  # Limit to 50 characters

def is_problematic_filename(filename):
    """Check if filename has numeric pattern that causes title issues"""
    # Look for pattern like YYYY-MM-DD-N-NNNNNN.md
    pattern = r'^\d{4}-\d{2}-\d{2}-\d+-\d+\.md$'
    return bool(re.match(pattern, filename))

def generate_semantic_filename(filepath):
    """Generate semantic filename based on article title and date"""
    title = extract_title(filepath)
    date = extract_date(filepath)
    
    # Extract original filename to get date if not found in content
    if not date:
        filename = os.path.basename(filepath)
        date_match = re.match(r'^(\d{4}-\d{2}-\d{2})', filename)
        if date_match:
            date = date_match.group(1)
        else:
            from datetime import datetime
            date = datetime.now().strftime('%Y-%m-%d')
    
    if not title:
        title = 'AI Article'
    
    slug = slugify(title)
    
    # Extract topic number from original filename for uniqueness
    filename = os.path.basename(filepath)
    match = re.search(r'-(\d+)-\d+\.md$', filename)
    topic_num = match.group(1) if match else '1'
    
    return f'{date}-{topic_num}-{slug}.md'

def main():
    """Fix existing problematic files"""
    print('🔧 Fixing existing problematic article filenames...')
    
    # Find all markdown files in _posts
    post_files = glob.glob('_posts/*.md')
    fixed_count = 0
    
    for filepath in post_files:
        filename = os.path.basename(filepath)
        
        if is_problematic_filename(filename):
            new_filename = generate_semantic_filename(filepath)
            new_filepath = os.path.join('_posts', new_filename)
            
            # Avoid overwriting existing files
            counter = 1
            original_new_filepath = new_filepath
            while os.path.exists(new_filepath):
                base, ext = os.path.splitext(original_new_filepath)
                new_filepath = f"{base}-{counter}{ext}"
                counter += 1
            
            try:
                os.rename(filepath, new_filepath)
                print(f'✅ Renamed: {filename} → {os.path.basename(new_filepath)}')
                fixed_count += 1
            except Exception as e:
                print(f'❌ Failed to rename {filename}: {e}')
        else:
            print(f'⏭️  Skipped: {filename} (already has good filename)')
    
    print(f'📊 Fixed {fixed_count} problematic filenames')

if __name__ == '__main__':
    main()