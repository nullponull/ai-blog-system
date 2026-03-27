#!/usr/bin/env python3
"""
fill_briefs.py - Claude CLI生成のブリーフでpSEOページを更新

local_context と challenge_summary を front matter に埋め込む。
ブリーフデータは briefs.json から読み込む。

Usage:
  python3 scripts/fill_briefs.py                    # 全ページ更新
  python3 scripts/fill_briefs.py --dry-run           # プレビュー
"""

import argparse
import json
import re
from pathlib import Path

PROJECT_ROOT = Path("/home/sol/ai-blog-system")
PAGES_DIR = PROJECT_ROOT / "_pages" / "ai-solutions"
BRIEFS_FILE = PROJECT_ROOT / "_data" / "pseo" / "briefs.json"


def update_frontmatter(filepath: Path, local_context: str, challenge_summary: str) -> bool:
    """Update local_context and challenge_summary in front matter."""
    content = filepath.read_text(encoding="utf-8")

    # Replace local_context
    content = re.sub(
        r'^local_context: ".*"$',
        f'local_context: "{local_context}"',
        content,
        flags=re.MULTILINE,
    )

    # Replace challenge_summary
    content = re.sub(
        r'^challenge_summary: ".*"$',
        f'challenge_summary: "{challenge_summary}"',
        content,
        flags=re.MULTILINE,
    )

    filepath.write_text(content, encoding="utf-8")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not BRIEFS_FILE.exists():
        print(f"ERROR: {BRIEFS_FILE} not found. Generate it first.")
        return

    with open(BRIEFS_FILE, encoding="utf-8") as f:
        briefs = json.load(f)

    updated = 0
    skipped = 0

    for key, brief in briefs.items():
        industry_id, pref_id = key.split("/")
        filepath = PAGES_DIR / industry_id / f"{pref_id}.md"

        if not filepath.exists():
            print(f"  SKIP (not found): {filepath}")
            skipped += 1
            continue

        # Check if already has content
        content = filepath.read_text(encoding="utf-8")
        if 'local_context: ""' not in content and 'challenge_summary: ""' not in content:
            # Already filled
            skipped += 1
            continue

        local_ctx = brief.get("local_context", "")
        challenge = brief.get("challenge_summary", "")

        if args.dry_run:
            print(f"  [DRY RUN] {key}")
            print(f"    local: {local_ctx[:60]}...")
            print(f"    challenge: {challenge[:60]}...")
        else:
            update_frontmatter(filepath, local_ctx, challenge)
            print(f"  UPDATED: {key}")

        updated += 1

    print(f"\n--- 結果 ---")
    print(f"更新: {updated}ページ, スキップ: {skipped}ページ")


if __name__ == "__main__":
    main()
