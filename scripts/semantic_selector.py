#!/usr/bin/env python3
"""
Semantic article selector using sentence transformers
Removes duplicate articles based on semantic similarity
"""

import os
import glob
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

def get_embedding(model, text):
    """Get text embedding using sentence transformer"""
    return model.encode([text])

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
    """Convert title to URL-friendly slug with improved Japanese handling"""
    import re
    import unicodedata
    
    # Clean the title first
    title = title.strip().replace('"', '')
    
    # Comprehensive Japanese-to-English mapping for better SEO
    japanese_mappings = {
        r'GoogleとMeta.*覇権争い': 'google-meta-ai-competition',
        r'GPT-5.*衝撃': 'gpt-5-impact',
        r'NVIDIA.*Blackwell': 'nvidia-blackwell',
        r'OpenAI.*自社.*チップ': 'openai-custom-chip',
        r'Microsoft.*AI.*投資': 'microsoft-ai-investment',
        r'クラウド.*覇権': 'cloud-ai-competition',
        r'重力波検出.*AI': 'gravitational-wave-ai',
        r'Broadcom.*OpenAI': 'broadcom-openai-deal',
        
        # General terms
        r'人工知能|AI技術|汎用人工知能|AGI': 'ai',
        r'投資.*分析|市場.*分析': 'investment-analysis',
        r'技術.*解説|技術.*革新': 'technology-analysis', 
        r'最新.*動向|最新.*ニュース': 'latest-trends',
        r'実装.*事例': 'implementation-case',
        r'研究.*論文': 'research-paper',
        r'覇権.*争い|競争.*激化': 'market-competition',
        r'新時代.*拓く': 'new-era',
        r'未来.*加速': 'future-acceleration',
        
        # Company and product names (keep in romaji)
        r'マイクロソフト': 'microsoft',
        r'グーグル': 'google',
        r'アマゾン': 'amazon',
        r'メタ': 'meta',
        r'エヌビディア': 'nvidia',
        r'アップル': 'apple',
        r'オープンAI': 'openai',
        r'ブロードコム': 'broadcom',
        r'日立Vantara': 'hitachi-vantara',
        r'エッジAI': 'edge-ai',
    }
    
    # Apply mappings
    slug = title
    for pattern, replacement in japanese_mappings.items():
        slug = re.sub(pattern, replacement, slug, flags=re.IGNORECASE)
    
    # Remove remaining Japanese characters and special characters
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', '', slug)  # Remove Japanese chars
    
    # Clean up and format
    slug = re.sub(r'[-\s]+', '-', slug).strip('-').lower()
    
    # Ensure minimum quality
    if not slug or len(slug.replace('-', '')) < 3:
        return 'ai-article-update'
    
    return slug[:60]  # Increase limit to 60 characters for better descriptiveness

def generate_semantic_filename(filepath):
    """Generate semantic filename based on article title and date"""
    title = extract_title(filepath)
    date = extract_date(filepath)
    
    if not date:
        from datetime import datetime
        date = datetime.now().strftime('%Y-%m-%d')
    
    if not title:
        title = 'AI Article'
    
    slug = slugify(title)
    # Extract topic number from original temp filename for uniqueness
    import re
    match = re.search(r'-(\d+)-\d+\.md$', filepath)
    topic_num = match.group(1) if match else '1'
    
    return f'{date}-{topic_num}-{slug}.md'

def main():
    """Main semantic selector function"""
    print('🧠 Loading multilingual sentence transformer model...')
    try:
        model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    except Exception as e:
        print(f'❌ Failed to load semantic model: {e}')
        print('⚠️ Falling back to simple keyword-based duplicate detection')
        simple_fallback()
        return
    
    # Load existing titles
    existing_titles = []
    if os.path.exists('_temp/existing_titles.txt'):
        with open('_temp/existing_titles.txt', 'r', encoding='utf-8', errors='ignore') as f:
            existing_titles = [line.strip().replace('title:', '').strip().strip('"') 
                             for line in f.readlines() if line.strip()]
    
    # Process temporary articles
    temp_articles = glob.glob('_temp/temp-*.md')
    published_count = 0
    print(f'📝 Evaluating {len(temp_articles)} articles using semantic analysis...')
    
    # Create directory if it doesn't exist
    os.makedirs('_posts', exist_ok=True)
    
    for filepath in temp_articles:
        title = extract_title(filepath)
        if not title:
            print(f'⚠️ No title found in {filepath}')
            continue
            
        max_similarity = 0.0
        best_match = ""
        
        if existing_titles:
            title_embedding = get_embedding(model, title)
            for existing_title in existing_titles:
                if existing_title:
                    existing_embedding = get_embedding(model, existing_title)
                    similarity = cosine_similarity(
                        title_embedding.reshape(1, -1), 
                        existing_embedding.reshape(1, -1)
                    )[0][0]
                    if similarity > max_similarity:
                        max_similarity = similarity
                        best_match = existing_title
        
        # Multiple duplicate detection strategies
        similarity_duplicate = max_similarity > 0.75
        
        # Check for same-day topic duplicates (GPT-5, NVIDIA, etc.)
        date_today = extract_date(filepath)
        topic_duplicate = False
        
        if date_today:
            # Extract key topic from title
            title_lower = title.lower()
            key_topics = ['gpt-5', 'nvidia', 'google ai', 'microsoft ai', 'openai', 'meta ai']
            
            for topic in key_topics:
                if topic in title_lower:
                    # Check if we already have this topic today
                    today_files = glob.glob(f'_posts/{date_today}*{topic.replace(" ", "*")}*.md')
                    if today_files:
                        topic_duplicate = True
                        print(f'⚠️ Same-day topic duplicate detected: {topic} on {date_today}')
                        break
        
        is_duplicate = similarity_duplicate or topic_duplicate
        
        if not is_duplicate:
            final_name = generate_semantic_filename(filepath)
            try:
                os.rename(filepath, f'_posts/{final_name}')
                print(f'✅ Published: {final_name}')
                published_count += 1
            except Exception as e:
                print(f'❌ Failed to publish {final_name}: {e}')
        else:
            print(f'⏭️ Skipped duplicate: {title[:50]}...')
            print(f'   Similarity: {max_similarity:.3f} with "{best_match[:30]}..."')
            # Clean up duplicate file
            try:
                os.remove(filepath)
            except:
                pass
    
    print(f'📊 Published {published_count} unique articles via semantic analysis')

def simple_fallback():
    """Fallback to simple keyword-based duplicate detection"""
    print('🔧 Using simple keyword-based duplicate detection...')
    
    # Load existing titles for keyword matching
    existing_keywords = set()
    if os.path.exists('_temp/existing_titles.txt'):
        with open('_temp/existing_titles.txt', 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                title = line.strip().replace('title:', '').strip().strip('"')
                if title:
                    # Extract first few keywords
                    words = title.split()[:3]
                    existing_keywords.update(word.lower() for word in words if len(word) > 2)
    
    temp_articles = glob.glob('_temp/temp-*.md')
    published_count = 0
    os.makedirs('_posts', exist_ok=True)
    
    for filepath in temp_articles:
        title = extract_title(filepath)
        if not title:
            continue
            
        # Simple keyword-based duplicate check
        title_words = set(word.lower() for word in title.split()[:3] if len(word) > 2)
        overlap = len(title_words.intersection(existing_keywords))
        
        is_duplicate = overlap >= 3  # If 3+ keywords match existing titles (more lenient)
        
        if not is_duplicate:
            final_name = generate_semantic_filename(filepath)
            try:
                os.rename(filepath, f'_posts/{final_name}')
                print(f'✅ Published: {final_name}')
                published_count += 1
            except Exception as e:
                print(f'❌ Failed to publish {final_name}: {e}')
        else:
            print(f'⏭️ Skipped potential duplicate: {title[:50]}...')
            try:
                os.remove(filepath)
            except:
                pass
    
    print(f'📊 Published {published_count} articles via keyword analysis')

if __name__ == '__main__':
    main()