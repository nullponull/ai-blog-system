#!/usr/bin/env python3
"""
Apply research findings to the knowledge base.
Merges kb_updates from _data/research/*.yml into _data/market/*.yml.

Usage:
  python3 scripts/apply_research_to_kb.py                   # Apply all recent research
  python3 scripts/apply_research_to_kb.py --dry-run          # Preview changes
  python3 scripts/apply_research_to_kb.py --file FILE.yml    # Apply specific research file
"""

import argparse
import os
import sys
import yaml
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))


def get_dirs():
    """Get research and market directories."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    research_dir = os.path.join(project_dir, '_data', 'research')
    market_dir = os.path.join(project_dir, '_data', 'market')
    return research_dir, market_dir


def load_yaml(filepath):
    """Load a YAML file safely."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"  Error loading {filepath}: {e}", file=sys.stderr)
        return None


def save_yaml(filepath, data):
    """Save data to YAML file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"# Updated: {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}\n\n")
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def merge_company_updates(existing_companies, updates):
    """Merge company updates into existing companies.yml data.

    Args:
        existing_companies: List of company dicts from companies.yml
        updates: List of company update dicts from kb_updates.companies

    Returns:
        Updated companies list, number of changes made
    """
    if not updates:
        return existing_companies, 0

    changes = 0
    company_map = {c.get('id', ''): c for c in existing_companies}

    for update in updates:
        company_id = update.get('id', '')
        if not company_id:
            continue

        if company_id in company_map:
            company = company_map[company_id]

            # Update recent_news (prepend new items, deduplicate)
            new_news = update.get('recent_news', [])
            if new_news:
                existing_headlines = {n.get('headline', '') for n in company.get('recent_news', [])}
                for news in new_news:
                    if news.get('headline', '') not in existing_headlines:
                        company.setdefault('recent_news', []).insert(0, news)
                        changes += 1
                # Keep only 5 most recent
                company['recent_news'] = company.get('recent_news', [])[:5]

            # Update valuation
            if update.get('valuation_usd'):
                if company.get('valuation_usd') != update['valuation_usd']:
                    company['valuation_usd'] = update['valuation_usd']
                    changes += 1

            # Update revenue
            if update.get('revenue_annual_usd'):
                if company.get('revenue_annual_usd') != update['revenue_annual_usd']:
                    company['revenue_annual_usd'] = update['revenue_annual_usd']
                    changes += 1

            # Update key_products (merge new ones)
            new_products = update.get('key_products', [])
            if new_products:
                existing_names = {p.get('name', '') for p in company.get('key_products', [])}
                for product in new_products:
                    if product.get('name', '') not in existing_names:
                        company.setdefault('key_products', []).append(product)
                        changes += 1

            # Update partnerships (merge new ones)
            new_partners = update.get('partnerships', [])
            if new_partners:
                existing_partners = set(company.get('partnerships', []))
                for partner in new_partners:
                    if partner not in existing_partners:
                        company.setdefault('partnerships', []).append(partner)
                        changes += 1

    return list(company_map.values()), changes


def merge_market_updates(existing_market, updates):
    """Merge market size updates.

    Args:
        existing_market: Dict from market_sizes.yml
        updates: Dict from kb_updates.market_sizes

    Returns:
        Updated market dict, number of changes
    """
    if not updates or not existing_market:
        return existing_market or {}, 0

    changes = 0

    # Update global AI market
    if 'global_ai_market' in updates:
        for key in ('current', 'forecast'):
            if key in updates['global_ai_market']:
                if existing_market.get('global_ai_market', {}).get(key) != updates['global_ai_market'][key]:
                    existing_market.setdefault('global_ai_market', {})[key] = updates['global_ai_market'][key]
                    changes += 1

    # Update generative AI market
    if 'generative_ai_market' in updates:
        for key in ('current', 'forecast'):
            if key in updates['generative_ai_market']:
                existing_market.setdefault('generative_ai_market', {})[key] = updates['generative_ai_market'][key]
                changes += 1

    # Update Japan market
    if 'japan_ai_market' in updates:
        for key in ('current', 'forecast'):
            if key in updates['japan_ai_market']:
                existing_market.setdefault('japan_ai_market', {})[key] = updates['japan_ai_market'][key]
                changes += 1

    return existing_market, changes


def merge_benchmark_updates(existing_benchmarks, updates):
    """Merge benchmark updates.

    Args:
        existing_benchmarks: Dict from benchmarks.yml
        updates: Dict from kb_updates.benchmarks

    Returns:
        Updated benchmarks dict, number of changes
    """
    if not updates or not existing_benchmarks:
        return existing_benchmarks or {}, 0

    changes = 0

    # Update LLM benchmarks
    new_llm = updates.get('llm_benchmarks', [])
    if new_llm:
        existing_models = {m.get('model', ''): m for m in existing_benchmarks.get('llm_benchmarks', [])}
        for bench in new_llm:
            model_name = bench.get('model', '')
            if model_name:
                if model_name in existing_models:
                    # Update existing
                    for key in ('mmlu', 'humaneval', 'math', 'gpqa', 'provider'):
                        if bench.get(key) and existing_models[model_name].get(key) != bench[key]:
                            existing_models[model_name][key] = bench[key]
                            changes += 1
                else:
                    # Add new model
                    existing_benchmarks.setdefault('llm_benchmarks', []).append(bench)
                    changes += 1

    return existing_benchmarks, changes


def apply_research_file(research_filepath, market_dir, dry_run=False):
    """Apply a single research file's kb_updates to the knowledge base.

    Args:
        research_filepath: Path to research YAML file
        market_dir: Path to _data/market/ directory
        dry_run: If True, only preview changes

    Returns:
        Total number of changes applied
    """
    research = load_yaml(research_filepath)
    if not research:
        return 0

    kb_updates = research.get('kb_updates', {})
    if not kb_updates:
        print(f"  No kb_updates in {os.path.basename(research_filepath)}", file=sys.stderr)
        return 0

    total_changes = 0
    filename = os.path.basename(research_filepath)

    # Companies
    company_updates = kb_updates.get('companies', [])
    if company_updates:
        companies_path = os.path.join(market_dir, 'companies.yml')
        existing = load_yaml(companies_path) or []
        updated, changes = merge_company_updates(existing, company_updates)
        if changes > 0:
            print(f"  {filename} -> companies.yml: {changes} updates", file=sys.stderr)
            if not dry_run:
                save_yaml(companies_path, updated)
            total_changes += changes

    # Market sizes
    market_updates = kb_updates.get('market_sizes', {})
    if market_updates:
        market_path = os.path.join(market_dir, 'market_sizes.yml')
        existing = load_yaml(market_path) or {}
        updated, changes = merge_market_updates(existing, market_updates)
        if changes > 0:
            print(f"  {filename} -> market_sizes.yml: {changes} updates", file=sys.stderr)
            if not dry_run:
                save_yaml(market_path, updated)
            total_changes += changes

    # Benchmarks
    bench_updates = kb_updates.get('benchmarks', {})
    if bench_updates:
        bench_path = os.path.join(market_dir, 'benchmarks.yml')
        existing = load_yaml(bench_path) or {}
        updated, changes = merge_benchmark_updates(existing, bench_updates)
        if changes > 0:
            print(f"  {filename} -> benchmarks.yml: {changes} updates", file=sys.stderr)
            if not dry_run:
                save_yaml(bench_path, updated)
            total_changes += changes

    # Update _last_updated.yml
    if total_changes > 0 and not dry_run:
        last_updated_path = os.path.join(market_dir, '_last_updated.yml')
        last_updated = load_yaml(last_updated_path) or {}
        now_str = datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')
        last_updated['last_research_applied'] = now_str
        last_updated['research_source'] = filename
        save_yaml(last_updated_path, last_updated)

    return total_changes


def apply_all_research(research_dir, market_dir, dry_run=False, max_age_days=3):
    """Apply all recent research files to the knowledge base.

    Args:
        research_dir: Path to _data/research/ directory
        market_dir: Path to _data/market/ directory
        dry_run: Preview only
        max_age_days: Max age of research files to apply

    Returns:
        Total changes across all files
    """
    if not os.path.isdir(research_dir):
        print(f"Research directory not found: {research_dir}", file=sys.stderr)
        return 0

    cutoff = datetime.now() - timedelta(days=max_age_days)
    total = 0

    import re
    for filename in sorted(os.listdir(research_dir)):
        if not filename.endswith('.yml') or filename.startswith('.'):
            continue

        match = re.match(r'(\d{4}-\d{2}-\d{2})', filename)
        if match:
            try:
                file_date = datetime.strptime(match.group(1), '%Y-%m-%d')
                if file_date < cutoff:
                    continue
            except ValueError:
                continue

        filepath = os.path.join(research_dir, filename)
        changes = apply_research_file(filepath, market_dir, dry_run)
        total += changes

    action = "Would apply" if dry_run else "Applied"
    print(f"\n{action} {total} total changes to knowledge base", file=sys.stderr)
    return total


def main():
    parser = argparse.ArgumentParser(description='Apply research to knowledge base')
    parser.add_argument('--file', help='Specific research YAML file to apply')
    parser.add_argument('--dry-run', action='store_true', help='Preview changes only')
    parser.add_argument('--max-age', type=int, default=3, help='Max age in days (default: 3)')
    args = parser.parse_args()

    research_dir, market_dir = get_dirs()

    if args.file:
        filepath = args.file
        if not os.path.isabs(filepath):
            filepath = os.path.join(research_dir, filepath)
        changes = apply_research_file(filepath, market_dir, dry_run=args.dry_run)
    else:
        changes = apply_all_research(research_dir, market_dir,
                                     dry_run=args.dry_run,
                                     max_age_days=args.max_age)

    return 0 if changes >= 0 else 1


if __name__ == '__main__':
    sys.exit(main())
