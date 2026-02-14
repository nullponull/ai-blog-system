#!/usr/bin/env python3
"""重複記事のcanonical設定 + 壊れたタイトル修正"""

import re
import yaml
from pathlib import Path
from collections import defaultdict

POSTS_DIR = Path(__file__).parent.parent / "_posts"


def parse_article(filepath):
    """記事のfrontmatter部分とbody部分、raw contentを返す"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    if not content.startswith("---"):
        return None, "", content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, "", content
    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        return None, parts[2], content
    return fm, parts[2].strip(), content


def get_permalink(filepath, fm):
    """ファイル名とfrontmatterからpermalinkを生成"""
    fname = filepath.stem  # e.g., 2025-09-15-2-aicpo
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})-(.*)', fname)
    if match:
        y, m, d, slug = match.groups()
        return f"/{y}/{m}/{d}/{slug}/"
    return None


def fix_duplicates(dry_run=True):
    """重複記事の短い方にcanonical URLを設定"""
    files = sorted(POSTS_DIR.glob("*.md"))
    title_map = defaultdict(list)

    for fp in files:
        fm, body, raw = parse_article(fp)
        if fm is None:
            continue
        title = fm.get("title", "")
        if not title:
            continue
        body_text = re.sub(r'\s+', '', body)
        title_map[title].append({
            "file": fp,
            "fm": fm,
            "body_len": len(body_text),
            "raw": raw,
        })

    fixed = 0
    for title, entries in title_map.items():
        if len(entries) <= 1:
            continue

        # 本文が長い方をメインに
        entries.sort(key=lambda x: x["body_len"], reverse=True)
        main = entries[0]
        main_permalink = get_permalink(main["file"], main["fm"])

        if not main_permalink:
            continue

        canonical_url = f"https://ai-media.co.jp{main_permalink}"

        for dup in entries[1:]:
            # 既にcanonicalが設定されていればスキップ
            if dup["fm"].get("canonical_url"):
                continue

            raw = dup["raw"]
            # frontmatterのtitle行の後にcanonical_urlを追加
            # frontmatter部分を再構成
            parts = raw.split("---", 2)
            fm_text = parts[1]

            # canonical_url が既にあるか確認
            if "canonical_url:" in fm_text:
                continue

            # titleの行の後にcanonical_urlを挿入
            new_fm = fm_text.rstrip() + f'\ncanonical_url: "{canonical_url}"\n'
            new_content = f"---{new_fm}---{parts[2]}"

            fixed += 1
            if dry_run:
                print(f"[DRY] {dup['file'].name}")
                print(f"  -> canonical: {canonical_url}")
            else:
                with open(dup["file"], "w", encoding="utf-8") as f:
                    f.write(new_content)
                print(f"[FIX] {dup['file'].name} -> {canonical_url}")

    print(f"\n合計: {fixed}件 {'(dry run)' if dry_run else '修正済み'}")


def fix_broken_titles(dry_run=True):
    """壊れたタイトル（'申し訳ありません...'など）を本文から修正"""
    files = sorted(POSTS_DIR.glob("*.md"))
    fixed = 0

    for fp in files:
        fm, body, raw = parse_article(fp)
        if fm is None:
            continue

        title = fm.get("title", "")
        needs_fix = False

        if title.startswith("申し訳ありません"):
            needs_fix = True
        elif title == "の可能性":
            needs_fix = True

        if not needs_fix:
            continue

        # 本文の最初のH1またはH2からタイトルを抽出
        new_title = None
        for line in body.split("\n"):
            line = line.strip()
            m = re.match(r'^#{1,2}\s+(.+)', line)
            if m:
                candidate = m.group(1).strip()
                if len(candidate) > 5 and not candidate.startswith("申し訳"):
                    new_title = candidate
                    break

        if not new_title:
            # 最初の段落からタイトルを生成
            for line in body.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("!") and len(line) > 20:
                    new_title = line[:50].rstrip("。、,.") + "..."
                    break

        if not new_title:
            print(f"[SKIP] {fp.name} - タイトル候補なし")
            continue

        old_title_line = f'title: "{title}"'
        new_title_escaped = new_title.replace('"', '\\"')
        new_title_line = f'title: "{new_title_escaped}"'

        new_content = raw.replace(old_title_line, new_title_line, 1)

        if new_content == raw:
            print(f"[SKIP] {fp.name} - 置換パターン不一致")
            continue

        fixed += 1
        if dry_run:
            print(f"[DRY] {fp.name}")
            print(f"  旧: {title}")
            print(f"  新: {new_title}")
        else:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"[FIX] {fp.name}: {title} -> {new_title}")

    print(f"\n壊れたタイトル: {fixed}件 {'(dry run)' if dry_run else '修正済み'}")


if __name__ == "__main__":
    import sys

    mode = "--fix" if len(sys.argv) > 1 and sys.argv[1] == "--fix" else None
    dry_run = mode != "--fix"

    print("=== 重複記事 canonical 設定 ===")
    fix_duplicates(dry_run=dry_run)

    print("\n=== 壊れたタイトル修正 ===")
    fix_broken_titles(dry_run=dry_run)
