#!/usr/bin/env python3
"""
Generate OGP images (1200x630) for blog posts using Pillow.

Creates category-themed template images with article titles.
No external font files required - uses built-in default font with scaling.

Usage:
    python3 scripts/generate_ogp_image.py _posts/          # Process all posts
    python3 scripts/generate_ogp_image.py _posts/2026-02-12-example.md  # Single post
    python3 scripts/generate_ogp_image.py _posts/ --dry-run # Preview only
"""

import os
import sys
import glob
import re
import argparse
import textwrap

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required: pip install Pillow", file=sys.stderr)
    sys.exit(1)

# OGP image dimensions
WIDTH = 1200
HEIGHT = 630

# Category color themes: (gradient_start, gradient_end, accent)
CATEGORY_THEMES = {
    "AI最新ニュース": ((26, 54, 93), (13, 148, 136), (230, 255, 250)),
    "AI技術ガイド": ((13, 148, 136), (10, 122, 112), (230, 255, 250)),
    "AI導入戦略": ((26, 54, 93), (21, 48, 82), (200, 220, 255)),
    "業界別AI活用": ((13, 148, 136), (26, 54, 93), (230, 255, 250)),
    "導入事例": ((26, 54, 93), (13, 148, 136), (255, 255, 255)),
    "研究論文": ((21, 48, 82), (13, 71, 68), (200, 230, 255)),
}

DEFAULT_THEME = ((26, 54, 93), (13, 148, 136), (230, 255, 250))


def create_gradient(draw, width, height, color_start, color_end):
    """Create a diagonal gradient background."""
    for y in range(height):
        for x in range(width):
            # Diagonal blend factor
            factor = (x / width * 0.6 + y / height * 0.4)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * factor)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * factor)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * factor)
            draw.point((x, y), fill=(r, g, b))


def create_gradient_fast(width, height, color_start, color_end):
    """Create gradient using numpy-free approach with horizontal bands."""
    img = Image.new('RGB', (width, height))
    for y in range(height):
        factor = y / height
        r = int(color_start[0] + (color_end[0] - color_start[0]) * factor)
        g = int(color_start[1] + (color_end[1] - color_start[1]) * factor)
        b = int(color_start[2] + (color_end[2] - color_start[2]) * factor)
        for x in range(width):
            # Add slight horizontal variation
            hf = x / width * 0.15
            rr = min(255, max(0, int(r + (color_end[0] - color_start[0]) * hf)))
            gg = min(255, max(0, int(g + (color_end[1] - color_start[1]) * hf)))
            bb = min(255, max(0, int(b + (color_end[2] - color_start[2]) * hf)))
            img.putpixel((x, y), (rr, gg, bb))
    return img


def wrap_text(text, max_chars_per_line=18):
    """Wrap Japanese text to fit within image width."""
    lines = []
    current_line = ""
    for char in text:
        current_line += char
        if len(current_line) >= max_chars_per_line:
            lines.append(current_line)
            current_line = ""
    if current_line:
        lines.append(current_line)
    return lines[:4]  # Max 4 lines


def get_font(size):
    """Get the best available font."""
    # Try common Japanese font paths
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Fallback to default
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def generate_ogp_image(title, category, output_path):
    """Generate an OGP image for a blog post."""
    theme = CATEGORY_THEMES.get(category, DEFAULT_THEME)
    color_start, color_end, text_color = theme

    # Create image with gradient
    img = create_gradient_fast(WIDTH, HEIGHT, color_start, color_end)
    draw = ImageDraw.Draw(img)

    # Draw decorative elements
    # Top-left accent circle
    draw.ellipse([(-50, -50), (150, 150)], fill=(*text_color, 30) if len(text_color) == 3 else text_color, outline=None)
    # Bottom-right accent
    draw.ellipse([(WIDTH - 200, HEIGHT - 200), (WIDTH + 50, HEIGHT + 50)], fill=(*text_color, 20) if len(text_color) == 3 else text_color, outline=None)

    # Draw category label
    small_font = get_font(24)
    category_text = category if category else "AIコンパス"
    draw.text((80, 60), category_text, fill=text_color, font=small_font)

    # Draw accent line under category
    draw.rectangle([(80, 95), (80 + len(category_text) * 24, 98)], fill=text_color)

    # Draw title
    title_font = get_font(48)
    title_lines = wrap_text(title, 20)

    y_start = 140
    line_height = 65
    for i, line in enumerate(title_lines):
        draw.text((80, y_start + i * line_height), line, fill=(255, 255, 255), font=title_font)

    # Draw site name at bottom
    site_font = get_font(20)
    draw.text((80, HEIGHT - 80), "AIコンパス by ALLFORCES", fill=(*text_color[:3],), font=site_font)

    # Draw bottom accent line
    draw.rectangle([(80, HEIGHT - 90), (WIDTH - 80, HEIGHT - 87)], fill=(*text_color[:3],))

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    return True


def extract_frontmatter(filepath):
    """Extract title and category from a post's frontmatter."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if not content.startswith('---'):
            return None, None

        parts = content.split('---', 2)
        if len(parts) < 3:
            return None, None

        fm = parts[1]
        title = None
        category = None

        for line in fm.split('\n'):
            if line.startswith('title:'):
                title = line.replace('title:', '').strip().strip('"').strip("'")
            elif line.startswith('categories:'):
                raw = line.replace('categories:', '').strip().strip('[]')
                cats = [c.strip().strip('"').strip("'") for c in raw.split(',')]
                category = cats[0] if cats else None

        return title, category
    except Exception:
        return None, None


def has_image_field(filepath):
    """Check if post already has an image field in frontmatter."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        parts = content.split('---', 2)
        if len(parts) >= 3:
            return 'image:' in parts[1]
        return False
    except Exception:
        return False


def add_image_to_frontmatter(filepath, image_path):
    """Add image field to post frontmatter."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        lines = content.split('\n')
        fm_end = -1
        fm_count = 0
        for i, line in enumerate(lines):
            if line.strip() == '---':
                fm_count += 1
                if fm_count == 2:
                    fm_end = i
                    break

        if fm_end > 0:
            lines.insert(fm_end, f'image: "{image_path}"')
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            return True
        return False
    except Exception:
        return False


def process_posts(path, dry_run=False, force=False):
    """Process posts to generate OGP images."""
    if os.path.isfile(path):
        files = [path]
    else:
        files = sorted(glob.glob(os.path.join(path, '*.md')))

    if not files:
        print(f'No markdown files found in {path}')
        return

    generated = 0
    skipped = 0

    for filepath in files:
        filename = os.path.basename(filepath)
        # Extract date and slug from filename: YYYY-MM-DD-slug.md
        match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.md', filename)
        if not match:
            skipped += 1
            continue

        date_str = match.group(1)
        slug = match.group(2)

        # Check if image already exists
        image_filename = f'{date_str}-{slug}-ogp.png'
        image_path = f'assets/images/posts/{image_filename}'

        if not force and os.path.exists(image_path):
            skipped += 1
            continue

        title, category = extract_frontmatter(filepath)
        if not title:
            skipped += 1
            continue

        if dry_run:
            print(f'  [DRY RUN] Would generate: {image_path} ({category}: {title[:30]}...)')
            generated += 1
            continue

        if generate_ogp_image(title, category, image_path):
            # Add image field to frontmatter if not present
            if not has_image_field(filepath):
                relative_image_path = f'/{image_path}'
                add_image_to_frontmatter(filepath, relative_image_path)
            print(f'  Generated: {image_filename}')
            generated += 1
        else:
            print(f'  Failed: {image_filename}')
            skipped += 1

    print(f'\nDone. Generated: {generated}, Skipped: {skipped}')


def main():
    parser = argparse.ArgumentParser(
        description='Generate OGP images for blog posts'
    )
    parser.add_argument('path', help='Path to _posts/ directory or single .md file')
    parser.add_argument('--dry-run', action='store_true', help='Preview without generating')
    parser.add_argument('--force', action='store_true', help='Regenerate existing images')
    args = parser.parse_args()

    process_posts(args.path, dry_run=args.dry_run, force=args.force)


if __name__ == '__main__':
    main()
