#!/usr/bin/env python3
"""
Batch OGP Image Generator for ai-blog-system.

Scans all _posts/*.md files and generates OGP images for articles
that are missing the `image:` field in their front matter.

This is a convenience wrapper around generate_ogp_image.py for bulk operations.

Usage:
    # Dry run - see how many articles need OGP images
    python3 scripts/generate_ogp_images.py --dry-run

    # Generate all missing OGP images
    python3 scripts/generate_ogp_images.py

    # Generate in batches of 200
    python3 scripts/generate_ogp_images.py --batch-size 200

    # Force regenerate all OGP images
    python3 scripts/generate_ogp_images.py --force

    # Show statistics only
    python3 scripts/generate_ogp_images.py --stats
"""

import os
import sys
import glob
import re
import time
import argparse

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generate_ogp_image import (
    generate_ogp_image,
    extract_frontmatter,
    has_image_field,
    add_image_to_frontmatter,
    get_project_root,
)

def get_stats(posts_dir, project_root):
    """Get statistics about OGP image coverage."""
    files = sorted(glob.glob(os.path.join(posts_dir, '*.md')))

    total = 0
    has_image = 0
    has_ogp_file = 0
    missing = 0
    no_title = 0
    categories = {}

    for filepath in files:
        filename = os.path.basename(filepath)
        match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.md', filename)
        if not match:
            continue

        total += 1
        date_str = match.group(1)
        slug = match.group(2)

        title, category = extract_frontmatter(filepath)
        if not title:
            no_title += 1
            continue

        cat = category or "uncategorized"
        if cat not in categories:
            categories[cat] = {"total": 0, "has_image": 0, "missing": 0}
        categories[cat]["total"] += 1

        image_filename = f'{date_str}-{slug}-ogp.png'
        abs_image_path = os.path.join(project_root, 'assets', 'images', 'posts', image_filename)

        if has_image_field(filepath):
            has_image += 1
            categories[cat]["has_image"] += 1
        elif os.path.exists(abs_image_path):
            has_ogp_file += 1
            categories[cat]["has_image"] += 1
        else:
            missing += 1
            categories[cat]["missing"] += 1

    return {
        "total": total,
        "has_image": has_image,
        "has_ogp_file": has_ogp_file,
        "missing": missing,
        "no_title": no_title,
        "categories": categories,
    }


def print_stats(stats):
    """Print formatted statistics."""
    total = stats["total"]
    covered = stats["has_image"] + stats["has_ogp_file"]
    missing = stats["missing"]
    coverage = (covered / total * 100) if total > 0 else 0

    print("=" * 60)
    print("  OGP Image Coverage Report")
    print("=" * 60)
    print(f"  Total articles:           {total:>6}")
    print(f"  With image (front matter): {stats['has_image']:>5}")
    print(f"  With OGP file (no FM):    {stats['has_ogp_file']:>6}")
    print(f"  Missing OGP:              {missing:>6}")
    print(f"  No title (skipped):       {stats['no_title']:>6}")
    print(f"  Coverage:                 {coverage:>5.1f}%")
    print("-" * 60)

    if stats["categories"]:
        print("\n  Category Breakdown:")
        print(f"  {'Category':<20} {'Total':>6} {'Has OGP':>8} {'Missing':>8} {'Coverage':>9}")
        print(f"  {'-'*20} {'-'*6} {'-'*8} {'-'*8} {'-'*9}")
        for cat, data in sorted(stats["categories"].items(), key=lambda x: -x[1]["missing"]):
            cat_coverage = (data["has_image"] / data["total"] * 100) if data["total"] > 0 else 0
            cat_display = cat[:20] if len(cat) <= 20 else cat[:17] + "..."
            print(f"  {cat_display:<20} {data['total']:>6} {data['has_image']:>8} {data['missing']:>8} {cat_coverage:>8.1f}%")

    print("=" * 60)

    if missing > 0:
        est_seconds = missing * 0.4  # ~0.4s per image with numpy
        est_minutes = est_seconds / 60
        print(f"\n  Estimated time to generate {missing} images: ~{est_minutes:.0f} minutes")
        print(f"  Run: python3 scripts/generate_ogp_images.py")
        print(f"  Or in batches: python3 scripts/generate_ogp_images.py --batch-size 200")


def process_all(posts_dir, project_root, dry_run=False, force=False, batch_size=0):
    """Process all posts and generate missing OGP images."""
    files = sorted(glob.glob(os.path.join(posts_dir, '*.md')))

    if not files:
        print(f"No markdown files found in {posts_dir}")
        return

    generated = 0
    skipped = 0
    already_has_image = 0
    failed = 0
    start_time = time.time()

    for filepath in files:
        filename = os.path.basename(filepath)
        match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.md', filename)
        if not match:
            skipped += 1
            continue

        date_str = match.group(1)
        slug = match.group(2)

        image_filename = f'{date_str}-{slug}-ogp.png'
        relative_image_path = f'assets/images/posts/{image_filename}'
        abs_image_path = os.path.join(project_root, relative_image_path)

        # Skip if front matter already has image field
        if not force and has_image_field(filepath):
            already_has_image += 1
            continue

        # Skip if OGP file already exists
        if not force and os.path.exists(abs_image_path):
            skipped += 1
            continue

        title, category = extract_frontmatter(filepath)
        if not title:
            skipped += 1
            continue

        if dry_run:
            print(f"  [DRY RUN] {image_filename} <- {title[:50]}...")
            generated += 1
            continue

        try:
            if generate_ogp_image(title, category, abs_image_path):
                if not has_image_field(filepath):
                    fm_image_path = f'/{relative_image_path}'
                    add_image_to_frontmatter(filepath, fm_image_path)
                generated += 1

                if generated % 100 == 0:
                    elapsed = time.time() - start_time
                    rate = generated / elapsed if elapsed > 0 else 0
                    remaining = (batch_size - generated if batch_size > 0
                                 else len(files) - generated - skipped - already_has_image)
                    eta = remaining / rate if rate > 0 else 0
                    print(f"  [{generated} done] {rate:.1f} img/sec, ETA: {eta:.0f}s",
                          file=sys.stderr)
            else:
                failed += 1
        except Exception as e:
            print(f"  Error processing {filename}: {e}", file=sys.stderr)
            failed += 1

        if batch_size > 0 and generated >= batch_size:
            print(f"\n  Batch limit reached ({batch_size}). Run again for more.")
            break

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"  Results ({elapsed:.1f}s)")
    print(f"{'='*60}")
    print(f"  Generated:        {generated:>6}")
    print(f"  Already had image: {already_has_image:>5}")
    print(f"  Skipped:          {skipped:>6}")
    print(f"  Failed:           {failed:>6}")

    if generated > 0 and not dry_run:
        rate = generated / elapsed if elapsed > 0 else 0
        print(f"  Speed:            {rate:>5.1f} img/sec")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(
        description='Batch generate OGP images for all blog posts missing them'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview what would be generated without creating files')
    parser.add_argument('--force', action='store_true',
                        help='Regenerate all OGP images (even existing ones)')
    parser.add_argument('--batch-size', type=int, default=0,
                        help='Limit number of images to generate per run (0=unlimited)')
    parser.add_argument('--stats', action='store_true',
                        help='Show OGP coverage statistics only')
    parser.add_argument('--posts-dir', type=str, default=None,
                        help='Path to _posts directory (auto-detected if not specified)')
    args = parser.parse_args()

    project_root = get_project_root()
    posts_dir = args.posts_dir or os.path.join(project_root, '_posts')

    if not os.path.isdir(posts_dir):
        print(f"Error: _posts directory not found at {posts_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Project root: {project_root}")
    print(f"Posts dir: {posts_dir}")

    if args.stats:
        stats = get_stats(posts_dir, project_root)
        print_stats(stats)
        return

    if args.dry_run:
        print("\n--- DRY RUN MODE ---\n")

    # Show stats first
    stats = get_stats(posts_dir, project_root)
    print_stats(stats)

    if stats["missing"] == 0 and not args.force:
        print("\nAll articles already have OGP images!")
        return

    print()
    process_all(posts_dir, project_root,
                dry_run=args.dry_run, force=args.force,
                batch_size=args.batch_size)


if __name__ == '__main__':
    main()
