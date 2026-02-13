#!/usr/bin/env python3
"""
Fix categories and tags in blog posts based on content analysis.

Features:
  - Category name migration (old names -> _config.yml names)
  - Weighted category scoring with bias reduction
  - Technology-specific tag detection (no useless default tags)
  - Reading time calculation based on character count
  - --migrate-only mode for safe category renaming
  - --dry-run mode for preview
"""

import os
import glob
import re
import argparse
from pathlib import Path


# ---------------------------------------------------------------------------
# Category name migration: old internal names -> _config.yml canonical names
# ---------------------------------------------------------------------------
CATEGORY_MIGRATION = {
    "最新動向": "AI最新ニュース",
    "技術解説": "AI技術ガイド",
    "業界分析": "業界別AI活用",
    "実装事例": "導入事例",
    # These are already correct in _config.yml:
    # "AI導入戦略": "AI導入戦略",
    # "研究論文": "研究論文",
}


def migrate_category_name(current_category):
    """Map old category names to _config.yml canonical names.

    Returns the migrated name if a mapping exists, otherwise returns the
    original name unchanged.
    """
    return CATEGORY_MIGRATION.get(current_category, current_category)


# ---------------------------------------------------------------------------
# Category analysis
# ---------------------------------------------------------------------------
def analyze_content_for_categories(filepath):
    """Analyze article content to determine the best category.

    Uses weighted keyword scoring. Broad financial terms that appear in
    almost every AI article (投資, 市場, 株価 ...) are intentionally
    excluded from AI導入戦略 to prevent the 61% skew observed previously.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()
            title_content = content[:1000]  # Focus on title and first part

        # Category definitions: keywords + weight multiplier
        categories = {
            "AI最新ニュース": {
                "keywords": [
                    "発表", "リリース", "新製品", "アップデート", "新機能",
                    "速報", "提携", "買収", "発売", "公開",
                ],
                "weight": 1.2,
            },
            "AI技術ガイド": {
                "keywords": [
                    "アーキテクチャ", "api", "sdk", "プログラム", "コード",
                    "アルゴリズム", "ファインチューニング", "rag", "llm",
                    "transformer", "推論", "学習率", "パラメータ",
                    "ベンチマーク",
                ],
                "weight": 1.3,
            },
            "AI導入戦略": {
                "keywords": [
                    "roi", "ロードマップ", "戦略策定", "導入計画",
                    "投資判断", "リスク評価", "ガバナンス",
                ],
                "weight": 1.0,
            },
            "業界別AI活用": {
                "keywords": [
                    "製造", "金融", "医療", "小売", "物流", "教育",
                    "建設", "不動産", "保険", "農業", "自動車",
                    "エネルギー", "通信", "放送", "出版",
                ],
                "weight": 1.4,
            },
            "導入事例": {
                "keywords": [
                    "導入事例", "活用事例", "ケーススタディ", "成功事例",
                    "プロジェクト事例", "実証実験", "poc", "パイロット",
                    "効果検証",
                ],
                "weight": 1.5,
            },
            "研究論文": {
                "keywords": [
                    "論文", "学術", "実験結果", "arxiv", "neurips",
                    "icml", "iclr", "研究者", "研究チーム",
                ],
                "weight": 1.5,
            },
        }

        # Weighted keyword scoring
        category_scores = {}
        for category, cfg in categories.items():
            raw_score = sum(
                title_content.count(kw) for kw in cfg["keywords"]
            )
            if raw_score > 0:
                category_scores[category] = raw_score * cfg["weight"]

        if category_scores:
            return max(category_scores, key=category_scores.get)
        else:
            return "AI最新ニュース"

    except Exception as e:
        print(f'Error analyzing {filepath}: {e}')
        return "AI最新ニュース"


# ---------------------------------------------------------------------------
# Tag analysis
# ---------------------------------------------------------------------------
def analyze_content_for_tags(filepath):
    """Analyze article content to determine appropriate tags.

    Returns up to 6 tags. No default filler tags are added -- every tag
    must be earned by keyword matches in the content.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().lower()

        tag_keywords = {
            # --- Company tags ---
            "OpenAI": ["openai", "gpt", "chatgpt", "dall-e", "sam altman", "o1", "o3"],
            "Google": ["google", "gemini", "deepmind", "tpu", "alphabet"],
            "Microsoft": ["microsoft", "azure", "copilot", "satya nadella"],
            "Meta": ["meta", "llama", "mark zuckerberg"],
            "NVIDIA": ["nvidia", "gpu", "cuda", "blackwell", "hopper", "jensen huang"],
            "Amazon": ["amazon", "aws", "bedrock"],
            "Anthropic": ["anthropic", "claude", "constitutional ai"],
            "Apple": ["apple", "siri", "apple intelligence"],
            "xAI": ["xai", "grok", "elon musk"],
            "ByteDance": ["bytedance", "tiktok", "doubao"],

            # --- Technology tags ---
            "LLM": ["llm", "大規模言語モデル", "language model", "transformer"],
            "RAG": ["rag", "検索拡張生成", "retrieval augmented"],
            "AIエージェント": ["エージェント", "agent", "自律型", "ツール呼び出し"],
            "マルチモーダル": ["マルチモーダル", "multimodal", "画像認識", "音声認識"],
            "画像生成": ["画像生成", "stable diffusion", "midjourney", "dall-e", "imagen"],
            "音声AI": ["音声", "speech", "tts", "stt", "whisper"],
            "推論最適化": ["推論", "inference", "量子化", "蒸留", "pruning"],
            "ファインチューニング": ["ファインチューニング", "fine-tun", "lora", "qlora", "peft"],

            # --- Business tags ---
            "ROI分析": ["roi", "投資対効果", "コスト削減効果"],
            "AI規制": ["規制", "法律", "ガイドライン", "コンプライアンス", "eu ai act"],
            "AI人材": ["人材", "採用", "スキル", "リスキリング", "トレーニング"],
            "DX推進": ["dx", "デジタルトランスフォーメーション", "業務改革"],

            # --- Domain tags ---
            "セキュリティ": ["セキュリティ", "security", "プライバシー", "privacy"],
            "AI倫理": ["倫理", "ethics", "責任", "バイアス", "公平性"],
            "自動運転": ["自動運転", "autonomous", "tesla", "waymo"],
            "ロボティクス": ["ロボット", "robot", "ロボティクス"],
        }

        matched_tags = []

        for tag, keywords in tag_keywords.items():
            if any(keyword in content for keyword in keywords):
                if tag not in matched_tags:
                    matched_tags.append(tag)

        # Limit to 6 tags maximum
        return matched_tags[:6]

    except Exception as e:
        print(f'Error analyzing tags for {filepath}: {e}')
        return []


# ---------------------------------------------------------------------------
# Reading time calculation
# ---------------------------------------------------------------------------
def calculate_reading_time(filepath):
    """Calculate reading time based on Japanese character count (500 chars/min).

    Returns an integer between 3 and 20 (minutes).
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        # Skip frontmatter
        parts = content.split('---', 2)
        if len(parts) >= 3:
            body = parts[2]
        else:
            body = content

        char_count = len(body.strip())
        reading_time = max(3, min(20, (char_count // 500) + 1))
        return reading_time

    except Exception:
        return 8


# ---------------------------------------------------------------------------
# Frontmatter update
# ---------------------------------------------------------------------------
def update_frontmatter(filepath, migrate_only=False, dry_run=False):
    """Update the frontmatter of a markdown file.

    Args:
        filepath: Path to the markdown file.
        migrate_only: If True, only migrate category names (no re-analysis).
        dry_run: If True, print changes but do not write.

    Returns:
        True if the file was (or would be) updated, False otherwise.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        if not content.strip():
            print(f'  Empty file: {filepath}')
            return False

        lines = content.split('\n')

        # Find frontmatter boundaries
        frontmatter_start = -1
        frontmatter_end = -1

        for i, line in enumerate(lines):
            if line.strip() == '---':
                if frontmatter_start == -1:
                    frontmatter_start = i
                else:
                    frontmatter_end = i
                    break

        if frontmatter_start == -1 or frontmatter_end == -1:
            print(f'  No valid frontmatter found in {filepath}')
            return False

        # --- Determine new category ---
        current_category = None
        for i, line in enumerate(lines):
            if frontmatter_start < i < frontmatter_end:
                if line.startswith('categories:'):
                    # Extract current category from various formats:
                    #   categories: ["foo"]  /  categories: [foo]  /  categories: foo
                    raw = line.replace('categories:', '').strip()
                    raw = raw.strip('[]').strip()
                    raw = raw.strip('"').strip("'")
                    current_category = raw
                    break

        if migrate_only:
            # Only rename if a migration mapping exists
            if current_category and current_category in CATEGORY_MIGRATION:
                new_category = CATEGORY_MIGRATION[current_category]
            else:
                new_category = current_category
        else:
            # Full re-analysis, but prefer migration for known old names
            if current_category and current_category in CATEGORY_MIGRATION:
                new_category = CATEGORY_MIGRATION[current_category]
            else:
                new_category = analyze_content_for_categories(filepath)

        # --- Determine new tags ---
        if migrate_only:
            new_tags = None  # Do not touch tags in migrate-only mode
        else:
            new_tags = analyze_content_for_tags(filepath)

        # --- Calculate reading time ---
        if migrate_only:
            new_reading_time = None  # Do not touch reading_time in migrate-only mode
        else:
            new_reading_time = calculate_reading_time(filepath)

        # --- Build updated lines ---
        updated_lines = []
        category_updated = False
        tags_updated = False
        reading_time_updated = False
        changes = []

        for i, line in enumerate(lines):
            if frontmatter_start < i < frontmatter_end:
                if line.startswith('categories:') and new_category is not None:
                    new_line = f'categories: ["{new_category}"]'
                    if line != new_line:
                        changes.append(f'  category: {line.strip()} -> {new_line.strip()}')
                    updated_lines.append(new_line)
                    category_updated = True
                elif line.startswith('tags:') and new_tags is not None:
                    tag_str = ', '.join(f'"{tag}"' for tag in new_tags)
                    new_line = f'tags: [{tag_str}]'
                    if line != new_line:
                        changes.append(f'  tags: updated')
                    updated_lines.append(new_line)
                    tags_updated = True
                elif line.startswith('reading_time:') and new_reading_time is not None:
                    new_line = f'reading_time: {new_reading_time}'
                    if line != new_line:
                        changes.append(f'  reading_time: {line.strip()} -> {new_line.strip()}')
                    updated_lines.append(new_line)
                    reading_time_updated = True
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # If reading_time line did not exist, insert it before frontmatter end
        if new_reading_time is not None and not reading_time_updated:
            insert_pos = frontmatter_end  # adjusted index in updated_lines
            # Find actual position of closing --- in updated_lines
            for idx in range(len(updated_lines) - 1, -1, -1):
                if updated_lines[idx].strip() == '---' and idx > frontmatter_start:
                    insert_pos = idx
                    break
            updated_lines.insert(insert_pos, f'reading_time: {new_reading_time}')
            changes.append(f'  reading_time: added ({new_reading_time})')

        if not changes:
            return False

        if dry_run:
            print(f'  [DRY RUN] {os.path.basename(filepath)}:')
            for c in changes:
                print(f'    {c}')
            return True

        # Write updated content back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines))

        return True

    except Exception as e:
        print(f'  Failed to update {filepath}: {e}')
        return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='Fix categories and tags in blog posts based on content analysis.'
    )
    parser.add_argument(
        '--migrate-only',
        action='store_true',
        help='Only migrate category names without re-analysis of content',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show changes without applying them',
    )
    args = parser.parse_args()

    mode_label = 'migration only' if args.migrate_only else 'full analysis'
    dry_label = ' (dry run)' if args.dry_run else ''
    print(f'Fixing categories and tags [{mode_label}]{dry_label} ...')

    # Find all markdown files in _posts
    post_files = sorted(glob.glob('_posts/*.md'))

    if not post_files:
        print('No posts found in _posts/. Make sure you run from the repo root.')
        return

    updated_count = 0
    skipped_count = 0

    for filepath in post_files:
        filename = os.path.basename(filepath)

        if update_frontmatter(filepath, migrate_only=args.migrate_only, dry_run=args.dry_run):
            print(f'  Updated: {filename}')
            updated_count += 1
        else:
            skipped_count += 1

    print(f'\nDone. Updated: {updated_count}, Skipped (no changes): {skipped_count}')


if __name__ == '__main__':
    main()
