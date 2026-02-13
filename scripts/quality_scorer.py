#!/usr/bin/env python3
"""
Quality scorer for AI-generated blog articles.
Scores articles on a 100-point scale across 4 dimensions:
- Completeness (25 pts)
- Factual density (25 pts)
- Readability (25 pts)
- Engagement (25 pts)

Pass threshold: 60 points
"""

import re
import sys


class QualityScorer:
    """Score article quality and provide actionable feedback."""

    PASS_THRESHOLD = 60

    # AI cliche phrases to penalize (Japanese)
    AI_CLICHES = [
        "大幅な改善",
        "革命的な",
        "画期的な",
        "パラダイムシフト",
        "目覚ましい進歩",
        "飛躍的な成長",
        "無限の可能性",
        "前例のない",
        "言うまでもなく",
        "いかがでしたでしょうか",
        "いかがでしたか",
        "まとめると",
        "最後までお読みいただき",
        "参考になれば幸いです",
        "お役に立てれば幸いです",
        "注目を集めています",
        "期待されています",
        "ますます重要になって",
    ]

    # Known company names for factual density check
    COMPANY_NAMES = [
        "OpenAI", "Google", "Microsoft", "NVIDIA", "Meta",
        "Amazon", "Anthropic", "Apple", "Samsung", "Intel",
        "AMD", "Broadcom", "ByteDance", "Baidu", "Mistral",
        "IBM", "Oracle", "Salesforce", "Adobe", "Tesla",
        "DeepMind", "Hugging Face", "Stability AI", "Cohere",
        "xAI", "Perplexity", "Databricks", "Snowflake",
        "ソフトバンク", "NTT", "富士通", "NEC", "日立",
        "トヨタ", "ソニー", "楽天", "LINE", "サイバーエージェント",
        "PKSHA", "Preferred Networks", "ABEJA",
    ]

    # Product/model names
    PRODUCT_NAMES = [
        "GPT-4", "GPT-4o", "GPT-5", "o1", "o3",
        "Claude", "Gemini", "Llama", "Mistral",
        "DALL-E", "Sora", "Midjourney", "Stable Diffusion",
        "Copilot", "Duet AI", "Bard",
        "H100", "H200", "B200", "A100",
        "ChatGPT", "Perplexity", "NotebookLM",
        "RAG", "LoRA", "RLHF", "DPO",
        "Transformer", "BERT", "LLM",
    ]

    @classmethod
    def score(cls, title, body, category=None):
        """Score an article. Returns (total_score, details_dict, feedback_list)."""
        details = {}
        feedback = []

        # 1. Completeness (25 pts)
        comp_score, comp_feedback = cls._score_completeness(body)
        details['completeness'] = comp_score
        feedback.extend(comp_feedback)

        # 2. Factual density (25 pts)
        fact_score, fact_feedback = cls._score_factual_density(body)
        details['factual_density'] = fact_score
        feedback.extend(fact_feedback)

        # 3. Readability (25 pts)
        read_score, read_feedback = cls._score_readability(body)
        details['readability'] = read_score
        feedback.extend(read_feedback)

        # 4. Engagement (25 pts)
        eng_score, eng_feedback = cls._score_engagement(title, body)
        details['engagement'] = eng_score
        feedback.extend(eng_feedback)

        total = sum(details.values())
        details['total'] = total
        details['passed'] = total >= cls.PASS_THRESHOLD

        return total, details, feedback

    @classmethod
    def _score_completeness(cls, body):
        """Score completeness (max 25 pts)."""
        score = 0
        feedback = []

        # Character count: 3000+ chars = 10 pts
        char_count = len(body)
        if char_count >= 3000:
            score += 10
        elif char_count >= 2000:
            score += 5
            feedback.append(f"[completeness] Article is {char_count} chars, aim for 3000+")
        else:
            feedback.append(f"[completeness] Article too short: {char_count} chars (need 3000+)")

        # Ends with proper punctuation: 5 pts
        stripped = body.rstrip()
        if stripped and stripped[-1] in '。！？.!?':
            score += 5
        else:
            feedback.append("[completeness] Article doesn't end with proper punctuation")

        # Has 3+ headings (## or ###): 5 pts
        headings = re.findall(r'^#{2,3}\s+.+', body, re.MULTILINE)
        if len(headings) >= 3:
            score += 5
        else:
            feedback.append(f"[completeness] Only {len(headings)} headings (need 3+)")

        # Has conclusion section: 5 pts
        conclusion_patterns = [
            r'##\s*(まとめ|結論|おわりに|今後の展望|結び)',
            r'##\s*(Conclusion|Summary|Final)',
        ]
        has_conclusion = any(re.search(p, body, re.IGNORECASE) for p in conclusion_patterns)
        if has_conclusion:
            score += 5
        else:
            feedback.append("[completeness] Missing conclusion/summary section")

        return score, feedback

    @classmethod
    def _score_factual_density(cls, body):
        """Score factual density (max 25 pts)."""
        score = 0
        feedback = []

        # Numbers/statistics: 5+ = 10 pts
        # Match numbers with units, percentages, dollar amounts, etc.
        number_patterns = [
            r'\d+\.?\d*\s*[%％]',           # Percentages
            r'\$\d+[\d,.]*[BMK]?',           # Dollar amounts
            r'\d+[\d,.]*\s*(億|兆|万)',       # Japanese large numbers
            r'\d{4}年',                       # Year references
            r'\d+\.?\d*\s*(倍|件|社|人|台)',  # Count with units
        ]
        num_count = sum(len(re.findall(p, body)) for p in number_patterns)
        if num_count >= 5:
            score += 10
        elif num_count >= 3:
            score += 5
            feedback.append(f"[factual] {num_count} data points found, aim for 5+")
        else:
            feedback.append(f"[factual] Only {num_count} data points - add specific numbers, stats, market data")

        # Company names: 3+ = 5 pts
        company_count = sum(1 for c in cls.COMPANY_NAMES if c in body)
        if company_count >= 3:
            score += 5
        else:
            feedback.append(f"[factual] Only {company_count} companies mentioned (need 3+)")

        # Product/model names: 2+ = 5 pts
        product_count = sum(1 for p in cls.PRODUCT_NAMES if p in body)
        if product_count >= 2:
            score += 5
        else:
            feedback.append(f"[factual] Only {product_count} products/models mentioned (need 2+)")

        # Source attribution: 2+ = 5 pts
        source_patterns = [
            r'によると',
            r'によれば',
            r'発表した',
            r'報告して',
            r'調査では',
            r'レポート',
            r'according to',
            r'\d{4}年\d{1,2}月時点',
            r'（出典',
            r'出所[：:]',
        ]
        source_count = sum(len(re.findall(p, body, re.IGNORECASE)) for p in source_patterns)
        if source_count >= 2:
            score += 5
        elif source_count >= 1:
            score += 2
            feedback.append("[factual] Add more source attributions (e.g., 'Xによると', '2025年時点')")
        else:
            feedback.append("[factual] No source attributions found - cite sources for credibility")

        return score, feedback

    @classmethod
    def _score_readability(cls, body):
        """Score readability (max 25 pts)."""
        score = 0
        feedback = []

        # Paragraphs: 5+ = 5 pts
        paragraphs = [p.strip() for p in body.split('\n\n') if p.strip() and not p.strip().startswith('#')]
        if len(paragraphs) >= 5:
            score += 5
        else:
            feedback.append(f"[readability] Only {len(paragraphs)} paragraphs (need 5+)")

        # Average paragraph length: 100-400 chars = 5 pts
        if paragraphs:
            avg_len = sum(len(p) for p in paragraphs) / len(paragraphs)
            if 100 <= avg_len <= 400:
                score += 5
            elif avg_len < 100:
                feedback.append(f"[readability] Paragraphs too short (avg {avg_len:.0f} chars)")
            else:
                feedback.append(f"[readability] Paragraphs too long (avg {avg_len:.0f} chars, aim for 100-400)")

        # Bullet points: not excessive (<=15 lines starting with - or *) = 5 pts
        bullet_lines = len(re.findall(r'^\s*[-*]\s', body, re.MULTILINE))
        total_lines = len([l for l in body.split('\n') if l.strip()])
        bullet_ratio = bullet_lines / max(total_lines, 1)
        if bullet_ratio <= 0.3:
            score += 5
        else:
            feedback.append(f"[readability] Too many bullet points ({bullet_ratio:.0%} of content)")

        # No AI cliche phrases = 10 pts
        cliche_found = [c for c in cls.AI_CLICHES if c in body]
        if not cliche_found:
            score += 10
        elif len(cliche_found) <= 2:
            score += 5
            feedback.append(f"[readability] AI cliches found: {', '.join(cliche_found[:3])}")
        else:
            feedback.append(f"[readability] Multiple AI cliches ({len(cliche_found)}): {', '.join(cliche_found[:5])}")

        return score, feedback

    @classmethod
    def _score_engagement(cls, title, body):
        """Score engagement potential (max 25 pts)."""
        score = 0
        feedback = []

        # Questions in body: 2+ = 10 pts
        questions = re.findall(r'[？?]', body)
        if len(questions) >= 2:
            score += 10
        elif len(questions) >= 1:
            score += 5
            feedback.append("[engagement] Add more rhetorical questions to engage readers")
        else:
            feedback.append("[engagement] No questions found - add rhetorical questions")

        # Personal opinion/perspective: 5 pts
        opinion_markers = [
            r'と考え[るられ]',
            r'ではないだろうか',
            r'と言える',
            r'注目すべき',
            r'興味深い',
            r'筆者は',
            r'私見では',
            r'個人的には',
            r'重要なのは',
            r'ポイントは',
        ]
        has_opinion = any(re.search(p, body) for p in opinion_markers)
        if has_opinion:
            score += 5
        else:
            feedback.append("[engagement] Add editorial perspective or personal analysis")

        # Intro paragraph <= 150 chars: 5 pts
        first_para = ""
        for line in body.split('\n'):
            stripped = line.strip()
            if stripped and not stripped.startswith('#'):
                first_para = stripped
                break
        if first_para and len(first_para) <= 150:
            score += 5
        elif first_para:
            feedback.append(f"[engagement] Intro too long ({len(first_para)} chars, aim for <=150)")

        # Curiosity-inducing title: 5 pts
        curiosity_patterns = [
            r'[？?]',          # Question in title
            r'なぜ',           # "Why"
            r'どう',           # "How"
            r'秘密',           # "Secret"
            r'理由',           # "Reason"
            r'方法',           # "Method"
            r'比較',           # "Comparison"
            r'vs\.?',          # "vs"
            r'徹底',           # "Thorough"
            r'\d+選',          # "X selections"
            r'\d+つの',        # "X things"
        ]
        has_curiosity = any(re.search(p, title or '') for p in curiosity_patterns)
        if has_curiosity:
            score += 5
        else:
            feedback.append("[engagement] Title could be more curiosity-inducing")

        return score, feedback

    @classmethod
    def format_report(cls, total, details, feedback):
        """Format a human-readable quality report."""
        lines = [
            f"Quality Score: {total}/100 ({'PASS' if details['passed'] else 'FAIL'})",
            f"  Completeness:    {details['completeness']}/25",
            f"  Factual density: {details['factual_density']}/25",
            f"  Readability:     {details['readability']}/25",
            f"  Engagement:      {details['engagement']}/25",
        ]

        if feedback:
            lines.append("\nFeedback for improvement:")
            for f in feedback:
                lines.append(f"  - {f}")

        return "\n".join(lines)

    @classmethod
    def generate_retry_prompt(cls, feedback, original_prompt=""):
        """Generate a revision prompt based on quality feedback."""
        improvement_instructions = []

        for f in feedback:
            if "[factual]" in f and "data points" in f:
                improvement_instructions.append("Include more specific numbers, statistics, and market data (at least 5 data points)")
            elif "[factual]" in f and "companies" in f:
                improvement_instructions.append("Mention at least 3 specific companies with their actual products or achievements")
            elif "[factual]" in f and "source" in f:
                improvement_instructions.append("Add source attributions like 'Xによると' or 'Y年時点で'")
            elif "[readability]" in f and "cliche" in f:
                improvement_instructions.append("Replace generic AI phrases with specific, concrete descriptions")
            elif "[engagement]" in f and "question" in f:
                improvement_instructions.append("Add 2-3 rhetorical questions to engage readers")
            elif "[completeness]" in f and "short" in f:
                improvement_instructions.append("Expand the article to at least 3000 characters with deeper analysis")

        if not improvement_instructions:
            return ""

        prompt = "Please revise the article with these improvements:\n"
        for i, instruction in enumerate(improvement_instructions, 1):
            prompt += f"{i}. {instruction}\n"

        return prompt


def main():
    """CLI: quality_scorer.py <markdown_file>"""
    if len(sys.argv) < 2:
        print("Usage: quality_scorer.py <markdown_file>", file=sys.stderr)
        sys.exit(1)

    filepath = sys.argv[1]
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    # Extract title from frontmatter
    title = ""
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].split('\n'):
                if line.startswith('title:'):
                    title = line.replace('title:', '').strip().strip('"').strip("'")
            body = parts[2]

    total, details, feedback = QualityScorer.score(title, body)
    print(QualityScorer.format_report(total, details, feedback))

    sys.exit(0 if details['passed'] else 1)


if __name__ == '__main__':
    main()
