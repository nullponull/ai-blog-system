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

def main():
    """Main semantic selector function"""
    print('🧠 Loading multilingual sentence transformer model...')
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    
    # Load existing titles
    existing_titles = []
    if os.path.exists('_temp/existing_titles.txt'):
        with open('_temp/existing_titles.txt', 'r') as f:
            existing_titles = [line.strip().replace('title:', '').strip().strip('"') 
                             for line in f.readlines() if line.strip()]
    
    # Process temporary articles
    temp_articles = glob.glob('_temp/temp-*.md')
    published_count = 0
    print(f'📝 Evaluating {len(temp_articles)} articles...')
    
    for filepath in temp_articles:
        title = extract_title(filepath)
        if not title:
            continue
            
        max_similarity = 0.0
        if existing_titles:
            title_embedding = get_embedding(model, title)
            for existing_title in existing_titles:
                if existing_title:
                    existing_embedding = get_embedding(model, existing_title)
                    similarity = cosine_similarity(
                        title_embedding.reshape(1, -1), 
                        existing_embedding.reshape(1, -1)
                    )[0][0]
                    max_similarity = max(max_similarity, similarity)
        
        is_duplicate = max_similarity > 0.75
        
        if not is_duplicate:
            final_name = os.path.basename(filepath).replace('temp-', '')
            os.rename(filepath, f'_posts/{final_name}')
            print(f'✅ Published: {final_name}')
            published_count += 1
        else:
            print(f'⏭️ Skipped duplicate: {title[:50]}... (similarity: {max_similarity:.3f})')
    
    print(f'📊 Published {published_count} unique articles')

if __name__ == '__main__':
    main()