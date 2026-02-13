#!/usr/bin/env python3
"""
Compliance & knowledge base loader for article pipeline.
Reads Markdown files from knowledge/ directory and provides
formatted text for prompt injection and quality checking.
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional


class ComplianceLoader:
    """Load compliance rules and supplementary knowledge from knowledge/ directory."""

    def __init__(self, base_dir=None):
        """Initialize with path to knowledge/ directory.

        Args:
            base_dir: Path to knowledge/ directory. Auto-detects if None.
        """
        if base_dir is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.join(os.path.dirname(script_dir), 'knowledge')
        self.base_dir = Path(base_dir)
        self._cache = {}

    def _read_markdown(self, file_path: Path) -> Optional[str]:
        """Read a Markdown file with caching."""
        key = str(file_path)
        if key in self._cache:
            return self._cache[key]

        try:
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                self._cache[key] = content
                return content
            else:
                print(f"  [Compliance] File not found: {file_path}", file=sys.stderr)
                return None
        except Exception as e:
            print(f"  [Compliance] Error reading {file_path}: {e}", file=sys.stderr)
            return None

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a named ## section from Markdown."""
        pattern = rf'^## {re.escape(section_name)}\s*\n(.*?)(?=^## |\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            return match.group(1).strip()
        return None

    def _truncate(self, text: str, max_chars: int = 3000) -> str:
        """Truncate text to max_chars."""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n...(以下省略)"

    def load_compliance_rules(self) -> str:
        """Load compliance rules for prompt injection.

        Returns:
            Formatted compliance rules string for article generation prompts.
        """
        compliance_dir = self.base_dir / "compliance"
        if not compliance_dir.exists():
            return ""

        rules = []
        rules.append("【コンプライアンスルール（法令遵守・必須）】")
        rules.append("以下のルールは法令に基づく必須要件です。記事内容がこれらに違反しないよう注意すること。\n")

        for md_file in sorted(compliance_dir.glob("*.md")):
            content = self._read_markdown(md_file)
            if not content:
                continue

            file_name = md_file.stem
            rules.append(f"■ {file_name}")

            # Extract applicable rules section
            apply_rules = self._extract_section(content, "記事生成時の適用ルール")
            if apply_rules:
                rules.append(apply_rules)
                rules.append("")

            # Extract forbidden expressions section
            forbidden = self._extract_section(content, "禁止表現・注意表現")
            if forbidden:
                rules.append(self._truncate(forbidden, 2000))
                rules.append("")

        result = "\n".join(rules)
        print(f"  [Compliance] Loaded rules: {len(result)} chars", file=sys.stderr)
        return result

    def load_tool_info(self, tool_name: str) -> str:
        """Load latest info for a specific tool.

        Args:
            tool_name: Tool name (e.g., "ChatGPT", "Gemini")

        Returns:
            Tool info string, or empty string if not found.
        """
        db_path = self.base_dir / "tools" / "tool_database.md"
        content = self._read_markdown(db_path)
        if not content:
            return ""

        # Exact match: "### ToolName"
        pattern = rf'^### {re.escape(tool_name)}\b.*?\n(.*?)(?=^### |\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            return match.group(0).strip()

        # Partial match: "### ... ToolName ..."
        pattern = rf'^### .*{re.escape(tool_name)}.*\n(.*?)(?=^### |\Z)'
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            return self._truncate(match.group(0).strip(), 2000)

        return ""

    def load_fact_check_sources(self) -> str:
        """Load trusted sources for fact-checking.

        Returns:
            Formatted fact-check source list.
        """
        sources_path = self.base_dir / "competitors" / "信頼できるソース一覧.md"
        content = self._read_markdown(sources_path)
        if not content:
            return ""

        section = self._extract_section(content, "記事生成時の適用ルール")
        if section:
            return self._truncate(section, 2000)

        # Fallback: extract "概要" section
        overview = self._extract_section(content, "概要")
        if overview:
            return self._truncate(overview, 1500)

        return ""

    def build_article_context(self, category: str = "", company_names: list = None) -> str:
        """Build compliance + supplementary context for article generation.

        This is injected into the article generation prompt alongside
        the existing KnowledgeBase and ResearchLoader contexts.

        Args:
            category: Article category for context-specific rules.
            company_names: Companies mentioned in the article.

        Returns:
            Formatted string for prompt injection.
        """
        sections = []

        # 1. Compliance rules (always included)
        compliance = self.load_compliance_rules()
        if compliance:
            sections.append(compliance)

        # 2. Category-specific guidance
        if category in ("AI導入戦略", "業界別AI活用", "導入事例"):
            # For business-oriented articles, add investment disclaimer rules
            fin_rules = self._extract_section(
                self._read_markdown(self.base_dir / "compliance" / "金融商品取引法ガイド.md") or "",
                "記事生成時の適用ルール"
            )
            if fin_rules:
                sections.append(f"\n【投資関連記事の追加注意事項】\n{fin_rules}")

        # 3. Tool info if companies are mentioned
        if company_names:
            tool_infos = []
            for name in company_names[:3]:
                info = self.load_tool_info(name)
                if info:
                    tool_infos.append(info)
            if tool_infos:
                sections.append("\n【ツール・企業最新情報】")
                sections.append("\n---\n".join(tool_infos))

        # 4. Fact-check reminder
        sections.append(
            "\n【ファクトチェック指示】"
            "\n- 数値データは「〜によると」「〜年時点で」と出典を明記すること"
            "\n- 確認できない数値は使用しないこと"
            "\n- 「必ず」「絶対」などの断定表現を避けること"
            "\n- 景品表示法に抵触する誇大表現を使用しないこと"
        )

        return "\n\n".join(sections)


# Compliance check patterns (used by quality_scorer.py)
COMPLIANCE_PATTERNS = [
    # Definitive income guarantees (景品表示法 violation risk)
    (r'(?:誰でも|誰もが|あなたも)(?:簡単に|必ず|確実に|絶対).{0,10}(?:稼げ|儲か|収入|収益)',
     "断定的収入保証（景品表示法違反リスク）", 3),
    (r'(?:必ず|絶対に|確実に).{0,15}(?:月\d+万|稼げ|成功)',
     "断定的成功保証（景品表示法違反リスク）", 3),
    (r'(?:誰でも|初心者でも)(?:簡単に|すぐに).{0,10}(?:稼|収入|収益)',
     "「誰でも簡単に」系の誇大表現", 2),

    # Unsubstantiated income claims
    (r'(?:月|年)\d+万円(?:稼げます|儲かります|手に入ります|得られます)',
     "根拠なき収入額の断言", 2),

    # Passive income / effortless earnings
    (r'(?:不労所得|寝ている間に|何もしなくても|放置で).{0,10}(?:稼|収入|収益)',
     "不労所得・放置系の誤解を招く表現", 3),

    # Investment advice risk
    (r'(?:この銘柄|この株|この投資).{0,10}(?:買う(?:べき|べし)|おすすめ)',
     "投資助言に該当する表現（金融商品取引法リスク）", 3),

    # False urgency / scarcity
    (r'(?:今だけ|期間限定|先着\d+名).{0,10}(?:無料|割引|特別価格)',
     "虚偽の緊急性・限定性（有利誤認リスク）", 2),
]

# Disclaimer patterns (presence reduces compliance penalty)
DISCLAIMER_PATTERNS = [
    r'個人の(?:感想|実績|体験)',
    r'(?:成果|結果|効果)を保証するものではありません',
    r'個人差があります',
    r'(?:成果|収入)には個人差',
    r'(?:筆者|私)の(?:場合|実績)',
    r'自己責任',
    r'利用規約を(?:確認|ご確認)',
]


def check_compliance(body: str):
    """Check article body for compliance violations.

    Args:
        body: Article body text.

    Returns:
        (penalty, issues) tuple.
        penalty: 0-15 score penalty.
        issues: List of detected issue descriptions.
    """
    detected = []
    total_penalty = 0

    for pattern, description, penalty_per_match in COMPLIANCE_PATTERNS:
        matches = re.findall(pattern, body, re.MULTILINE)
        if matches:
            count = len(matches)
            detected.append(f"{description} ({count}件)")
            total_penalty += penalty_per_match * count

    # Check for income claims without disclaimer
    has_income_claim = bool(re.search(r'月\d+[万千]円', body))
    if has_income_claim:
        has_disclaimer = any(re.search(p, body) for p in DISCLAIMER_PATTERNS)
        if not has_disclaimer:
            detected.append("収入額の記載があるが打消し表示なし")
            total_penalty += 3

    return min(15, total_penalty), detected


def main():
    """CLI: compliance_loader.py [--rules] [--tool NAME] [--context CATEGORY] [--check FILE]"""
    import argparse

    parser = argparse.ArgumentParser(description='Load compliance knowledge base')
    parser.add_argument('--rules', action='store_true', help='Show compliance rules')
    parser.add_argument('--tool', help='Show tool info')
    parser.add_argument('--context', help='Build article context for category')
    parser.add_argument('--check', help='Check a markdown file for compliance')
    args = parser.parse_args()

    loader = ComplianceLoader()

    if args.rules:
        print(loader.load_compliance_rules())
    elif args.tool:
        info = loader.load_tool_info(args.tool)
        print(info if info else f"No info found for: {args.tool}")
    elif args.context:
        print(loader.build_article_context(category=args.context))
    elif args.check:
        try:
            with open(args.check, 'r', encoding='utf-8') as f:
                content = f.read()
            penalty, issues = check_compliance(content)
            print(f"Compliance penalty: {penalty}/15")
            for issue in issues:
                print(f"  - {issue}")
            if not issues:
                print("  No compliance issues detected")
        except FileNotFoundError:
            print(f"File not found: {args.check}", file=sys.stderr)
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
