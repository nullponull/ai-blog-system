#!/usr/bin/env python3
"""
記事の完成度をチェックし、途中で終わった記事を検出・補完する機能
"""

import os
import re
import sys
from pathlib import Path
from datetime import datetime

def check_article_completion(file_path):
    """
    記事が完全かどうかをチェックする
    
    返り値:
    - 'complete': 完全な記事
    - 'incomplete_content': 本文が途中で終わっている
    - 'incomplete_structure': 構造的に不完全
    - 'too_short': 記事が短すぎる
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 基本的なフロントマターチェック
        if not content.startswith('---'):
            return 'incomplete_structure'
        
        # フロントマターの終了確認
        parts = content.split('---', 2)
        if len(parts) < 3:
            return 'incomplete_structure'
        
        article_body = parts[2].strip()
        
        # 記事が空または非常に短い
        if len(article_body) < 500:
            return 'too_short'
        
        # 文字数チェック（日本語記事として適切な長さ）
        if len(article_body) < 2000:
            return 'too_short'
        
        # 途中で切れている可能性をチェック
        # 1. 最後の文が不完全（句読点で終わっていない）
        lines = article_body.strip().split('\n')
        last_meaningful_line = ""
        
        # 最後の意味のある行を見つける
        for line in reversed(lines):
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('*'):
                last_meaningful_line = line
                break
        
        if last_meaningful_line:
            # 最後が句読点で終わっていない場合
            if not re.search(r'[。！？]$', last_meaningful_line):
                return 'incomplete_content'
            
            # 文の途中で切れているパターン
            if re.search(r'[、]$', last_meaningful_line):
                return 'incomplete_content'
            
            # 特定の文字で終わっている（文字化けや途切れの可能性）
            if re.search(r'[段エとかがてでにはをのもしまたり]$', last_meaningful_line):
                return 'incomplete_content'
        
        # 2. 記事の構造的チェック
        # 見出しが適切に配置されているか
        heading_count = len(re.findall(r'^#{1,3} ', article_body, re.MULTILINE))
        if heading_count < 2:  # タイトル以外に少なくとも1つの見出しが必要
            return 'incomplete_structure'
        
        # 3. 結論部分があるかチェック
        conclusion_patterns = [
            r'まとめ',
            r'結論',
            r'おわりに',
            r'今後の展望',
            r'最後に'
        ]
        
        has_conclusion = any(
            re.search(pattern, article_body, re.IGNORECASE)
            for pattern in conclusion_patterns
        )
        
        # 結論がなく、記事が短い場合は不完全の可能性
        if not has_conclusion and len(article_body) < 3000:
            return 'incomplete_content'
        
        return 'complete'
        
    except Exception as e:
        print(f"エラー: {file_path} の読み取りに失敗: {e}")
        return 'error'

def find_incomplete_articles(posts_dir='_posts', days_back=7):
    """
    最近の記事から不完全なものを検索
    """
    posts_path = Path(posts_dir)
    if not posts_path.exists():
        print(f"投稿ディレクトリが見つかりません: {posts_dir}")
        return []
    
    incomplete_articles = []
    
    # 最近の記事をチェック
    for md_file in posts_path.glob('*.md'):
        # ファイル名から日付を抽出
        date_match = re.match(r'(\d{4}-\d{2}-\d{2})', md_file.name)
        if not date_match:
            continue
        
        file_date = datetime.strptime(date_match.group(1), '%Y-%m-%d')
        days_ago = (datetime.now() - file_date).days
        
        if days_ago <= days_back:
            status = check_article_completion(md_file)
            if status != 'complete':
                incomplete_articles.append({
                    'file': str(md_file),
                    'filename': md_file.name,
                    'status': status,
                    'date': file_date.strftime('%Y-%m-%d')
                })
    
    return incomplete_articles

def generate_completion_prompt(article_path):
    """
    記事の続きを生成するためのプロンプトを作成
    """
    try:
        with open(article_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # フロントマターを分離
        parts = content.split('---', 2)
        if len(parts) >= 3:
            frontmatter = parts[1]
            article_body = parts[2]
        else:
            frontmatter = ""
            article_body = content
        
        # タイトルを抽出
        title_match = re.search(r'title:\s*["\']?([^"\']+)["\']?', frontmatter)
        title = title_match.group(1) if title_match else "AI記事"
        
        # 既存の内容の最後の部分を取得（コンテキスト用）
        words = article_body.strip().split()
        context_words = words[-200:] if len(words) > 200 else words
        context = ' '.join(context_words)
        
        prompt = f"""以下の記事「{title}」が途中で終わっています。この記事の続きを自然に書いて完成させてください。

【既存の記事の最後の部分】
{context}

【要求事項】
1. 上記の文章から自然に続くように記事を完成させる
2. 記事全体で3000-4000文字程度になるよう調整
3. 日本語として自然な文章で書く
4. AIらしい機械的な表現は避ける
5. 投資家・技術者にとって有用な情報を含める
6. 最後に適切な結論で締めくくる
7. 記事の末尾に ---END--- を必ず追加する

【注意】
- フロントマターは追加しない（本文のみ）
- 既存の内容を繰り返さない
- 自然な流れで続きを書く

続きを書いてください："""
        
        return prompt
        
    except Exception as e:
        print(f"プロンプト生成エラー: {e}")
        return None

def main():
    """メイン処理"""
    if len(sys.argv) > 1:
        posts_dir = sys.argv[1]
    else:
        posts_dir = '_posts'
    
    print("🔍 不完全な記事を検索中...")
    incomplete_articles = find_incomplete_articles(posts_dir)
    
    if not incomplete_articles:
        print("✅ すべての記事は完成しています")
        return
    
    print(f"\n📋 {len(incomplete_articles)}個の不完全な記事を発見:")
    for article in incomplete_articles:
        print(f"  📄 {article['filename']}")
        print(f"     状態: {article['status']}")
        print(f"     日付: {article['date']}")
        
        # 補完用のプロンプトを生成
        prompt = generate_completion_prompt(article['file'])
        if prompt:
            # プロンプトをファイルに保存
            prompt_file = f"_temp/completion_prompt_{article['filename']}.txt"
            os.makedirs('_temp', exist_ok=True)
            
            with open(prompt_file, 'w', encoding='utf-8') as f:
                f.write(prompt)
            print(f"     💡 補完プロンプト: {prompt_file}")
        
        print()
    
    # 補完対象のファイルリストを出力
    completion_files = [article['filename'] for article in incomplete_articles]
    with open('_temp/incomplete_articles.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(completion_files))
    
    print(f"📝 補完対象ファイル一覧: _temp/incomplete_articles.txt")

if __name__ == "__main__":
    main()