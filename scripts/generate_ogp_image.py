#!/usr/bin/env python3
"""
Generate OGP images (1200x630) for blog posts using Pillow + numpy.

Creates category-themed template images with article titles.
Uses Noto Sans CJK JP font for proper Japanese rendering.

Usage:
    python3 scripts/generate_ogp_image.py _posts/          # Process all posts
    python3 scripts/generate_ogp_image.py _posts/2026-02-12-example.md  # Single post
    python3 scripts/generate_ogp_image.py _posts/ --dry-run # Preview only
    python3 scripts/generate_ogp_image.py _posts/ --force   # Regenerate existing
    python3 scripts/generate_ogp_image.py _posts/ --batch-size 100  # Process in batches
"""

import os
import sys
import glob
import re
import argparse
import time

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("Pillow is required: pip install Pillow", file=sys.stderr)
    sys.exit(1)

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

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

# Font cache to avoid repeated filesystem lookups
_font_cache = {}

# Font search paths (ordered by preference)
FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/google-noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]

# Resolved font path (cached at module level)
_resolved_font_path = None


def _find_font_path():
    """Find the best available font path (cached)."""
    global _resolved_font_path
    if _resolved_font_path is not None:
        return _resolved_font_path
    for path in FONT_PATHS:
        if os.path.exists(path):
            _resolved_font_path = path
            return path
    _resolved_font_path = ""
    return ""


def get_font(size):
    """Get the best available font (with caching)."""
    if size in _font_cache:
        return _font_cache[size]

    font_path = _find_font_path()
    font = None
    if font_path:
        try:
            font = ImageFont.truetype(font_path, size)
        except Exception:
            pass
    if font is None:
        font = ImageFont.load_default()

    _font_cache[size] = font
    return font


def create_gradient_numpy(width, height, color_start, color_end):
    """Create gradient using numpy (fast vectorized approach)."""
    # Create vertical gradient factor [0..1]
    y_factor = np.linspace(0, 1, height, dtype=np.float32).reshape(height, 1)
    # Add slight horizontal variation
    x_factor = np.linspace(0, 0.15, width, dtype=np.float32).reshape(1, width)

    # Combined factor
    factor = y_factor + x_factor  # shape: (height, width)

    # Create RGB channels
    img_array = np.zeros((height, width, 3), dtype=np.uint8)
    for c in range(3):
        channel = color_start[c] + (color_end[c] - color_start[c]) * factor
        img_array[:, :, c] = np.clip(channel, 0, 255).astype(np.uint8)

    return Image.fromarray(img_array, 'RGB')


def create_gradient_fallback(width, height, color_start, color_end):
    """Create gradient without numpy (slower but no dependencies)."""
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    for y in range(height):
        factor_y = y / height
        for x in range(width):
            factor = factor_y + (x / width * 0.15)
            r = min(255, max(0, int(color_start[0] + (color_end[0] - color_start[0]) * factor)))
            g = min(255, max(0, int(color_start[1] + (color_end[1] - color_start[1]) * factor)))
            b = min(255, max(0, int(color_start[2] + (color_end[2] - color_start[2]) * factor)))
            pixels[x, y] = (r, g, b)
    return img


def create_gradient(width, height, color_start, color_end):
    """Create gradient using the best available method."""
    if HAS_NUMPY:
        return create_gradient_numpy(width, height, color_start, color_end)
    return create_gradient_fallback(width, height, color_start, color_end)


def wrap_text_smart(text, font, max_width, draw):
    """Wrap text intelligently using actual font metrics."""
    if not text:
        return [""]

    lines = []
    current_line = ""

    for char in text:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width > max_width and current_line:
            lines.append(current_line)
            current_line = char
        else:
            current_line = test_line

    if current_line:
        lines.append(current_line)

    return lines[:4]  # Max 4 lines


def generate_ogp_image(title, category, output_path):
    """Generate an OGP image for a blog post."""
    theme = CATEGORY_THEMES.get(category, DEFAULT_THEME)
    color_start, color_end, text_color = theme

    # Create image with gradient
    img = create_gradient(WIDTH, HEIGHT, color_start, color_end)
    draw = ImageDraw.Draw(img)

    # Draw decorative elements - semi-transparent circles
    overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    overlay_draw.ellipse(
        [(-50, -50), (150, 150)],
        fill=(*text_color, 25)
    )
    overlay_draw.ellipse(
        [(WIDTH - 200, HEIGHT - 200), (WIDTH + 50, HEIGHT + 50)],
        fill=(*text_color, 18)
    )
    # Additional subtle accent
    overlay_draw.ellipse(
        [(WIDTH - 400, -100), (WIDTH - 100, 200)],
        fill=(*text_color, 12)
    )
    img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
    draw = ImageDraw.Draw(img)

    # Draw category label
    small_font = get_font(24)
    category_text = category if category else "AIコンパス"

    # Category pill background
    cat_bbox = draw.textbbox((0, 0), category_text, font=small_font)
    cat_width = cat_bbox[2] - cat_bbox[0]
    cat_height = cat_bbox[3] - cat_bbox[1]
    pill_x, pill_y = 80, 55
    pill_padding_x, pill_padding_y = 16, 8
    draw.rounded_rectangle(
        [(pill_x, pill_y),
         (pill_x + cat_width + pill_padding_x * 2, pill_y + cat_height + pill_padding_y * 2)],
        radius=6,
        fill=(*text_color[:3], ),
    )
    # Category text (dark on light pill)
    draw.text(
        (pill_x + pill_padding_x, pill_y + pill_padding_y),
        category_text,
        fill=color_start,
        font=small_font,
    )

    # Draw title with smart wrapping
    title_font = get_font(46)
    max_text_width = WIDTH - 160  # 80px padding on each side
    title_lines = wrap_text_smart(title, title_font, max_text_width, draw)

    y_start = 135
    line_height = 64
    for i, line in enumerate(title_lines):
        draw.text((80, y_start + i * line_height), line, fill=(255, 255, 255), font=title_font)

    # Draw bottom separator line
    draw.rectangle([(80, HEIGHT - 95), (WIDTH - 80, HEIGHT - 92)], fill=(*text_color[:3],))

    # Draw site name at bottom
    site_font = get_font(22)
    draw.text((80, HEIGHT - 75), "AIコンパス by ALLFORCES", fill=(*text_color[:3],), font=site_font)

    # Draw subtle AI icon (circuit-like pattern) at bottom right
    icon_font = get_font(16)
    draw.text((WIDTH - 200, HEIGHT - 75), "ai-media.co.jp", fill=(*text_color[:3],), font=icon_font)

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path, "PNG", optimize=True)
    return True


def extract_frontmatter(filepath):
    """Extract title and category from a post's frontmatter."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(3000)  # Only read front matter area

        if not content.startswith('---'):
            return None, None

        end_idx = content.find('---', 3)
        if end_idx == -1:
            return None, None

        fm = content[3:end_idx]
        title = None
        category = None

        for line in fm.split('\n'):
            line_stripped = line.strip()
            if line_stripped.startswith('title:'):
                title = line_stripped.replace('title:', '', 1).strip().strip('"').strip("'")
            elif line_stripped.startswith('categories:'):
                raw = line_stripped.replace('categories:', '', 1).strip().strip('[]')
                cats = [c.strip().strip('"').strip("'") for c in raw.split(',')]
                category = cats[0] if cats else None

        return title, category
    except Exception:
        return None, None


def has_image_field(filepath):
    """Check if post already has an image field in frontmatter."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(3000)
        if not content.startswith('---'):
            return False
        end_idx = content.find('---', 3)
        if end_idx == -1:
            return False
        return 'image:' in content[3:end_idx]
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


def get_project_root():
    """Get the ai-blog-system project root directory."""
    # Try to find _posts directory relative to script or cwd
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    if os.path.isdir(os.path.join(project_root, '_posts')):
        return project_root
    # Fallback to cwd
    if os.path.isdir(os.path.join(os.getcwd(), '_posts')):
        return os.getcwd()
    return project_root


def process_posts(path, dry_run=False, force=False, batch_size=0):
    """Process posts to generate OGP images."""
    project_root = get_project_root()

    if os.path.isfile(path):
        files = [path]
    else:
        files = sorted(glob.glob(os.path.join(path, '*.md')))

    if not files:
        print(f'No markdown files found in {path}')
        return

    generated = 0
    skipped = 0
    already_has_image = 0
    failed = 0
    start_time = time.time()

    for filepath in files:
        filename = os.path.basename(filepath)
        # Extract date and slug from filename: YYYY-MM-DD-slug.md
        match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.md', filename)
        if not match:
            skipped += 1
            continue

        date_str = match.group(1)
        slug = match.group(2)

        # Image paths (use absolute path for existence check)
        image_filename = f'{date_str}-{slug}-ogp.png'
        relative_image_path = f'assets/images/posts/{image_filename}'
        abs_image_path = os.path.join(project_root, relative_image_path)

        # Skip if image exists and not forcing
        if not force and os.path.exists(abs_image_path):
            skipped += 1
            continue

        # Skip if front matter already has image (and file exists)
        if not force and has_image_field(filepath):
            already_has_image += 1
            continue

        title, category = extract_frontmatter(filepath)
        if not title:
            skipped += 1
            continue

        if dry_run:
            print(f'  [DRY RUN] Would generate: {relative_image_path} ({category}: {title[:40]}...)')
            generated += 1
            continue

        if generate_ogp_image(title, category, abs_image_path):
            # Add image field to frontmatter if not present
            if not has_image_field(filepath):
                fm_image_path = f'/{relative_image_path}'
                add_image_to_frontmatter(filepath, fm_image_path)
            generated += 1

            # Progress indicator every 50 images
            if generated % 50 == 0:
                elapsed = time.time() - start_time
                rate = generated / elapsed if elapsed > 0 else 0
                print(f'  Progress: {generated} generated ({rate:.1f} img/sec)', file=sys.stderr)
        else:
            print(f'  Failed: {image_filename}', file=sys.stderr)
            failed += 1

        # Batch size limit
        if batch_size > 0 and generated >= batch_size:
            print(f'\n  Batch limit reached ({batch_size}). Run again for more.')
            break

    elapsed = time.time() - start_time
    print(f'\nDone in {elapsed:.1f}s. Generated: {generated}, Skipped: {skipped}, '
          f'Already had image: {already_has_image}, Failed: {failed}')


def main():
    parser = argparse.ArgumentParser(
        description='Generate OGP images for blog posts'
    )
    parser.add_argument('path', help='Path to _posts/ directory or single .md file')
    parser.add_argument('--dry-run', action='store_true', help='Preview without generating')
    parser.add_argument('--force', action='store_true', help='Regenerate existing images')
    parser.add_argument('--batch-size', type=int, default=0,
                        help='Limit number of images to generate (0=unlimited)')
    args = parser.parse_args()

    process_posts(args.path, dry_run=args.dry_run, force=args.force,
                  batch_size=args.batch_size)


if __name__ == '__main__':
    main()
