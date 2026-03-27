#!/usr/bin/env python3
"""
generate_hub_pages.py - 業界別ハブページ生成

各業界の地域一覧ページを生成する。100%テンプレート固定（AI生成ゼロ）。

Usage:
  python3 scripts/generate_hub_pages.py
"""

from pathlib import Path
import yaml

PROJECT_ROOT = Path("/home/sol/ai-blog-system")
PAGES_DIR = PROJECT_ROOT / "_pages" / "ai-solutions"
DATA_DIR = PROJECT_ROOT / "_data" / "pseo"


def main():
    with open(DATA_DIR / "industries.yml", encoding="utf-8") as f:
        industries = yaml.safe_load(f)

    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    generated = []

    for ind in industries:
        filepath = PAGES_DIR / f"{ind['id']}.html"
        content = f"""---
layout: default
title: "{ind['display_name']}ガイド | 地域別AI導入状況 | AIコンパス"
description: "{ind['name']}のAI導入率は{ind['ai_adoption_rate']}。全国の地域別に{ind['name']}のAI活用状況・課題・ソリューションを解説。"
permalink: /ai-solutions/{ind['id']}/
sitemap:
  priority: 0.8
  changefreq: weekly
---

<div class="pseo-hub">
  <nav class="breadcrumb">
    <a href="/">ホーム</a> &gt;
    <a href="/ai-solutions/">AI導入ガイド</a> &gt;
    <span>{ind['display_name']}</span>
  </nav>

  <h1>{ind['display_name']}ガイド</h1>

  <div class="pseo-hub-stats">
    <div class="pseo-stat">
      <span class="pseo-stat-num">{ind['ai_adoption_rate']}</span>
      <span class="pseo-stat-label">AI導入率</span>
    </div>
    <div class="pseo-stat">
      <span class="pseo-stat-num">{ind['company_count']:,}</span>
      <span class="pseo-stat-label">調査対象企業</span>
    </div>
  </div>

  <section>
    <h2>{ind['name']}の主要課題</h2>
    <ul>
"""
        for ch in ind["top_challenges"]:
            content += f"      <li>{ch}</li>\n"

        content += f"""    </ul>
    <p class="pseo-source">出典: {ind['source']}</p>
  </section>

  <section>
    <h2>AI活用の主なユースケース</h2>
    <ul>
"""
        for uc in ind["top_use_cases"]:
            content += f"      <li>{uc}</li>\n"

        content += f"""    </ul>
  </section>

  <section>
    <h2>地域別ガイド</h2>
    <p>{ind['name']}のAI活用を地域ごとにまとめています。</p>
    <div class="pseo-region-grid">
      {{% for pref in site.data.pseo.prefectures %}}
      <a href="/ai-solutions/{ind['id']}/{{{{ pref.id }}}}/" class="pseo-region-link">
        {{{{ pref.name }}}}
      </a>
      {{% endfor %}}
    </div>
  </section>

  <section>
    <h2>関連する補助金</h2>
    <ul>
"""
        for sub in ind.get("related_subsidies", []):
            content += f"      <li>{sub}</li>\n"

        content += f"""    </ul>
    <p class="pseo-note">※ 公募状況は年度により変更されます。最新情報は各省庁サイトをご確認ください。</p>
  </section>

  <section class="pseo-cta">
    <h2>{ind['name']}のAI導入をご検討の方へ</h2>
    <a href="/contact/" class="pseo-cta-button">無料相談はこちら</a>
    <p><a href="/ai-solutions/">他の業界を見る</a></p>
  </section>
</div>
"""
        filepath.write_text(content, encoding="utf-8")
        generated.append(f"/ai-solutions/{ind['id']}/")
        print(f"  SAVED: {filepath.relative_to(PROJECT_ROOT)}")

    print(f"\n生成: {len(generated)} ハブページ")


if __name__ == "__main__":
    main()
