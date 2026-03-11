#!/usr/bin/env python3
"""
fix_seo_meta.py - SEO meta description自動修正スクリプト

機能:
1. front matterにdescriptionがない記事に本文から自動生成
2. excerptがない記事に本文から自動生成
3. titleが短い記事を検出（50文字未満）
4. titleが重複している記事を検出
5. image(OGP画像)が未設定の記事を検出
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
IDEAL_TITLE_MIN = 40
IDEAL_TITLE_MAX = 60


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
        if line.startswith('{%'):
            continue
        if line.startswith('- ') or line.startswith('* '):
            continue
        # マークダウン記法を除去
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        clean = re.sub(r'[*_`~]', '', clean)
        clean = clean.strip()
        if clean and len(clean) > 20:
            text_parts.append(clean)
        if len(''.join(text_parts)) >= length:
            break
    result = ''.join(text_parts)
    if len(result) > length:
        # 文末で切る（句読点の後）
        cut = result[:length]
        last_period = max(cut.rfind('。'), cut.rfind('。'), cut.rfind('．'))
        if last_period > length // 2:
            result = cut[:last_period + 1]
        else:
            result = cut[:length - 3] + '...'
    return result


def add_field_to_front_matter(content: str, field: str, value: str) -> str:
    """front matterにフィールドを追加"""
    parts = content.split('---', 2)
    if len(parts) < 3:
        return content
    escaped = value.replace('"', '\\"')
    parts[1] = parts[1].rstrip('\n') + f'\n{field}: "{escaped}"\n'
    return '---'.join(parts)


def check_and_fix_posts(dry_run: bool = True):
    """全記事をチェックして修正"""
    posts = sorted(POSTS_DIR.glob("*.md"))
    print(f"総記事数: {len(posts)}")

    stats = {
        'total': len(posts),
        'no_description': 0,
        'no_excerpt': 0,
        'short_excerpt': 0,
        'no_image': 0,
        'short_title': 0,
        'fixed_description': 0,
        'fixed_excerpt': 0,
    }

    titles = []
    short_title_posts = []
    no_image_posts = []

    for post_path in posts:
        content = post_path.read_text(encoding='utf-8')
        fm, body, _ = parse_front_matter(content)
        modified = False

        title = fm.get('title', '').strip('"').strip("'")
        titles.append(title)

        # タイトル文字数チェック
        if title and len(title) < IDEAL_TITLE_MIN:
            stats['short_title'] += 1
            if len(short_title_posts) < 20:
                short_title_posts.append((post_path.name, title, len(title)))

        # description チェック
        description = fm.get('description', '').strip('"').strip("'")
        if not description:
            stats['no_description'] += 1
            new_desc = extract_first_text(body, MAX_DESCRIPTION_LENGTH)
            if new_desc and not dry_run:
                content = add_field_to_front_matter(content, 'description', new_desc)
                modified = True
                stats['fixed_description'] += 1

        # excerpt チェック
        excerpt = fm.get('excerpt', '').strip('"').strip("'")
        if not excerpt:
            stats['no_excerpt'] += 1
            new_excerpt = extract_first_text(body, 120)
            if new_excerpt and not dry_run:
                content = add_field_to_front_matter(content, 'excerpt', new_excerpt)
                modified = True
                stats['fixed_excerpt'] += 1
        elif len(excerpt) < MIN_DESCRIPTION_LENGTH:
            stats['short_excerpt'] += 1

        # image チェック
        if 'image' not in fm:
            stats['no_image'] += 1
            if len(no_image_posts) < 10:
                no_image_posts.append(post_path.name)

        # 書き込み
        if modified:
            post_path.write_text(content, encoding='utf-8')

    # 重複タイトル検出
    title_counts = Counter(titles)
    duplicates = {t: c for t, c in title_counts.items() if c > 1}

    # レポート出力
    print("\n" + "=" * 60)
    print("SEO診断レポート")
    print("=" * 60)
    print(f"\n総記事数: {stats['total']}")
    print(f"\n--- メタデータ ---")
    print(f"description未設定: {stats['no_description']}件 ({stats['no_description']/stats['total']*100:.1f}%)")
    print(f"excerpt未設定: {stats['no_excerpt']}件 ({stats['no_excerpt']/stats['total']*100:.1f}%)")
    print(f"excerpt短すぎ(<{MIN_DESCRIPTION_LENGTH}文字): {stats['short_excerpt']}件")
    print(f"OGP画像未設定: {stats['no_image']}件 ({stats['no_image']/stats['total']*100:.1f}%)")

    print(f"\n--- タイトル ---")
    print(f"短いタイトル(<{IDEAL_TITLE_MIN}文字): {stats['short_title']}件 ({stats['short_title']/stats['total']*100:.1f}%)")

    if short_title_posts[:10]:
        print(f"\n短いタイトルの記事(先頭10件):")
        for name, title, length in short_title_posts[:10]:
            print(f"  [{length}文字] {name}: \"{title}\"")

    if duplicates:
        print(f"\n重複タイトル: {len(duplicates)}件")
        for title, count in sorted(duplicates.items(), key=lambda x: -x[1])[:10]:
            print(f"  [{count}回] {title}")

    if no_image_posts:
        print(f"\nOGP画像未設定(先頭10件):")
        for name in no_image_posts[:10]:
            print(f"  {name}")

    if not dry_run:
        print(f"\n--- 修正結果 ---")
        print(f"description追加: {stats['fixed_description']}件")
        print(f"excerpt追加: {stats['fixed_excerpt']}件")
    else:
        print(f"\n[DRY RUN] 実際の修正は行われていません。--fix オプションで修正を実行します。")

    return stats, duplicates


if __name__ == '__main__':
    dry_run = '--fix' not in sys.argv
    if dry_run:
        print("DRY RUNモード (--fix で実際に修正)")
    else:
        print("FIXモード: 記事を修正します")
    print()

    stats, duplicates = check_and_fix_posts(dry_run=dry_run)
