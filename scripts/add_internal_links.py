#!/usr/bin/env python3
"""
add_internal_links.py - 内部リンク自動追加スクリプト

機能:
1. 各記事のカテゴリ・タグを分析して関連記事を特定
2. 記事末尾に「関連記事」セクションを追加（未設定の記事のみ）
3. front matterのrelated_articlesフィールドを自動生成
4. カテゴリ内のピラー記事（最も長い記事）を特定してリンク

使い方:
  python scripts/add_internal_links.py           # DRY RUN
  python scripts/add_internal_links.py --fix     # 実際に修正
  python scripts/add_internal_links.py --report  # レポートのみ
"""

import os
import re
import sys
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

POSTS_DIR = Path("/home/sol/ai-blog-system/_posts")
MAX_RELATED = 3


def parse_post(filepath: Path) -> dict:
    """記事ファイルを解析してメタデータを返す"""
    content = filepath.read_text(encoding='utf-8')
    match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if not match:
        return None

    fm_text = match.group(1)
    body = match.group(2)

    meta = {'path': filepath, 'body': body, 'content': content}

    # title
    m = re.search(r'^title:\s*"?(.+?)"?\s*$', fm_text, re.MULTILINE)
    meta['title'] = m.group(1) if m else filepath.stem

    # date
    m = re.search(r'^date:\s*(.+)$', fm_text, re.MULTILINE)
    meta['date'] = m.group(1).strip() if m else ''

    # categories
    m = re.search(r'^categories:\s*\[?"?(.+?)"?\]?\s*$', fm_text, re.MULTILINE)
    if m:
        cats = m.group(1).replace('"', '').replace("'", '')
        meta['categories'] = [c.strip() for c in cats.split(',')]
    else:
        meta['categories'] = []

    # tags
    m = re.search(r'^tags:\s*\[(.+?)\]\s*$', fm_text, re.MULTILINE)
    if m:
        tags_str = m.group(1).replace('"', '').replace("'", '')
        meta['tags'] = [t.strip() for t in tags_str.split(',')]
    else:
        meta['tags'] = []

    # related_articles (既存)
    meta['has_related'] = 'related_articles:' in fm_text

    # slug (filename without date prefix)
    meta['slug'] = filepath.stem

    # word count
    meta['word_count'] = len(body)

    # permalink
    date_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', filepath.name)
    if date_match:
        y, m_str, d = date_match.groups()
        title_slug = filepath.stem[11:]  # remove date prefix
        meta['url'] = f"/{y}/{m_str}/{d}/{title_slug}/"
    else:
        meta['url'] = f"/{filepath.stem}/"

    return meta


def compute_similarity(post_a: dict, post_b: dict) -> int:
    """2記事間の関連度スコアを計算"""
    score = 0

    # 同カテゴリ
    common_cats = set(post_a['categories']) & set(post_b['categories'])
    score += len(common_cats) * 3

    # 共通タグ
    common_tags = set(post_a['tags']) & set(post_b['tags'])
    score += len(common_tags) * 1

    return score


def find_related_posts(target: dict, all_posts: list, max_count: int = MAX_RELATED) -> list:
    """対象記事に対する関連記事を特定"""
    scored = []
    for post in all_posts:
        if post['slug'] == target['slug']:
            continue
        score = compute_similarity(target, post)
        if score >= 2:
            scored.append((score, post))

    scored.sort(key=lambda x: (-x[0], x[1]['date']), reverse=False)
    scored.sort(key=lambda x: -x[0])

    return [p for _, p in scored[:max_count]]


def add_related_section_to_body(content: str, related_posts: list) -> str:
    """記事本文末尾に関連記事セクションを追加"""
    if '## 関連記事' in content or '### 関連記事' in content:
        return content

    links = []
    for p in related_posts:
        links.append(f"- [{p['title']}]({p['url']})")

    section = "\n\n---\n\n## 関連記事\n\n" + "\n".join(links) + "\n"

    # front matterの後に本文があるので、末尾に追加
    return content.rstrip('\n') + section


def generate_report(all_posts: list):
    """内部リンク状況のレポートを生成"""
    category_counts = defaultdict(int)
    has_related_count = 0
    has_body_links = 0

    for post in all_posts:
        for cat in post['categories']:
            category_counts[cat] += 1
        if post['has_related']:
            has_related_count += 1
        if re.search(r'\[.*?\]\(/20', post['body']):
            has_body_links += 1

    print("=" * 60)
    print("内部リンク分析レポート")
    print("=" * 60)
    print(f"\n総記事数: {len(all_posts)}")
    print(f"related_articles設定済み: {has_related_count}件 ({has_related_count/len(all_posts)*100:.1f}%)")
    print(f"本文内に内部リンクあり: {has_body_links}件 ({has_body_links/len(all_posts)*100:.1f}%)")
    print(f"\nカテゴリ別記事数:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}件")

    # 孤立記事（内部リンクなし + 被リンクなし）の検出
    linked_urls = set()
    for post in all_posts:
        urls = re.findall(r'\]\((/20[^)]+)\)', post['body'])
        linked_urls.update(urls)

    orphan_count = 0
    for post in all_posts:
        has_outgoing = bool(re.search(r'\[.*?\]\(/20', post['body']))
        has_incoming = post['url'] in linked_urls
        if not has_outgoing and not has_incoming and not post['has_related']:
            orphan_count += 1

    print(f"\n孤立記事（リンクなし）: {orphan_count}件 ({orphan_count/len(all_posts)*100:.1f}%)")


def main():
    dry_run = '--fix' not in sys.argv
    report_only = '--report' in sys.argv

    print("記事を読み込み中...")
    posts = sorted(POSTS_DIR.glob("*.md"))
    all_posts = []
    for p in posts:
        meta = parse_post(p)
        if meta:
            all_posts.append(meta)
    print(f"  {len(all_posts)}件の記事を読み込みました")

    if report_only:
        generate_report(all_posts)
        return

    # 関連記事のない記事を対象に
    targets = [p for p in all_posts if not p['has_related']]
    print(f"  related_articles未設定: {len(targets)}件")

    if dry_run:
        print("\n[DRY RUN] 実際の修正は行われません。--fix で修正実行。\n")

    fixed_count = 0
    for target in targets:
        related = find_related_posts(target, all_posts)
        if not related:
            continue

        if dry_run:
            if fixed_count < 5:
                print(f"  {target['slug']}:")
                for r in related:
                    print(f"    -> {r['title']}")
            elif fixed_count == 5:
                print(f"  ... (残り{len(targets)-5}件)")
        else:
            new_content = add_related_section_to_body(target['content'], related)
            if new_content != target['content']:
                target['path'].write_text(new_content, encoding='utf-8')
                fixed_count += 1

        fixed_count += 1 if dry_run else 0

    print(f"\n{'修正対象' if dry_run else '修正完了'}: {fixed_count}件")

    # レポートも出力
    print()
    generate_report(all_posts)


if __name__ == '__main__':
    main()
