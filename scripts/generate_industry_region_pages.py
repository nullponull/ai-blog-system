#!/usr/bin/env python3
"""
generate_industry_region_pages.py - 業界×地域 pSEOページ生成

SEOタイガー方式: テンプレート80%固定 + AI生成20%（短文ブリーフのみ）

Usage:
  python3 scripts/generate_industry_region_pages.py --priority 1          # 主要10都市
  python3 scripts/generate_industry_region_pages.py --priority 1 --batch 5  # 1日5ページ
  python3 scripts/generate_industry_region_pages.py --industry manufacturing --prefecture tokyo  # 1ページ
  python3 scripts/generate_industry_region_pages.py --dry-run --priority 1   # プレビュー
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yaml

PROJECT_ROOT = Path("/home/sol/ai-blog-system")
PAGES_DIR = PROJECT_ROOT / "_pages" / "ai-solutions"
DATA_DIR = PROJECT_ROOT / "_data" / "pseo"
BRIEFS_DIR = DATA_DIR / "briefs"

JST = timezone(timedelta(hours=9))


def load_data():
    """Load industries and prefectures from YAML."""
    with open(DATA_DIR / "industries.yml", encoding="utf-8") as f:
        industries = yaml.safe_load(f)
    with open(DATA_DIR / "prefectures.yml", encoding="utf-8") as f:
        prefectures = yaml.safe_load(f)
    return {i["id"]: i for i in industries}, {p["id"]: p for p in prefectures}


def generate_brief(industry: dict, prefecture: dict) -> dict:
    """Generate AI brief (the 20% AI-generated portion).

    Uses Gemini flash-lite for short text only (100-200 chars each).
    Falls back to empty strings if API unavailable.
    """
    brief = {"local_context": "", "challenge_summary": ""}

    try:
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from gemini_client import GeminiClient
        client = GeminiClient()

        prompt = f"""以下の条件で、2つの短文を生成してください。JSONで返してください。

【業界】{industry['name']}（AI導入率: {industry['ai_adoption_rate']}）
【地域】{prefecture['name']}（主要産業: {', '.join(prefecture['top_industries'])}）
【事業所数】約{prefecture['business_count']:,}社

生成する短文:
1. local_context: {prefecture['name']}の{industry['name']}の特徴を1-2文で（100-150文字）。地域固有の産業集積や特色に触れる。
2. challenge_summary: {prefecture['name']}の{industry['name']}がAI導入で得られる具体的効果を1文で（80-120文字）。

【条件】
- 具体的な地名や産業特性に言及する
- 一般論ではなく地域固有の情報
- 「革命的」等のAIクリシェ禁止
- 数字は入れなくてよい（正確性を担保できないため）"""

        schema = {
            "type": "OBJECT",
            "properties": {
                "local_context": {"type": "STRING"},
                "challenge_summary": {"type": "STRING"},
            },
            "required": ["local_context", "challenge_summary"],
        }

        result = client.call_json(prompt, schema=schema)
        if result:
            brief["local_context"] = result.get("local_context", "")[:200]
            brief["challenge_summary"] = result.get("challenge_summary", "")[:150]

        time.sleep(1)  # Rate limit
    except Exception as e:
        print(f"  [WARN] Brief generation failed: {e}. Using template-only page.")

    return brief


def generate_page(industry: dict, prefecture: dict, brief: dict) -> str:
    """Generate a Jekyll page file content."""
    now = datetime.now(JST)
    date_str = now.strftime("%Y-%m-%d %H:%M:%S +0900")

    title = f"{prefecture['name']}の{industry['name']}におけるAI活用ガイド【2026年版】"
    description = (
        f"{prefecture['name']}の{industry['name']}向けAI導入ガイド。"
        f"AI導入率{industry['ai_adoption_rate']}の業界で、"
        f"{industry['top_use_cases'][0]}など具体的な活用法を解説。"
    )

    tags = [industry["name"], "AI活用", prefecture["name"], "DX", "中小企業"]

    # Front matter with AI-generated briefs embedded
    local_ctx = brief.get("local_context", "").replace('"', '\\"')
    challenge_sum = brief.get("challenge_summary", "").replace('"', '\\"')
    tags_json = json.dumps(tags, ensure_ascii=False)
    ind_id = industry["id"]
    pref_id = prefecture["id"]

    frontmatter = f"""---
layout: pseo-industry-region
title: "{title}"
date: {date_str}
permalink: /ai-solutions/{ind_id}/{pref_id}/
description: "{description}"
industry_id: "{ind_id}"
prefecture_id: "{pref_id}"
tags: {tags_json}
author: "ALLFORCES編集部"
local_context: "{local_ctx}"
challenge_summary: "{challenge_sum}"
sitemap:
  priority: 0.7
  changefreq: monthly
---
"""
    return frontmatter


def main():
    parser = argparse.ArgumentParser(description="業界×地域 pSEOページ生成")
    parser.add_argument("--priority", type=int, choices=[1, 2, 3],
                        help="都道府県の優先度（1=主要10都市, 2=地方主要, 3=残り）")
    parser.add_argument("--industry", type=str, help="特定の業界ID")
    parser.add_argument("--prefecture", type=str, help="特定の都道府県ID")
    parser.add_argument("--batch", type=int, default=0,
                        help="バッチサイズ（0=全て）")
    parser.add_argument("--dry-run", action="store_true", help="プレビューのみ")
    parser.add_argument("--no-ai", action="store_true",
                        help="AI生成をスキップ（テンプレートのみ）")
    args = parser.parse_args()

    industries, prefectures = load_data()

    # Determine which pages to generate
    pairs = []
    for ind_id, ind in industries.items():
        for pref_id, pref in prefectures.items():
            if args.industry and ind_id != args.industry:
                continue
            if args.prefecture and pref_id != args.prefecture:
                continue
            if args.priority and pref.get("priority") != args.priority:
                continue
            pairs.append((ind, pref))

    # Filter out already-generated pages
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    existing = set()
    for f in PAGES_DIR.rglob("*.md"):
        existing.add(f.stem)

    new_pairs = []
    for ind, pref in pairs:
        page_stem = f"{ind['id']}_{pref['id']}"
        if page_stem not in existing:
            new_pairs.append((ind, pref))

    if args.batch > 0:
        new_pairs = new_pairs[:args.batch]

    print(f"対象: {len(new_pairs)}ページ（既存{len(existing)}ページをスキップ）")

    if not new_pairs:
        print("生成対象なし。")
        return

    generated = []
    for i, (ind, pref) in enumerate(new_pairs):
        label = f"{pref['name']}×{ind['name']}"
        print(f"\n[{i+1}/{len(new_pairs)}] {label}")

        if args.dry_run:
            print(f"  [DRY RUN] /ai-solutions/{ind['id']}/{pref['id']}/")
            continue

        # Generate brief (AI 20%)
        if args.no_ai:
            brief = {"local_context": "", "challenge_summary": ""}
        else:
            brief = generate_brief(ind, pref)
            if brief["local_context"]:
                print(f"  Brief: {brief['local_context'][:60]}...")

        # Generate page content
        content = generate_page(ind, pref, brief)

        # Save
        page_dir = PAGES_DIR / ind["id"]
        page_dir.mkdir(parents=True, exist_ok=True)
        filepath = page_dir / f"{pref['id']}.md"
        filepath.write_text(content, encoding="utf-8")

        print(f"  SAVED: {filepath.relative_to(PROJECT_ROOT)}")
        generated.append(f"/ai-solutions/{ind['id']}/{pref['id']}/")

    print(f"\n--- 結果 ---")
    print(f"生成: {len(generated)}ページ")
    for url in generated:
        print(f"  {url}")


if __name__ == "__main__":
    main()
