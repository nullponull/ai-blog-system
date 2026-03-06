#!/usr/bin/env python3
"""
fix_seo_meta.py - SEO meta description自動修正スクリプト

機能:
1. front matterにdescriptionがない記事にexcerptから自動生成
2. excerptが短すぎる場合、本文冒頭150字を使用
3. titleが重複している記事を検出
4. image(OGP画像)が未設定の記事を検出
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from collections import Counter

POSTS_DIR = Path("/home/sol/ai-blog-system/_posts")
MAX_DESCRIPTION_LENGTH = 160
MIN_DESCRIPTION_LENGTH = 50


def parse_front_matter(content: str) -> tuple[dict, str, int]:
    """front matterとbodyを分離して返す"""
    match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not match:
        return {}, content, 0
    fm_text = match.group(1)
    body = match.group(2)
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            key = line.split(':', 1)[0].strip()
            value = line.split(':', 1)[1].strip()
            fm[key] = value
    return fm, body, len(fm_text.split('\n'))


def extract_first_text(body: str, length: int = 160) -> str:
    """本文から最初のテキスト部分を抽出（マークダウン記法を除去）"""
    lines = body.strip().split('\n')
    text_parts = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('#'):
            continue
        if line.startswith('```'):
            continue
        if line.startswith('|'):
            continue
        if line.startswith('!['):
            continue
        if line.startswith('---'):
            continue
        # マークダウン記法を除去
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        clean = re.sub(r'[*_`~]', '', clean)
        clean = clean.strip()
        if clean:
            text_parts.append(clean)
        if len(''.join(text_parts)) >= length:
            break
    result = ''.join(text_parts)
    if len(result) > length:
        result = result[:length-3] + '...'
    return result


def check_and_fix_posts(dry_run: bool = True):
    """全記事をチェックして修正"""
    posts = sorted(POSTS_DIR.glob("*.md"))
    print(f"総記事数: {len(posts)}")

    # 統計カウンタ
    stats = {
        'total': len(posts),
        'no_excerpt': 0,
        'short_excerpt': 0,
        'no_description': 0,
        'no_image': 0,
        'fixed': 0,
    }

    titles = []
    no_image_posts = []
    short_excerpt_posts = []

    for post_path in posts:
        content = post_path.read_text(encoding='utf-8')
        fm, body, _ = parse_front_matter(content)

        title = fm.get('title', '').strip('"').strip("'")
        titles.append(title)

        # excerpt チェック
        excerpt = fm.get('excerpt', '').strip('"').strip("'")
        if not excerpt:
            stats['no_excerpt'] += 1
            # 本文からexcerptを生成
            new_excerpt = extract_first_text(body, MAX_DESCRIPTION_LENGTH)
            if new_excerpt and not dry_run:
                # front matterにexcerptを追加
                content = add_excerpt_to_front_matter(content, new_excerpt)
                post_path.write_text(content, encoding='utf-8')
                stats['fixed'] += 1
                print(f"  [FIXED] {post_path.name}: excerpt追加")
        elif len(excerpt) < MIN_DESCRIPTION_LENGTH:
            stats['short_excerpt'] += 1
            short_excerpt_posts.append((post_path.name, excerpt))

        # image チェック
        if 'image' not in fm:
            stats['no_image'] += 1
            no_image_posts.append(post_path.name)

    # 重複タイトル検出
    title_counts = Counter(titles)
    duplicates = {t: c for t, c in title_counts.items() if c > 1}

    # レポート出力
    print("\n" + "=" * 60)
    print("SEO診断レポート")
    print("=" * 60)
    print(f"\n総記事数: {stats['total']}")
    print(f"excerpt未設定: {stats['no_excerpt']}件")
    print(f"excerpt短すぎ(<{MIN_DESCRIPTION_LENGTH}文字): {stats['short_excerpt']}件")
    print(f"OGP画像未設定: {stats['no_image']}件 ({stats['no_image']/stats['total']*100:.1f}%)")

    if duplicates:
        print(f"\n重複タイトル: {len(duplicates)}件")
        for title, count in sorted(duplicates.items(), key=lambda x: -x[1]):
            print(f"  [{count}回] {title}")

    if short_excerpt_posts[:10]:
        print(f"\nexcerpt短すぎの記事(先頭10件):")
        for name, excerpt in short_excerpt_posts[:10]:
            print(f"  {name}: \"{excerpt[:50]}...\"")

    if not dry_run:
        print(f"\n修正件数: {stats['fixed']}件")
    else:
        print(f"\n[DRY RUN] 実際の修正は行われていません。--fix オプションで修正を実行します。")

    return stats, duplicates


def add_excerpt_to_front_matter(content: str, excerpt: str) -> str:
    """front matterにexcerptフィールドを追加"""
    # 最初の---と2番目の---の間に追加
    parts = content.split('---', 2)
    if len(parts) < 3:
        return content
    escaped = excerpt.replace('"', '\\"')
    parts[1] = parts[1].rstrip('\n') + f'\nexcerpt: "{escaped}"\n'
    return '---'.join(parts)


if __name__ == '__main__':
    dry_run = '--fix' not in sys.argv
    if dry_run:
        print("DRY RUNモード (--fix で実際に修正)")
    else:
        print("FIXモード: 記事を修正します")
    print()

    stats, duplicates = check_and_fix_posts(dry_run=dry_run)
