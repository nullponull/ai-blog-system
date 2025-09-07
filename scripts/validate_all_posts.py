#!/usr/bin/env python3
"""
Validate all posts after fixes
"""

import os
import glob
import re
from collections import defaultdict

def extract_frontmatter_field(filepath, field):
    """Extract a field from frontmatter"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if not content.strip():
                return f"EMPTY_FILE"
            
            lines = content.split('\n')
            in_frontmatter = False
            
            for line in lines:
                if line.strip() == '---':
                    if not in_frontmatter:
                        in_frontmatter = True
                        continue
                    else:
                        break
                if in_frontmatter and line.startswith(f'{field}:'):
                    return line.replace(f'{field}:', '').strip().strip('[]"')
    except Exception as e:
        return f"ERROR: {e}"
    return f"NOT_FOUND"

def classify_filename_pattern(filename):
    """Classify filename patterns"""
    name_part = re.sub(r'^\d{4}-\d{2}-\d{2}-\d+-', '', filename.replace('.md', ''))
    
    if len(name_part) <= 3:
        return "TOO_SHORT"
    elif name_part.startswith('ai-article'):
        return "GENERIC"
    elif re.match(r'^\d+$', name_part):
        return "NUMERIC_ONLY"
    elif len(name_part) > 50:
        return "TOO_LONG"
    else:
        return "GOOD"

def main():
    """Validate all posts"""
    print('🔍 Validating all posts after fixes...')
    
    post_files = glob.glob('_posts/*.md')
    
    # Statistics
    total_files = len(post_files)
    filename_patterns = defaultdict(int)
    categories = defaultdict(int)
    empty_files = []
    invalid_frontmatter = []
    
    print(f'\n📊 Total files: {total_files}')
    
    for filepath in post_files:
        filename = os.path.basename(filepath)
        
        # Check filename pattern
        pattern = classify_filename_pattern(filename)
        filename_patterns[pattern] += 1
        
        # Check frontmatter
        title = extract_frontmatter_field(filepath, 'title')
        category = extract_frontmatter_field(filepath, 'categories')
        tags = extract_frontmatter_field(filepath, 'tags')
        
        if title == "EMPTY_FILE":
            empty_files.append(filename)
        elif title == "NOT_FOUND" or category == "NOT_FOUND":
            invalid_frontmatter.append(filename)
        else:
            # Count categories
            if '"' in category:
                category = category.replace('"', '')
            categories[category] += 1
    
    print('\n📂 Filename Pattern Distribution:')
    print('=' * 40)
    for pattern, count in sorted(filename_patterns.items()):
        status = "✅" if pattern == "GOOD" else "⚠️"
        print(f'  {status} {pattern}: {count} files')
    
    print('\n🏷️ Category Distribution:')
    print('=' * 40)
    for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
        print(f'  {category}: {count} files')
    
    if empty_files:
        print(f'\n❌ Empty files found ({len(empty_files)}):')
        for file in empty_files[:5]:
            print(f'  - {file}')
    
    if invalid_frontmatter:
        print(f'\n❌ Invalid frontmatter ({len(invalid_frontmatter)}):')
        for file in invalid_frontmatter[:5]:
            print(f'  - {file}')
    
    # Quality score
    good_filenames = filename_patterns.get('GOOD', 0)
    quality_score = (good_filenames / total_files) * 100
    
    print(f'\n📈 Quality Score: {quality_score:.1f}%')
    print(f'   ({good_filenames}/{total_files} files have good filenames)')
    
    # Issues to address
    issues = []
    if filename_patterns.get('TOO_SHORT', 0) > 0:
        issues.append(f"{filename_patterns['TOO_SHORT']} files with too short names")
    if filename_patterns.get('GENERIC', 0) > 0:
        issues.append(f"{filename_patterns['GENERIC']} files with generic names")
    if len(empty_files) > 0:
        issues.append(f"{len(empty_files)} empty files")
    if len(invalid_frontmatter) > 0:
        issues.append(f"{len(invalid_frontmatter)} files with invalid frontmatter")
    
    if issues:
        print(f'\n⚠️ Remaining Issues:')
        for issue in issues:
            print(f'   - {issue}')
    else:
        print(f'\n✅ All validation checks passed!')
    
    # Save validation report
    os.makedirs('_temp', exist_ok=True)
    with open('_temp/validation_report.txt', 'w', encoding='utf-8') as f:
        f.write(f'Blog Post Validation Report\n')
        f.write(f'Generated: {__import__("datetime").datetime.now()}\n\n')
        f.write(f'Total files: {total_files}\n\n')
        
        f.write('Filename patterns:\n')
        for pattern, count in filename_patterns.items():
            f.write(f'  {pattern}: {count}\n')
        
        f.write('\nCategories:\n')
        for category, count in categories.items():
            f.write(f'  {category}: {count}\n')
        
        f.write(f'\nQuality score: {quality_score:.1f}%\n')
        
        if issues:
            f.write('\nRemaining issues:\n')
            for issue in issues:
                f.write(f'  - {issue}\n')
    
    print('\n📄 Validation report saved to _temp/validation_report.txt')

if __name__ == '__main__':
    main()