#!/usr/bin/env python3
"""記事品質改善スクリプト - 定型excerpt修正・重複記事対応"""

import os
import re
import yaml
from pathlib import Path

POSTS_DIR = Path(__file__).parent.parent / "_posts"

GENERIC_EXCERPTS = [
    "最新のAI技術動向と市場分析をお届けします。",
    "最新のAI技術動向と市場分析をお届けします",
]


def extract_excerpt_from_body(body, max_len=160):
    """本文から最初の意味のある段落を抽出してexcerptにする"""
    lines = body.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("!["):
            continue
        if line.startswith("{%"):
            continue
        if line.startswith("|"):
            continue
        if line.startswith("-") and len(line) < 30:
            continue

        # マークダウンリンク除去
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        # 太字・斜体除去
        clean = re.sub(r'[*_`]', '', clean)
        clean = clean.strip()

        if len(clean) > 30:
            if len(clean) > max_len:
                # 文の区切りで切る
                sentences = re.split(r'[。！？]', clean)
                result = ""
                for s in sentences:
                    if len(result + s) > max_len:
                        break
                    result += s + "。"
                return result.rstrip("。") + "。" if result else clean[:max_len]
            return clean

    return None


def fix_generic_excerpts(dry_run=True):
    """定型excerptを本文から抽出した内容に置換"""
    files = sorted(POSTS_DIR.glob("*.md"))
    fixed_count = 0

    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.startswith("---"):
            continue

        parts = content.split("---", 2)
        if len(parts) < 3:
            continue

        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            continue

        if fm is None:
            continue

        excerpt = fm.get("excerpt", "")
        if excerpt.strip() not in GENERIC_EXCERPTS:
            continue

        body = parts[2].strip()
        new_excerpt = extract_excerpt_from_body(body)

        if not new_excerpt:
            continue

        # YAML内のexcerptを置換
        old_excerpt_line = f'excerpt: "{excerpt}"'
        new_excerpt_escaped = new_excerpt.replace('"', '\\"')
        new_excerpt_line = f'excerpt: "{new_excerpt_escaped}"'

        new_content = content.replace(old_excerpt_line, new_excerpt_line, 1)

        if new_content == content:
            # シングルクォートやその他のフォーマットを試す
            old_excerpt_line2 = f"excerpt: '{excerpt}'"
            new_excerpt_line2 = f'excerpt: "{new_excerpt_escaped}"'
            new_content = content.replace(old_excerpt_line2, new_excerpt_line2, 1)

        if new_content != content:
            fixed_count += 1
            if dry_run:
                print(f"[DRY] {fp.name}")
                print(f"  旧: {excerpt[:60]}...")
                print(f"  新: {new_excerpt[:60]}...")
            else:
                with open(fp, "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"[FIX] {fp.name} -> {new_excerpt[:50]}...")

    print(f"\n合計: {fixed_count}件 {'(dry run)' if dry_run else '修正済み'}")
    return fixed_count


def find_duplicates():
    """重複タイトルの記事ペアを特定し、古い方にcanonicalを設定"""
    from collections import defaultdict

    files = sorted(POSTS_DIR.glob("*.md"))
    title_map = defaultdict(list)

    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            continue
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            continue
        if fm is None:
            continue

        title = fm.get("title", "")
        body = parts[2].strip()
        body_len = len(re.sub(r'\s+', '', body))
        title_map[title].append({
            "file": fp,
            "date": fm.get("date", ""),
            "body_len": body_len,
        })

    duplicates = []
    for title, entries in title_map.items():
        if len(entries) > 1:
            # 本文が長い方をメイン記事とする
            entries.sort(key=lambda x: x["body_len"], reverse=True)
            duplicates.append({
                "title": title,
                "keep": entries[0],
                "remove": entries[1:],
            })

    return duplicates


def report_duplicates():
    """重複記事のレポート"""
    duplicates = find_duplicates()
    print(f"\n重複タイトル: {len(duplicates)}セット")
    for dup in duplicates:
        print(f"\n  [{dup['title']}]")
        print(f"    保持 ({dup['keep']['body_len']}文字): {dup['keep']['file'].name}")
        for rm in dup["remove"]:
            print(f"    重複 ({rm['body_len']}文字): {rm['file'].name}")
    return duplicates


def fix_broken_titles():
    """タイトルが「申し訳ありませんが」「の可能性とは？」のみの壊れた記事を特定"""
    files = sorted(POSTS_DIR.glob("*.md"))
    broken = []

    broken_patterns = [
        r'^申し訳ありません',
        r'^の可能性$',
        r'^AI記事の更新$',
    ]

    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.startswith("---"):
            continue
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        try:
            fm = yaml.safe_load(parts[1])
        except yaml.YAMLError:
            continue
        if fm is None:
            continue

        title = fm.get("title", "")
        for pattern in broken_patterns:
            if re.search(pattern, title):
                body = parts[2].strip()
                body_len = len(re.sub(r'\s+', '', body))
                broken.append({
                    "file": fp.name,
                    "title": title,
                    "body_len": body_len,
                })
                break

    print(f"\n壊れたタイトルの記事: {len(broken)}件")
    for b in broken:
        print(f"  {b['title']} ({b['body_len']}文字) - {b['file']}")
    return broken


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--fix":
        print("=== 定型excerpt修正 (実行モード) ===")
        fix_generic_excerpts(dry_run=False)
    else:
        print("=== 定型excerpt修正 (dry run) ===")
        fix_generic_excerpts(dry_run=True)

    print("\n=== 重複記事チェック ===")
    report_duplicates()

    print("\n=== 壊れたタイトルチェック ===")
    fix_broken_titles()
