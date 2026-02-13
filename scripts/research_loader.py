#!/usr/bin/env python3
"""
Research data loader for article pipeline integration.
Reads structured YAML research files from _data/research/ and formats
them for prompt injection into article generation.
"""

import os
import sys
import re
import yaml
from datetime import datetime, timedelta


class ResearchLoader:
    """Load and format pre-research data for article generation."""

    def __init__(self, research_dir=None):
        """Initialize with path to _data/research/ directory.

        Args:
            research_dir: Path to research directory. Auto-detects if None.
        """
        if research_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            research_dir = os.path.join(os.path.dirname(script_dir), '_data', 'research')
        self.research_dir = research_dir

    def find_research(self, topic_slug=None, keywords=None, date=None, max_age_days=7):
        """Find matching research YAML for a topic.

        Args:
            topic_slug: Slug to match in filename (e.g., 'openai-gpt5')
            keywords: List of keywords to match in topic field
            date: Specific date string (YYYY-MM-DD) or None for recent
            max_age_days: Maximum age of research data in days

        Returns:
            Parsed YAML dict, or None if no match found
        """
        if not os.path.isdir(self.research_dir):
            return None

        cutoff = datetime.now() - timedelta(days=max_age_days)
        best_match = None
        best_score = 0

        for filename in sorted(os.listdir(self.research_dir), reverse=True):
            if not filename.endswith('.yml') or filename.startswith('.'):
                continue

            # Parse date from filename: {date}-{slug}.yml
            match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.yml', filename)
            if not match:
                continue

            file_date_str, file_slug = match.group(1), match.group(2)

            # Check date filter
            try:
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                if file_date < cutoff:
                    continue
                if date and file_date_str != date:
                    continue
            except ValueError:
                continue

            # Score match
            score = 0

            # Slug match
            if topic_slug:
                slug_lower = topic_slug.lower()
                file_slug_lower = file_slug.lower()
                if slug_lower == file_slug_lower:
                    score += 100
                elif slug_lower in file_slug_lower or file_slug_lower in slug_lower:
                    score += 50
                # Check word overlap
                slug_words = set(slug_lower.split('-'))
                file_words = set(file_slug_lower.split('-'))
                overlap = slug_words & file_words
                if overlap:
                    score += len(overlap) * 10

            # Keyword match (requires loading file)
            if keywords and score == 0:
                filepath = os.path.join(self.research_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = yaml.safe_load(f)
                    topic_text = str(data.get('topic', '')).lower()
                    for kw in keywords:
                        if kw.lower() in topic_text:
                            score += 20
                except Exception:
                    continue

            # Recency bonus (newer = better)
            days_old = (datetime.now() - file_date).days
            score += max(0, 7 - days_old)

            if score > best_score:
                best_score = score
                best_match = filename

        if not best_match:
            return None

        filepath = os.path.join(self.research_dir, best_match)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            print(f"  [Research] Loaded: {best_match} (score: {best_score})", file=sys.stderr)
            return data
        except Exception as e:
            print(f"  [Research] Error loading {best_match}: {e}", file=sys.stderr)
            return None

    def find_all_recent(self, max_age_days=3):
        """Find all recent research files.

        Args:
            max_age_days: Maximum age in days

        Returns:
            List of parsed YAML dicts
        """
        if not os.path.isdir(self.research_dir):
            return []

        cutoff = datetime.now() - timedelta(days=max_age_days)
        results = []

        for filename in sorted(os.listdir(self.research_dir), reverse=True):
            if not filename.endswith('.yml') or filename.startswith('.'):
                continue

            match = re.match(r'(\d{4}-\d{2}-\d{2})-(.+)\.yml', filename)
            if not match:
                continue

            try:
                file_date = datetime.strptime(match.group(1), '%Y-%m-%d')
                if file_date < cutoff:
                    continue
            except ValueError:
                continue

            filepath = os.path.join(self.research_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                if data:
                    results.append(data)
            except Exception:
                continue

        return results

    def format_research_context(self, research_data):
        """Format research data for prompt injection.

        Args:
            research_data: Parsed YAML dict from find_research()

        Returns:
            Formatted string ready for prompt injection
        """
        if not research_data:
            return ""

        sections = ["【事前リサーチ結果（検証済みデータ）】"]

        # Facts
        facts = research_data.get('facts', [])
        high_confidence = [f for f in facts if f.get('confidence') in ('high', 'medium')]
        if high_confidence:
            sections.append("■ 検証済みファクト:")
            for fact in high_confidence[:10]:
                source = fact.get('source_name', '不明')
                date = fact.get('date', '')
                date_str = f", {date}" if date else ""
                sections.append(f"  - {fact.get('claim', '')}（出典: {source}{date_str}）")

        # Statistics
        statistics = research_data.get('statistics', [])
        if statistics:
            sections.append("■ 統計データ:")
            for stat in statistics[:8]:
                source = stat.get('source', '不明')
                date = stat.get('date', '')
                date_str = f", {date}" if date else ""
                sections.append(f"  - {stat.get('metric', '')}: {stat.get('value', '')}（{source}{date_str}）")

        # Companies
        companies = research_data.get('companies', [])
        if companies:
            sections.append("■ 企業最新情報:")
            for company in companies[:5]:
                name = company.get('name', '')
                news = company.get('latest_news', '')
                numbers = company.get('key_numbers', '')
                parts = [f"  - {name}"]
                if news:
                    parts.append(f": {news}")
                if numbers:
                    parts.append(f"（{numbers}）")
                sections.append("".join(parts))

        # Quotes
        quotes = research_data.get('quotes', [])
        if quotes:
            sections.append("■ 注目発言:")
            for quote in quotes[:3]:
                speaker = quote.get('speaker', '不明')
                sections.append(f"  - 「{quote.get('text', '')}」- {speaker}")

        if len(sections) <= 1:
            return ""

        sections.append("")
        sections.append("【指示】上記リサーチデータを積極的に引用すること。出典を明示すること。")

        return "\n".join(sections)

    def get_kb_updates(self, research_data):
        """Extract KB update instructions from research data.

        Args:
            research_data: Parsed YAML dict

        Returns:
            Dict with kb_updates section, or empty dict
        """
        if not research_data:
            return {}
        return research_data.get('kb_updates', {})


def main():
    """CLI: research_loader.py [--find SLUG] [--recent] [--format SLUG]"""
    import argparse

    parser = argparse.ArgumentParser(description='Load and format research data')
    parser.add_argument('--find', help='Find research by topic slug')
    parser.add_argument('--keywords', nargs='+', help='Find research by keywords')
    parser.add_argument('--recent', action='store_true', help='List all recent research')
    parser.add_argument('--format', dest='format_slug', help='Find and format research for prompt')
    parser.add_argument('--max-age', type=int, default=7, help='Max age in days (default: 7)')
    args = parser.parse_args()

    loader = ResearchLoader()

    if args.recent:
        results = loader.find_all_recent(max_age_days=args.max_age)
        for r in results:
            print(f"  {r.get('date', '?')} - {r.get('topic', '?')}")
        print(f"\nTotal: {len(results)} research files")

    elif args.find:
        data = loader.find_research(topic_slug=args.find, max_age_days=args.max_age)
        if data:
            print(yaml.dump(data, allow_unicode=True, default_flow_style=False))
        else:
            print("No matching research found", file=sys.stderr)

    elif args.format_slug:
        data = loader.find_research(topic_slug=args.format_slug, max_age_days=args.max_age)
        if data:
            print(loader.format_research_context(data))
        else:
            print("No matching research found", file=sys.stderr)

    elif args.keywords:
        data = loader.find_research(keywords=args.keywords, max_age_days=args.max_age)
        if data:
            print(loader.format_research_context(data))
        else:
            print("No matching research found", file=sys.stderr)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
