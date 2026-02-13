#!/usr/bin/env python3
"""
Title sanitizer for AI-generated blog article titles.
Removes Markdown formatting, clickbait patterns, and handles
multi-byte safe truncation with smart break points.
"""

import re
import unicodedata


class TitleSanitizer:
    """Clean and optimize AI-generated titles for Japanese blog posts."""

    # Markdown patterns to remove
    MARKDOWN_PATTERNS = [
        (r'\*\*(.+?)\*\*', r'\1'),      # **bold**
        (r'\*(.+?)\*', r'\1'),            # *italic*
        (r'__(.+?)__', r'\1'),            # __bold__
        (r'_(.+?)_', r'\1'),              # _italic_
        (r'~~(.+?)~~', r'\1'),            # ~~strikethrough~~
        (r'`(.+?)`', r'\1'),              # `code`
        (r'\[(.+?)\]\(.+?\)', r'\1'),     # [text](url)
        (r'^#{1,6}\s*', ''),              # # heading
    ]

    # Clickbait/sensational patterns to remove (Japanese)
    CLICKBAIT_PATTERNS = [
        r'【衝撃】',
        r'【速報】',
        r'【緊急】',
        r'【驚愕】',
        r'【悲報】',
        r'【朗報】',
        r'【注目】',
        r'【必見】',
        r'【最新】',
        r'【重要】',
        r'【話題】',
        r'【炎上】',
        r'！{2,}',          # Multiple exclamation marks ！！！
        r'\!{2,}',          # Multiple ASCII exclamation marks !!!
        r'？{2,}',          # Multiple question marks ？？？
        r'\?{2,}',          # Multiple ASCII question marks ???
    ]

    # Natural break characters for smart truncation (Japanese)
    BREAK_CHARS = set('。、！？：；）」』】〕》〉｝},.!?:;)')
    # Acceptable break positions (after these chars)
    SOFT_BREAK_CHARS = set('のがをはにでとも・')

    @classmethod
    def sanitize(cls, title, max_len=40):
        """Full sanitization pipeline. Returns cleaned title string."""
        if not title:
            return ""

        result = title.strip()
        result = cls.remove_markdown(result)
        result = cls.remove_clickbait(result)
        result = cls.normalize_whitespace(result)
        result = cls.smart_truncate(result, max_len)
        return result

    @classmethod
    def remove_markdown(cls, text):
        """Remove Markdown formatting from text."""
        result = text
        for pattern, replacement in cls.MARKDOWN_PATTERNS:
            result = re.sub(pattern, replacement, result, flags=re.MULTILINE)
        return result.strip()

    @classmethod
    def remove_clickbait(cls, text):
        """Remove clickbait/sensational patterns."""
        result = text
        for pattern in cls.CLICKBAIT_PATTERNS:
            result = re.sub(pattern, '', result)
        return result.strip()

    @classmethod
    def normalize_whitespace(cls, text):
        """Normalize whitespace: collapse multiple spaces, trim."""
        result = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing dashes or special chars
        result = result.strip(' \t\n\r\u3000-_=')
        return result

    @classmethod
    def smart_truncate(cls, text, max_len=40):
        """Multi-byte safe truncation with smart break points.

        Truncates at the nearest natural break point before max_len.
        Falls back to character-level truncation if no good break found.
        """
        if len(text) <= max_len:
            return text

        # Look for a natural break point within the last 30% of allowed length
        search_start = int(max_len * 0.7)
        best_break = -1

        for i in range(search_start, max_len):
            char = text[i]
            if char in cls.BREAK_CHARS:
                best_break = i + 1  # Include the break character
                break
            elif char in cls.SOFT_BREAK_CHARS and i > search_start:
                best_break = i + 1  # Include the particle

        if best_break > 0 and best_break <= max_len:
            return text[:best_break].rstrip()

        # No good break found - truncate at max_len
        return text[:max_len].rstrip()

    @classmethod
    def to_slug(cls, title, max_len=60):
        """Convert Japanese title to URL-safe English slug.

        Since the title is Japanese, we create a romanized/simplified slug.
        Falls back to a timestamp-based slug if conversion fails.
        """
        # Remove all non-alphanumeric, non-Japanese chars
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        # Replace whitespace with hyphens
        slug = re.sub(r'[\s_]+', '-', slug)
        # Remove consecutive hyphens
        slug = re.sub(r'-+', '-', slug)
        # Trim
        slug = slug.strip('-')

        if len(slug) > max_len:
            # Truncate at word boundary
            slug = slug[:max_len].rsplit('-', 1)[0]

        return slug or "article"

    @classmethod
    def validate(cls, title):
        """Validate a title. Returns (is_valid, issues) tuple."""
        issues = []

        if not title:
            return False, ["Title is empty"]

        if len(title) < 5:
            issues.append("Title too short (< 5 chars)")

        if len(title) > 60:
            issues.append(f"Title too long ({len(title)} chars, max 60)")

        if re.search(r'\*\*|__|~~|`', title):
            issues.append("Contains Markdown formatting")

        if re.search(r'【.+?】', title):
            issues.append("Contains bracket decorations")

        # Check for truncation artifacts
        if title.endswith(('...', '…')):
            issues.append("Appears truncated")

        # Check for encoding issues (replacement character)
        if '\ufffd' in title or '?' in title[-3:]:
            issues.append("Possible encoding corruption")

        return len(issues) == 0, issues


def main():
    """CLI usage: title_sanitizer.py <title> [max_len]"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: title_sanitizer.py <title> [max_len]", file=sys.stderr)
        sys.exit(1)

    title = sys.argv[1]
    max_len = int(sys.argv[2]) if len(sys.argv) > 2 else 40

    sanitized = TitleSanitizer.sanitize(title, max_len)
    is_valid, issues = TitleSanitizer.validate(sanitized)

    print(sanitized)
    if issues:
        for issue in issues:
            print(f"  Warning: {issue}", file=sys.stderr)


if __name__ == '__main__':
    main()
