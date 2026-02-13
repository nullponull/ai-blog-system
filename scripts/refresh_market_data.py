#!/usr/bin/env python3
"""
Refresh market data in the knowledge base using Gemini API with Web Search.
Updates _data/market/*.yml files with latest information.

Usage:
  python3 scripts/refresh_market_data.py                    # Update all
  python3 scripts/refresh_market_data.py --section companies # Update specific section
  python3 scripts/refresh_market_data.py --dry-run          # Preview only
"""

import argparse
import os
import sys
import yaml
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gemini_client import GeminiClient

JST = timezone(timedelta(hours=9))


def get_market_dir():
    """Get the _data/market/ directory path."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(os.path.dirname(script_dir), '_data', 'market')


def load_yaml(filepath):
    """Load a YAML file."""
    if not os.path.exists(filepath):
        return None
    with open(filepath, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(filepath, data, comment=""):
    """Save data to a YAML file with optional header comment."""
    with open(filepath, 'w', encoding='utf-8') as f:
        if comment:
            f.write(f"# {comment}\n")
        f.write(f"# Updated: {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}\n\n")
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def refresh_companies(client, market_dir, dry_run=False):
    """Refresh company data in batches of 5."""
    print("Refreshing companies...", file=sys.stderr)
    filepath = os.path.join(market_dir, 'companies.yml')
    existing = load_yaml(filepath) or []

    # Process in batches
    company_ids = [c.get('id', '') for c in existing]
    batch_size = 5

    for i in range(0, len(company_ids), batch_size):
        batch = company_ids[i:i+batch_size]
        batch_names = [c.get('name', c.get('id', '')) for c in existing[i:i+batch_size]]

        prompt = f"""以下のAI企業の最新情報を提供してください。各企業について:
- 最新の評価額/時価総額
- 直近の売上/収益
- 新製品・サービスのリリース
- 重要な提携やニュース

企業: {', '.join(batch_names)}

JSON形式で、各企業のrecent_newsフィールド(date, headline)を含めて返してください。
情報は{datetime.now().strftime('%Y年%m月')}時点の最新のものを使用。"""

        if dry_run:
            print(f"  [DRY RUN] Would update: {', '.join(batch)}", file=sys.stderr)
            continue

        result = client.call_json_with_search(prompt)
        if result:
            # Merge updates into existing data
            if isinstance(result, list):
                for update in result:
                    uid = update.get('id', '')
                    for j, company in enumerate(existing):
                        if company.get('id') == uid or company.get('name') == update.get('name'):
                            # Update recent_news
                            if 'recent_news' in update:
                                existing[j]['recent_news'] = update['recent_news'][:3]
                            # Update financials if provided
                            for key in ['valuation_usd', 'revenue_annual_usd', 'market_cap_usd']:
                                if key in update and update[key]:
                                    existing[j][key] = update[key]
                            break
            print(f"  Updated batch: {', '.join(batch)}", file=sys.stderr)

    if not dry_run:
        save_yaml(filepath, existing, "AI主要企業プロフィール")
    return True


def refresh_market_sizes(client, market_dir, dry_run=False):
    """Refresh market size data."""
    print("Refreshing market sizes...", file=sys.stderr)
    filepath = os.path.join(market_dir, 'market_sizes.yml')

    prompt = f"""AI市場規模の最新データを提供してください。以下の情報を含めて:

1. グローバルAI市場規模（現在と予測）
2. 生成AI市場規模（現在と予測）
3. 日本AI市場規模（円とドル）
4. AI投資額（VC投資、設備投資）
5. セグメント別市場（生成AI、AIエージェント、AIチップ、クラウドAI、自動運転、AIヘルスケア）

{datetime.now().strftime('%Y年%m月')}時点の最新データを使用。
YAML形式で出力してください。"""

    if dry_run:
        print("  [DRY RUN] Would update market sizes", file=sys.stderr)
        return True

    result = client.call_with_search(prompt)
    if result:
        try:
            data = yaml.safe_load(result)
            if data:
                save_yaml(filepath, data, "AI市場規模データ")
                print("  Market sizes updated", file=sys.stderr)
                return True
        except yaml.YAMLError:
            print("  Warning: Could not parse market size response as YAML", file=sys.stderr)

    return False


def refresh_benchmarks(client, market_dir, dry_run=False):
    """Refresh LLM and GPU benchmark data."""
    print("Refreshing benchmarks...", file=sys.stderr)
    filepath = os.path.join(market_dir, 'benchmarks.yml')

    prompt = f"""AI関連のベンチマークデータの最新情報を提供してください。

1. LLMベンチマーク: 主要モデル(GPT-5, GPT-4o, Claude Opus, Gemini 3 Pro, DeepSeek R1, Llama 3等)の
   MMLU, HumanEval, SWE-bench, Arenaスコア
2. GPU性能: NVIDIA B200, H200, H100, AMD MI300X等のスペック

{datetime.now().strftime('%Y年%m月')}時点の最新データを使用。
YAML形式で出力してください。"""

    if dry_run:
        print("  [DRY RUN] Would update benchmarks", file=sys.stderr)
        return True

    result = client.call_with_search(prompt)
    if result:
        try:
            data = yaml.safe_load(result)
            if data:
                save_yaml(filepath, data, "LLMベンチマーク・GPU性能データ")
                print("  Benchmarks updated", file=sys.stderr)
                return True
        except yaml.YAMLError:
            print("  Warning: Could not parse benchmark response as YAML", file=sys.stderr)

    return False


def refresh_pricing(client, market_dir, dry_run=False):
    """Refresh API pricing data."""
    print("Refreshing pricing...", file=sys.stderr)
    filepath = os.path.join(market_dir, 'pricing.yml')

    prompt = f"""AI API の最新価格表を提供してください。

プロバイダー: OpenAI, Anthropic, Google, DeepSeek, Mistral
各モデルについて: モデル名、入力/出力の1Mトークン当たり価格、コンテキストウィンドウ

{datetime.now().strftime('%Y年%m月')}時点の最新の公式価格を使用。
YAML形式で出力してください。"""

    if dry_run:
        print("  [DRY RUN] Would update pricing", file=sys.stderr)
        return True

    result = client.call_with_search(prompt)
    if result:
        try:
            data = yaml.safe_load(result)
            if data:
                save_yaml(filepath, data, "AI API価格比較表")
                print("  Pricing updated", file=sys.stderr)
                return True
        except yaml.YAMLError:
            print("  Warning: Could not parse pricing response as YAML", file=sys.stderr)

    return False


def update_last_updated(market_dir, sections):
    """Update the _last_updated.yml file."""
    filepath = os.path.join(market_dir, '_last_updated.yml')
    data = load_yaml(filepath) or {}

    now_str = datetime.now(JST).strftime('%Y-%m-%d')

    for section in sections:
        if section not in data:
            data[section] = {}
        data[section]['updated'] = now_str
        data[section]['source'] = 'Gemini API Web Search'

    save_yaml(filepath, data, "ナレッジベース更新履歴")


def main():
    parser = argparse.ArgumentParser(
        description='Refresh market data knowledge base'
    )
    parser.add_argument('--section', choices=['companies', 'market_sizes', 'benchmarks', 'pricing', 'all'],
                        default='all', help='Section to refresh')
    parser.add_argument('--dry-run', action='store_true', help='Preview only')
    args = parser.parse_args()

    market_dir = get_market_dir()
    if not os.path.isdir(market_dir):
        print(f"ERROR: Market data directory not found: {market_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        client = GeminiClient()
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    sections_updated = []

    if args.section in ('all', 'companies'):
        if refresh_companies(client, market_dir, args.dry_run):
            sections_updated.append('companies')

    if args.section in ('all', 'market_sizes'):
        if refresh_market_sizes(client, market_dir, args.dry_run):
            sections_updated.append('market_sizes')

    if args.section in ('all', 'benchmarks'):
        if refresh_benchmarks(client, market_dir, args.dry_run):
            sections_updated.append('benchmarks')

    if args.section in ('all', 'pricing'):
        if refresh_pricing(client, market_dir, args.dry_run):
            sections_updated.append('pricing')

    if sections_updated and not args.dry_run:
        update_last_updated(market_dir, sections_updated)

    print(f"\nRefresh complete. Updated: {', '.join(sections_updated) or 'none'}", file=sys.stderr)


if __name__ == '__main__':
    main()
