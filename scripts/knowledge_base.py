#!/usr/bin/env python3
"""
Knowledge Base loader and query utility.
Reads YAML files from _data/market/ and provides structured access
for article generation prompts.
"""

import os
import sys
import yaml
from datetime import datetime


class KnowledgeBase:
    """Load and query market data from _data/market/ YAML files."""

    def __init__(self, base_dir=None):
        """Initialize with path to the project root or _data/market/ directory."""
        if base_dir is None:
            # Auto-detect: look for _data/market/ relative to scripts/
            script_dir = os.path.dirname(os.path.abspath(__file__))
            base_dir = os.path.join(os.path.dirname(script_dir), '_data', 'market')
        elif not base_dir.endswith(os.path.join('_data', 'market')):
            base_dir = os.path.join(base_dir, '_data', 'market')

        self.base_dir = base_dir
        self._cache = {}

    def _load(self, filename):
        """Load a YAML file from the knowledge base directory."""
        if filename in self._cache:
            return self._cache[filename]

        filepath = os.path.join(self.base_dir, filename)
        if not os.path.exists(filepath):
            print(f"  [KB] File not found: {filepath}", file=sys.stderr)
            return None

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            self._cache[filename] = data
            return data
        except Exception as e:
            print(f"  [KB] Error loading {filename}: {e}", file=sys.stderr)
            return None

    def get_companies(self):
        """Get all company profiles."""
        return self._load('companies.yml') or []

    def get_company(self, company_id):
        """Get a specific company by ID."""
        for company in self.get_companies():
            if company.get('id') == company_id:
                return company
        return None

    def get_companies_by_ids(self, ids):
        """Get multiple companies by their IDs."""
        companies = self.get_companies()
        return [c for c in companies if c.get('id') in ids]

    def get_market_sizes(self):
        """Get market size data."""
        return self._load('market_sizes.yml') or {}

    def get_benchmarks(self):
        """Get LLM/GPU benchmark data."""
        return self._load('benchmarks.yml') or {}

    def get_trends(self):
        """Get current trends data."""
        return self._load('trends.yml') or {}

    def get_pricing(self):
        """Get AI API pricing data."""
        return self._load('pricing.yml') or {}

    def get_last_updated(self):
        """Get last update timestamps."""
        return self._load('_last_updated.yml') or {}

    def format_company_context(self, company_ids=None):
        """Format company data for prompt injection.

        Args:
            company_ids: List of company IDs to include, or None for all

        Returns:
            Formatted string for prompt injection
        """
        if company_ids:
            companies = self.get_companies_by_ids(company_ids)
        else:
            companies = self.get_companies()

        if not companies:
            return ""

        lines = []
        for c in companies:
            name = c.get('name', c.get('id', 'Unknown'))
            parts = [f"■ {name}"]

            if c.get('valuation_usd'):
                parts.append(f"評価額${c['valuation_usd']}")
            if c.get('revenue_annual_usd'):
                parts.append(f"年間売上${c['revenue_annual_usd']}")

            line = ": ".join([parts[0], ", ".join(parts[1:])]) if len(parts) > 1 else parts[0]
            lines.append(line)

            # Key products
            products = c.get('key_products', [])
            if products:
                prod_strs = [f"{p['name']}({p.get('type', '')})" for p in products[:4]]
                lines.append(f"  主力製品: {', '.join(prod_strs)}")

            # Recent news
            news = c.get('recent_news', [])
            if news:
                latest = news[0]
                lines.append(f"  最新: {latest.get('date', '')} {latest.get('headline', '')}")

            # Partnerships
            partners = c.get('partnerships', [])
            if partners:
                lines.append(f"  提携: {', '.join(partners[:5])}")

        return "\n".join(lines)

    def format_market_context(self):
        """Format market size data for prompt injection."""
        data = self.get_market_sizes()
        if not data:
            return ""

        lines = []

        # Global AI market
        global_data = data.get('global_ai_market', {})
        if global_data:
            current = global_data.get('current', {})
            forecast = global_data.get('forecast', {})
            if current:
                lines.append(f"■ AI市場規模: {current.get('year', '')}年 ${current.get('size_usd', '')}")
            if forecast:
                lines.append(f"  予測: {forecast.get('year', '')}年 ${forecast.get('size_usd', '')} (CAGR {forecast.get('cagr', '')})")

        # Generative AI
        gen_ai = data.get('generative_ai_market', {})
        if gen_ai:
            current = gen_ai.get('current', {})
            if current:
                lines.append(f"■ 生成AI市場: {current.get('year', '')}年 ${current.get('size_usd', '')}")

        # Japan AI market
        japan = data.get('japan_ai_market', {})
        if japan:
            current = japan.get('current', {})
            if current:
                lines.append(f"■ 日本AI市場: {current.get('year', '')}年 {current.get('size_jpy', '')}")

        # Segments
        segments = data.get('segments', [])
        if segments:
            lines.append("■ セグメント別:")
            for seg in segments[:5]:
                lines.append(f"  {seg.get('name', '')}: ${seg.get('size_usd', '')} ({seg.get('growth', '')})")

        return "\n".join(lines)

    def format_benchmark_context(self, model_names=None):
        """Format benchmark data for prompt injection."""
        data = self.get_benchmarks()
        if not data:
            return ""

        lines = []

        # LLM benchmarks
        llm_benchmarks = data.get('llm_benchmarks', [])
        if llm_benchmarks:
            models = llm_benchmarks
            if model_names:
                models = [m for m in models if m.get('model') in model_names]

            lines.append("■ LLMベンチマーク:")
            for m in models[:8]:
                scores = []
                if m.get('mmlu'):
                    scores.append(f"MMLU:{m['mmlu']}")
                if m.get('humaneval'):
                    scores.append(f"HumanEval:{m['humaneval']}")
                if m.get('math'):
                    scores.append(f"MATH:{m['math']}")
                if scores:
                    lines.append(f"  {m.get('model', 'Unknown')}: {', '.join(scores)}")

        # GPU benchmarks
        gpu_benchmarks = data.get('gpu_benchmarks', [])
        if gpu_benchmarks:
            lines.append("■ GPU性能:")
            for g in gpu_benchmarks[:5]:
                specs = []
                if g.get('memory'):
                    specs.append(f"{g['memory']}")
                if g.get('tflops_fp16'):
                    specs.append(f"FP16:{g['tflops_fp16']}TFLOPS")
                if specs:
                    lines.append(f"  {g.get('name', 'Unknown')}: {', '.join(specs)}")

        return "\n".join(lines)

    def format_pricing_context(self):
        """Format API pricing data for prompt injection."""
        data = self.get_pricing()
        if not data:
            return ""

        lines = ["■ AI API価格比較:"]

        providers = data.get('providers', [])
        for provider in providers:
            name = provider.get('name', '')
            models = provider.get('models', [])
            for model in models[:3]:
                input_price = model.get('input_per_1m_tokens', '?')
                output_price = model.get('output_per_1m_tokens', '?')
                lines.append(f"  {name} {model.get('name', '')}: 入力${input_price}/1M, 出力${output_price}/1M")

        return "\n".join(lines)

    def format_trends_context(self):
        """Format trends data for prompt injection."""
        data = self.get_trends()
        if not data:
            return ""

        lines = []

        # Hot technologies
        hot_tech = data.get('hot_technologies', [])
        if hot_tech:
            lines.append("■ 注目技術:")
            for tech in hot_tech[:5]:
                lines.append(f"  - {tech.get('name', '')}: {tech.get('description', '')}")

        # Investment highlights
        investments = data.get('investments', [])
        if investments:
            lines.append("■ 投資動向:")
            for inv in investments[:5]:
                lines.append(f"  - {inv.get('company', '')}: {inv.get('amount', '')} ({inv.get('description', '')})")

        # Regulatory
        regulatory = data.get('regulatory', [])
        if regulatory:
            lines.append("■ 規制動向:")
            for reg in regulatory[:3]:
                lines.append(f"  - {reg.get('region', '')}: {reg.get('description', '')}")

        return "\n".join(lines)

    def build_prompt_context(self, company_ids=None, include_market=True,
                            include_benchmarks=True, include_pricing=False,
                            include_trends=True):
        """Build complete knowledge base context for prompt injection.

        Returns a formatted string ready to be inserted into a generation prompt.
        """
        sections = []

        sections.append("【参照データ（ナレッジベース）】")

        company_ctx = self.format_company_context(company_ids)
        if company_ctx:
            sections.append(company_ctx)

        if include_market:
            market_ctx = self.format_market_context()
            if market_ctx:
                sections.append(market_ctx)

        if include_benchmarks:
            bench_ctx = self.format_benchmark_context()
            if bench_ctx:
                sections.append(bench_ctx)

        if include_pricing:
            price_ctx = self.format_pricing_context()
            if price_ctx:
                sections.append(price_ctx)

        if include_trends:
            trends_ctx = self.format_trends_context()
            if trends_ctx:
                sections.append(trends_ctx)

        sections.append("")
        sections.append("【指示】上記データは事実として使用可。最新情報はWeb検索で補完すること。")
        sections.append("数値は「〜によると」「〜年時点で」のように出典を明示すること。")

        return "\n\n".join(sections)


def main():
    """CLI: knowledge_base.py [--companies] [--market] [--benchmarks] [--pricing] [--trends] [--all]"""
    import argparse

    parser = argparse.ArgumentParser(description='Query the knowledge base')
    parser.add_argument('--base-dir', help='Path to project root')
    parser.add_argument('--companies', nargs='*', help='Show company data (optionally filter by IDs)')
    parser.add_argument('--market', action='store_true', help='Show market size data')
    parser.add_argument('--benchmarks', action='store_true', help='Show benchmark data')
    parser.add_argument('--pricing', action='store_true', help='Show pricing data')
    parser.add_argument('--trends', action='store_true', help='Show trends data')
    parser.add_argument('--all', action='store_true', help='Show full prompt context')
    args = parser.parse_args()

    kb = KnowledgeBase(args.base_dir)

    if args.all:
        print(kb.build_prompt_context())
    else:
        if args.companies is not None:
            ids = args.companies if args.companies else None
            print(kb.format_company_context(ids))
        if args.market:
            print(kb.format_market_context())
        if args.benchmarks:
            print(kb.format_benchmark_context())
        if args.pricing:
            print(kb.format_pricing_context())
        if args.trends:
            print(kb.format_trends_context())


if __name__ == '__main__':
    main()
