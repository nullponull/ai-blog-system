#!/usr/bin/env python3
"""
optimize_titles.py - タイトルを45-58文字に最適化するバッチスクリプト

- 短いタイトル（40文字未満）をSEO最適化された45-58文字に拡張
- 重複タイトルを差別化
- 10件ずつバッチでGemini APIに送信（API効率化）
- --dry-run でプレビュー、--fix で実際に修正
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent))
from gemini_client import GeminiClient

POSTS_DIR = Path("/home/sol/ai-blog-system/_posts")
BATCH_SIZE = 10
MIN_TITLE_LEN = 40
MAX_TITLE_LEN = 58
RATE_LIMIT_SLEEP = 2  # seconds between API calls


def parse_front_matter(content: str) -> tuple[str, str, dict]:
    """Parse front matter and body."""
    match = re.match(r'^(---\n)(.*?)\n(---\n)(.*)', content, re.DOTALL)
    if not match:
        return '', content, {}
    fm_text = match.group(2)
    body = match.group(4)
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            key = line.split(':', 1)[0].strip()
            value = line.split(':', 1)[1].strip()
            fm[key] = value
    return fm_text, body, fm


def get_articles_needing_title_fix():
    """Get articles with short or duplicate titles."""
    posts = sorted(POSTS_DIR.glob("*.md"), reverse=True)  # newest first

    articles = []
    titles = []

    for post_path in posts:
        content = post_path.read_text(encoding='utf-8')
        fm_text, body, fm = parse_front_matter(content)
        title = fm.get('title', '').strip('"').strip("'")
        category = fm.get('categories', '').strip('[]"').split(',')[0].strip().strip('"')
        titles.append(title)

        # Get first 200 chars of body for context
        body_preview = ''
        for line in body.split('\n'):
            stripped = line.strip()
            if stripped and not stripped.startswith('#') and not stripped.startswith('```'):
                clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', stripped)
                clean = re.sub(r'[*_`~]', '', clean)
                body_preview += clean + ' '
                if len(body_preview) > 200:
                    break
        body_preview = body_preview[:200].strip()

        articles.append({
            'path': post_path,
            'title': title,
            'title_len': len(title),
            'category': category,
            'body_preview': body_preview,
        })

    # Find duplicates
    title_counts = Counter(titles)
    duplicates = {t for t, c in title_counts.items() if c > 1}

    # Filter: short titles or duplicates
    needs_fix = []
    for art in articles:
        if art['title_len'] < MIN_TITLE_LEN or art['title'] in duplicates:
            reason = []
            if art['title_len'] < MIN_TITLE_LEN:
                reason.append(f"short({art['title_len']}文字)")
            if art['title'] in duplicates:
                reason.append("duplicate")
            art['reason'] = ', '.join(reason)
            needs_fix.append(art)

    return needs_fix


def optimize_titles_batch(client, batch):
    """Send a batch of titles to Gemini for optimization."""
    items = []
    for i, art in enumerate(batch):
        items.append(
            f"{i+1}. 現タイトル: 「{art['title']}」\n"
            f"   カテゴリ: {art['category']}\n"
            f"   本文冒頭: {art['body_preview'][:150]}"
        )

    schema = {
        "type": "OBJECT",
        "properties": {
            "titles": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "index": {"type": "INTEGER"},
                        "new_title": {"type": "STRING"},
                    },
                    "required": ["index", "new_title"]
                }
            }
        },
        "required": ["titles"]
    }

    prompt = f"""以下の{len(batch)}件の記事タイトルをSEO最適化してください。

【最適化条件】
- 45-58文字（Google検索結果で全文表示される最適長）
- 主要キーワードを前方（最初の20文字以内）に配置
- 数字を含める（「○選」「○つの理由」「○%改善」等）
- 具体的で好奇心を刺激する
- 煽り文句禁止（【衝撃】【速報】等）
- Markdown記号禁止
- 元のタイトルの意味・キーワードを保持しつつ拡張

【記事リスト】
{chr(10).join(items)}

各記事のindex(1始まり)とnew_titleを返してください。"""

    result = client.call_json(prompt, schema=schema)
    if result and 'titles' in result:
        return {item['index']: item['new_title'] for item in result['titles']}
    return {}


def update_title_in_file(post_path, old_title, new_title):
    """Update title in file's front matter."""
    content = post_path.read_text(encoding='utf-8')
    # Replace title line in front matter
    escaped_old = old_title.replace('"', '\\"')
    escaped_new = new_title.replace('"', '\\"')

    # Match title: "..." or title: '...' patterns
    pattern = f'title: "{re.escape(escaped_old)}"'
    replacement = f'title: "{escaped_new}"'

    new_content = content.replace(f'title: "{old_title}"', f'title: "{new_title}"', 1)
    if new_content == content:
        # Try single quotes
        new_content = content.replace(f"title: '{old_title}'", f'title: "{new_title}"', 1)

    if new_content != content:
        post_path.write_text(new_content, encoding='utf-8')
        return True
    return False


def main():
    dry_run = '--fix' not in sys.argv
    limit = None
    for arg in sys.argv:
        if arg.startswith('--limit='):
            limit = int(arg.split('=')[1])

    if dry_run:
        print("DRY RUNモード (--fix で実際に修正)")
    else:
        print("FIXモード: タイトルを修正します")

    # Get articles needing fix
    needs_fix = get_articles_needing_title_fix()
    print(f"\n修正対象: {len(needs_fix)}件")

    if limit:
        needs_fix = needs_fix[:limit]
        print(f"制限: 先頭{limit}件のみ処理")

    if not needs_fix:
        print("修正対象なし")
        return

    # Show preview
    print(f"\n--- 修正対象プレビュー (先頭20件) ---")
    for art in needs_fix[:20]:
        print(f"  [{art['title_len']}文字] [{art['reason']}] {art['title']}")

    if dry_run:
        print(f"\n[DRY RUN] --fix オプションで実際に修正を実行")
        return

    # Initialize Gemini client
    client = GeminiClient()

    # Process in batches
    total_fixed = 0
    total_failed = 0
    batch_num = 0

    for i in range(0, len(needs_fix), BATCH_SIZE):
        batch = needs_fix[i:i + BATCH_SIZE]
        batch_num += 1
        print(f"\n--- バッチ {batch_num} ({i+1}-{i+len(batch)}/{len(needs_fix)}) ---")

        optimized = optimize_titles_batch(client, batch)

        if not optimized:
            print(f"  API失敗、スキップ")
            total_failed += len(batch)
            time.sleep(RATE_LIMIT_SLEEP * 3)
            continue

        for j, art in enumerate(batch):
            idx = j + 1
            if idx in optimized:
                new_title = optimized[idx].strip()
                # Validate
                if len(new_title) < 30 or len(new_title) > 65:
                    print(f"  [{idx}] SKIP (長さ不正 {len(new_title)}文字): {new_title}")
                    total_failed += 1
                    continue

                if update_title_in_file(art['path'], art['title'], new_title):
                    print(f"  [{idx}] {art['title']} → {new_title} ({len(new_title)}文字)")
                    total_fixed += 1
                else:
                    print(f"  [{idx}] FAIL (置換失敗): {art['title']}")
                    total_failed += 1
            else:
                print(f"  [{idx}] SKIP (API未返却): {art['title']}")
                total_failed += 1

        time.sleep(RATE_LIMIT_SLEEP)

    print(f"\n--- 結果 ---")
    print(f"修正成功: {total_fixed}件")
    print(f"失敗/スキップ: {total_failed}件")


if __name__ == '__main__':
    main()
