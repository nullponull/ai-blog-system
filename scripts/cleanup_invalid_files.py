#!/usr/bin/env python3
"""
Clean up files with invalid frontmatter and generic names
"""

import os
import glob
import re
from pathlib import Path

def check_file_validity(filepath):
    """Check if file has valid structure"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if not content.strip():
            return "EMPTY"
        
        # Check if it has proper frontmatter structure
        lines = content.split('\n')
        if len(lines) < 5:
            return "TOO_SHORT"
        
        # Look for frontmatter boundaries
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
            return "INVALID_FRONTMATTER"
        
        # Check if title exists
        title_found = False
        for i in range(frontmatter_start + 1, frontmatter_end):
            if i < len(lines) and lines[i].startswith('title:'):
                title = lines[i].replace('title:', '').strip().strip('"')
                if title:
                    title_found = True
                break
        
        if not title_found:
            return "NO_TITLE"
        
        # Check if content exists after frontmatter
        content_after_frontmatter = '\n'.join(lines[frontmatter_end + 1:]).strip()
        if not content_after_frontmatter:
            return "NO_CONTENT"
        
        return "VALID"
    
    except Exception as e:
        return f"ERROR: {e}"

def fix_line_formatting(filepath):
    """Fix files where all content is on one line"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check if it's all on one line and needs formatting
        lines = content.split('\n')
        if len(lines) == 1 and '---' in content:
            # This looks like a single line with the entire content
            # Try to split it properly
            content = content.replace(' ---', '\n---\n')
            content = content.replace('--- ', '\n---\n')
            content = re.sub(r' (layout|title|date|categories|tags|author|excerpt|reading_time):', r'\n\1:', content)
            content = re.sub(r' # ', r'\n\n# ', content)
            content = re.sub(r' ## ', r'\n\n## ', content)
            content = re.sub(r'。 ', r'。\n\n', content)
            
            # Write back the formatted content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return True
    except Exception as e:
        print(f"Error fixing formatting for {filepath}: {e}")
        return False
    
    return False

def extract_title_for_renaming(filepath):
    """Extract title from file for better naming"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Look for title in frontmatter
        lines = content.split('\n')
        for line in lines:
            if line.strip().startswith('title:'):
                title = line.replace('title:', '').strip().strip('"')
                return title
        
        # Look for H1 in content
        for line in lines:
            if line.strip().startswith('# '):
                title = line.replace('#', '').strip()
                return title
    
    except Exception:
        pass
    
    return ""

def slugify_for_filename(title):
    """Create URL-friendly slug from title"""
    if not title:
        return "article"
    
    import unicodedata
    
    # Normalize and convert
    title = unicodedata.normalize('NFKD', title)
    
    # Replace Japanese terms with English
    replacements = {
        'ai技術': 'ai-tech',
        'ai投資': 'ai-investment', 
        '最新': 'latest',
        '企業': 'company',
        '市場': 'market',
        '投資': 'investment',
        '技術': 'tech',
        '分析': 'analysis',
        '動向': 'trends',
        '進化': 'evolution',
        'openai': 'openai',
        'google': 'google',
        'microsoft': 'microsoft',
        'nvidia': 'nvidia'
    }
    
    title_lower = title.lower()
    for jp, en in replacements.items():
        title_lower = title_lower.replace(jp, en)
    
    # Clean up
    slug = re.sub(r'[^\w\s-]', '', title_lower)
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    
    return slug[:40] if slug else "article"

def main():
    """Clean up invalid files and generic names"""
    print('🧹 Cleaning up invalid files and generic names...')
    
    # Find all ai-article files
    ai_article_files = glob.glob('_posts/*ai-article*.md')
    
    processed = 0
    fixed = 0
    removed = 0
    renamed = 0
    
    for filepath in ai_article_files:
        filename = os.path.basename(filepath)
        print(f'\n🔍 Processing: {filename}')
        
        # Check validity
        validity = check_file_validity(filepath)
        
        if validity == "EMPTY":
            print(f'  ❌ Empty file - removing')
            try:
                os.remove(filepath)
                removed += 1
            except Exception as e:
                print(f'  Failed to remove: {e}')
        
        elif validity in ["TOO_SHORT", "NO_CONTENT"]:
            print(f'  ❌ Invalid file ({validity}) - removing')
            try:
                os.remove(filepath)
                removed += 1
            except Exception as e:
                print(f'  Failed to remove: {e}')
        
        elif validity == "INVALID_FRONTMATTER":
            print(f'  🔧 Attempting to fix formatting...')
            if fix_line_formatting(filepath):
                # Re-check after fixing
                new_validity = check_file_validity(filepath)
                if new_validity == "VALID":
                    print(f'  ✅ Fixed formatting')
                    fixed += 1
                else:
                    print(f'  ❌ Still invalid after fix - removing')
                    try:
                        os.remove(filepath)
                        removed += 1
                    except Exception as e:
                        print(f'  Failed to remove: {e}')
            else:
                print(f'  ❌ Could not fix - removing')
                try:
                    os.remove(filepath)
                    removed += 1
                except Exception as e:
                    print(f'  Failed to remove: {e}')
        
        elif validity == "VALID":
            # File is valid but has generic name - try to rename
            title = extract_title_for_renaming(filepath)
            if title:
                # Extract date and topic number from filename
                date_match = re.match(r'^(\d{4}-\d{2}-\d{2})', filename)
                topic_match = re.search(r'-(\d+)-', filename)
                
                if date_match and topic_match:
                    date = date_match.group(1)
                    topic_num = topic_match.group(1)
                    slug = slugify_for_filename(title)
                    
                    new_filename = f'{date}-{topic_num}-{slug}.md'
                    new_filepath = os.path.join('_posts', new_filename)
                    
                    # Avoid overwriting
                    counter = 1
                    original_new_filepath = new_filepath
                    while os.path.exists(new_filepath):
                        base, ext = os.path.splitext(original_new_filepath)
                        new_filepath = f"{base}-{counter}{ext}"
                        counter += 1
                    
                    try:
                        os.rename(filepath, new_filepath)
                        print(f'  ✅ Renamed to: {os.path.basename(new_filepath)}')
                        renamed += 1
                    except Exception as e:
                        print(f'  ❌ Failed to rename: {e}')
                else:
                    print(f'  ⚠️  Could not extract date/topic from filename')
            else:
                print(f'  ⚠️  No title found for renaming')
        
        else:
            print(f'  ❌ Error: {validity}')
        
        processed += 1
    
    print(f'\n📊 Cleanup Summary:')
    print(f'  Processed: {processed} files')
    print(f'  Fixed formatting: {fixed} files')
    print(f'  Renamed: {renamed} files')
    print(f'  Removed: {removed} files')
    
    # Final check - count remaining generic files
    remaining_generic = len(glob.glob('_posts/*ai-article*.md'))
    print(f'  Remaining generic files: {remaining_generic}')

if __name__ == '__main__':
    main()