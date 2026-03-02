#!/usr/bin/env python3
"""
内部リンク戦略エンジン — E-E-A-T 向上

実装方針：
1. Pillar Content（柱記事）: カテゴリ別の包括的なガイド
2. Cluster Content（クラスタ記事）: 詳細な技術解説・事例
3. Topic Cluster Model: Pillar ← (内部リンク) ← Cluster
4. SEO効果: クローラー巡回 + ユーザー回遊 + ドメインオーソリティ向上

セクション別の内部リンク戦略：
- 導入：関連カテゴリの入門記事へリンク
- 詳細：技術詳細記事へリンク
- 実装例：類似事例記事へリンク
- まとめ：総合ガイド（Pillar）へリンク
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict


class InternalLinkingStrategy:
    """内部リンク戦略エンジン"""

    def __init__(self, posts_dir: str = "_posts"):
        self.posts_dir = Path(posts_dir)
        self.articles = {}
        self.keyword_index = defaultdict(list)
        self.category_map = defaultdict(list)
        self.load_articles()

    def load_articles(self):
        """既存記事を読み込んでインデックス化"""
        if not self.posts_dir.exists():
            return

        for post_file in self.posts_dir.glob("*.md"):
            try:
                with open(post_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Parse frontmatter
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        fm = parts[1]
                        body = parts[2]

                        # Extract metadata
                        title = self._extract_frontmatter(fm, "title")
                        category = self._extract_frontmatter(fm, "categories")
                        date_str = self._extract_frontmatter(fm, "date")
                        slug = post_file.stem

                        if title and category:
                            self.articles[slug] = {
                                "file": post_file,
                                "title": title,
                                "category": category,
                                "date": date_str,
                                "body": body,
                                "keywords": self._extract_keywords(title, body),
                            }

                            # Index by category
                            self.category_map[category].append(slug)

                            # Index by keywords
                            for keyword in self._extract_keywords(title, body):
                                self.keyword_index[keyword].append(slug)
            except Exception as e:
                print(f"Warning: Failed to parse {post_file}: {e}")

    def _extract_frontmatter(self, fm: str, key: str) -> Optional[str]:
        """Extract a value from frontmatter"""
        pattern = rf'{key}:\s*"?([^"\n]+)"?'
        match = re.search(pattern, fm)
        return match.group(1).strip() if match else None

    def _extract_keywords(self, title: str, body: str, max_keywords: int = 5) -> List[str]:
        """Extract important keywords from title and body"""
        # Simple keyword extraction: title words + section headers
        keywords = []

        # Title keywords (high priority)
        title_words = [w for w in title.split() if len(w) > 3 and w not in ["とは", "する", "なり"]]
        keywords.extend(title_words[:3])

        # Section headers (medium priority)
        headers = re.findall(r"^#+\s+(.+)$", body, re.MULTILINE)
        for header in headers[:3]:
            header_words = [w for w in header.split() if len(w) > 3]
            keywords.extend(header_words[:1])

        # Remove duplicates and limit
        seen = set()
        result = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                result.append(k)
                if len(result) >= max_keywords:
                    break

        return result

    def find_related_articles(
        self,
        title: str,
        category: str,
        body: str = "",
        max_links: int = 3,
    ) -> List[Tuple[str, str, str]]:
        """Find related articles for internal linking.

        Returns:
            List of (article_slug, article_title, link_reason)
        """
        keywords = self._extract_keywords(title, body)
        related = defaultdict(lambda: {"score": 0, "title": "", "slug": ""})

        # Score articles by keyword match
        for keyword in keywords:
            for slug in self.keyword_index.get(keyword, []):
                if self.articles[slug]["category"] != category:  # Prefer different category
                    related[slug]["score"] += 2
                else:
                    related[slug]["score"] += 1
                related[slug]["title"] = self.articles[slug]["title"]
                related[slug]["slug"] = slug

        # Score articles by category proximity (same category = lower priority)
        same_category_articles = [
            s for s in self.category_map.get(category, []) if s not in related
        ]
        for slug in same_category_articles[:2]:
            related[slug]["score"] = 0.5
            related[slug]["title"] = self.articles[slug]["title"]
            related[slug]["slug"] = slug

        # Sort by score and return top N
        sorted_articles = sorted(related.items(), key=lambda x: x[1]["score"], reverse=True)
        result = [
            (item["slug"], item["title"], "関連記事")
            for _, item in sorted_articles[:max_links]
        ]

        return result

    def find_pillar_article(self, category: str) -> Optional[Tuple[str, str]]:
        """Find the main Pillar article for a category.

        Pillar articles are comprehensive guides that serve as entry points.
        Strategy: Longest article in category = best candidate for pillar.
        """
        candidates = []
        for slug in self.category_map.get(category, []):
            article = self.articles[slug]
            body_length = len(article["body"])
            candidates.append((slug, article["title"], body_length))

        if candidates:
            # Return longest article as pillar
            pillar_slug, pillar_title, _ = max(candidates, key=lambda x: x[2])
            return (pillar_slug, pillar_title)

        return None

    def generate_internal_links_markdown(
        self, related_articles: List[Tuple[str, str, str]]
    ) -> str:
        """Generate markdown for internal links section."""
        if not related_articles:
            return ""

        md_lines = ["\n## 関連記事\n"]
        for slug, title, reason in related_articles:
            # Use Jekyll link tag or URL
            md_lines.append(f"- [{title}]({self._article_url(slug)}) — {reason}")

        return "\n".join(md_lines)

    def _article_url(self, slug: str) -> str:
        """Generate article URL from slug."""
        # Jekyll post URL format: /YYYY/MM/DD/slug/
        article = self.articles.get(slug)
        if article:
            date_str = article["date"].split()[0] if article["date"] else "2026-01-01"
            date_parts = date_str.split("-")
            if len(date_parts) == 3:
                year, month, day = date_parts
                return f"/{year}/{month}/{day}/{slug}/"

        # Fallback
        return f"/{slug}/"

    def generate_metadata_with_links(
        self,
        title: str,
        category: str,
        body: str,
        existing_metadata: Optional[Dict] = None,
    ) -> Dict:
        """Generate metadata enriched with internal linking strategy."""
        metadata = existing_metadata or {}

        # Find related articles
        related = self.find_related_articles(title, category, body, max_links=3)

        # Find pillar article if available
        pillar = self.find_pillar_article(category)

        # Add to metadata
        metadata["related_articles"] = [
            {"slug": slug, "title": title, "reason": reason}
            for slug, title, reason in related
        ]

        if pillar:
            metadata["pillar_article"] = {"slug": pillar[0], "title": pillar[1]}

        # Add SEO tags: include related keywords
        all_keywords = set()
        for keyword in self._extract_keywords(title, body):
            all_keywords.add(keyword)
        for _, _, _ in related:
            pass  # Additional keyword extraction could happen here

        if "tags" in metadata:
            metadata["tags"].extend(list(all_keywords))
            metadata["tags"] = list(dict.fromkeys(metadata["tags"]))  # Remove duplicates

        return metadata

    def get_linking_statistics(self) -> Dict:
        """Get statistics about internal linking opportunity."""
        stats = {
            "total_articles": len(self.articles),
            "by_category": {},
            "avg_links_per_article": 0,
            "linking_opportunities": 0,
        }

        for category in self.category_map:
            category_count = len(self.category_map[category])
            stats["by_category"][category] = category_count

            # Each article can link to 2-3 others = N * 2.5 opportunities
            stats["linking_opportunities"] += int(category_count * 2.5)

        if stats["total_articles"] > 0:
            stats["avg_links_per_article"] = stats["linking_opportunities"] / stats["total_articles"]

        return stats


# Utility function for use in article_pipeline.py
def get_internal_linking_engine(posts_dir: str = "_posts") -> InternalLinkingStrategy:
    """Initialize and return the internal linking strategy engine."""
    return InternalLinkingStrategy(posts_dir)
