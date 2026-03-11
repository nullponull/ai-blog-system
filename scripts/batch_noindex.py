#!/usr/bin/env python3
"""
Batch noindex tool: scores all _posts/*.md articles and adds
robots: noindex + sitemap: false to low-quality ones.

Usage:
    python batch_noindex.py --dry-run          # preview only
    python batch_noindex.py                    # apply changes
    python batch_noindex.py --threshold 50     # custom threshold
"""

import argparse
import glob
import os
import re
import sys

# Import QualityScorer from the same scripts directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from quality_scorer import QualityScorer


def parse_front_matter(content):
    """Parse front matter and body from markdown content.
    Returns (front_matter_str, body_str, front_matter_dict_lines) or (None, None, None) if no front matter.
    """
    if not content.startswith('---'):
        return None, content, None
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None, content, None
    return parts[1], parts[2], parts[1].strip().split('\n')


def extract_title(fm_str):
    """Extract title from front matter string."""
    if not fm_str:
        return ""
    for line in fm_str.split('\n'):
        stripped = line.strip()
        if stripped.startswith('title:'):
            title = stripped.replace('title:', '', 1).strip()
            return title.strip('"').strip("'")
    return ""


def has_flag(fm_str, key, value):
    """Check if front matter contains key: value."""
    if not fm_str:
        return False
    pattern = rf'^\s*{re.escape(key)}\s*:\s*{re.escape(value)}\s*$'
    return bool(re.search(pattern, fm_str, re.MULTILINE))


def add_noindex(content, fm_str):
    """Add robots: noindex and sitemap: false to front matter.
    Returns modified content.
    """
    additions = []
    if not has_flag(fm_str, 'robots', 'noindex'):
        additions.append('robots: noindex')
    if not has_flag(fm_str, 'sitemap', 'false'):
        additions.append('sitemap: false')

    if not additions:
        return content  # already has both

    # Insert before the closing ---
    # Content format: ---\n{fm}\n---\n{body}
    parts = content.split('---', 2)
    fm_lines = parts[1].rstrip('\n')
    fm_lines += '\n' + '\n'.join(additions) + '\n'
    return '---' + fm_lines + '---' + parts[2]


def main():
    parser = argparse.ArgumentParser(description='Batch noindex low-quality articles')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be changed without modifying files')
    parser.add_argument('--threshold', type=int, default=40, help='Score threshold for noindexing (default: 40)')
    args = parser.parse_args()

    posts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '_posts')
    files = sorted(glob.glob(os.path.join(posts_dir, '*.md')))

    total = len(files)
    scored = 0
    noindexed = 0
    skipped_already = 0
    skipped_protected = 0
    scores = []
    noindexed_files = []

    print(f"{'[DRY RUN] ' if args.dry_run else ''}Scanning {total} articles (threshold: {args.threshold})")
    print("=" * 70)

    for filepath in files:
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        fm_str, body, _ = parse_front_matter(content)
        if fm_str is None:
            continue

        # Skip protected articles
        if has_flag(fm_str, 'pillar', 'true') or has_flag(fm_str, 'comparison', 'true'):
            skipped_protected += 1
            continue

        # Skip already noindexed
        if has_flag(fm_str, 'robots', 'noindex'):
            skipped_already += 1
            continue

        title = extract_title(fm_str)
        score, details, _ = QualityScorer.score(title, body)
        scored += 1
        scores.append(score)

        if score < args.threshold:
            noindexed += 1
            noindexed_files.append((filename, score))
            if not args.dry_run:
                new_content = add_noindex(content, fm_str)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)

    # Print noindexed files
    if noindexed_files:
        print(f"\n{'Would noindex' if args.dry_run else 'Noindexed'} ({len(noindexed_files)} files):")
        print("-" * 70)
        for fname, s in sorted(noindexed_files, key=lambda x: x[1]):
            print(f"  score={s:3d}  {fname}")

    # Score distribution
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"  Total articles:      {total}")
    print(f"  Already noindexed:   {skipped_already}")
    print(f"  Protected (pillar/comparison): {skipped_protected}")
    print(f"  Scored:              {scored}")
    print(f"  {'Would noindex' if args.dry_run else 'Noindexed'}:       {noindexed}")

    if scores:
        print(f"\nScore distribution (scored articles):")
        brackets = [(0, 20), (20, 40), (40, 60), (60, 80), (80, 101)]
        for low, high in brackets:
            count = sum(1 for s in scores if low <= s < high)
            bar = '#' * count
            label = f"{low:3d}-{high-1:3d}"
            print(f"  {label}: {count:4d}  {bar}")
        avg = sum(scores) / len(scores)
        print(f"\n  Average score: {avg:.1f}")
        print(f"  Min: {min(scores)}  Max: {max(scores)}")


if __name__ == '__main__':
    main()
