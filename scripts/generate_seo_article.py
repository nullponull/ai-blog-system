#!/usr/bin/env python3
"""
商用キーワード SEO記事生成

AI導入検討者が検索する商用キーワードを狙った記事を生成し、
Jekyll形式で _posts/ に保存する。問い合わせCTAを自動挿入。

Usage:
  python3 generate_seo_article.py                        # ランダムにキーワード選択
  python3 generate_seo_article.py --keyword "AI導入 費用"  # キーワード指定
  python3 generate_seo_article.py --batch 5              # 5記事一括生成
  python3 generate_seo_article.py --list                 # キーワード一覧表示
"""

import json
import subprocess
import sys
import os
import random
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
POSTS_DIR = PROJECT_ROOT / '_posts'

# 商用キーワード（AI導入検討者が検索するワード）
SEO_KEYWORDS = [
    {"keyword": "AI導入 費用 相場", "intent": "費用感を知りたい", "category": "ai-consulting"},
    {"keyword": "AIエージェント 開発 依頼", "intent": "開発会社を探している", "category": "ai-development"},
    {"keyword": "DX コンサル 比較", "intent": "DX支援会社を比較したい", "category": "dx-consulting"},
    {"keyword": "AI 業務効率化 事例", "intent": "導入事例を参考にしたい", "category": "ai-case-study"},
    {"keyword": "ChatGPT 業務活用 方法", "intent": "ChatGPTを業務に使いたい", "category": "ai-tools"},
    {"keyword": "AI音声合成 企業 導入", "intent": "音声合成を導入したい", "category": "ai-voice"},
    {"keyword": "RAG システム 構築 費用", "intent": "RAG導入を検討中", "category": "ai-development"},
    {"keyword": "AI開発会社 選び方", "intent": "開発パートナーを探している", "category": "ai-consulting"},
    {"keyword": "社内DX 進め方 ステップ", "intent": "DXの始め方を知りたい", "category": "dx-consulting"},
    {"keyword": "AI導入 失敗 原因", "intent": "失敗を避けたい", "category": "ai-consulting"},
    {"keyword": "AIチャットボット 開発 費用", "intent": "チャットボット導入検討", "category": "ai-development"},
    {"keyword": "業務自動化 AI ツール", "intent": "自動化ツールを探している", "category": "ai-tools"},
    {"keyword": "AI 画像認識 導入 製造業", "intent": "製造業でのAI活用", "category": "ai-case-study"},
    {"keyword": "VR 研修 導入 効果", "intent": "VR研修を検討中", "category": "vr-training"},
    {"keyword": "AI POC 進め方", "intent": "AI導入の第一歩を知りたい", "category": "ai-consulting"},
]

# Jekyll記事テンプレート
FRONT_MATTER_TEMPLATE = """---
layout: post
title: "{title}"
date: {date}
categories: [{category}]
tags: [{tags}]
description: "{description}"
seo_keyword: "{keyword}"
---

"""

CTA_BLOCK = """
---

## AI導入・DXのご相談

この記事の内容について、より詳しく知りたい方や、貴社での導入を検討されている方は、お気軽にご相談ください。15年以上のIT業界経験と、AI音声合成・VR・業務自動化の実績をもとに、最適なソリューションをご提案します。

{% include consulting-cta.html position="post" %}
"""


def generate_article(keyword_info):
    """Claude CLI で SEO記事を生成"""
    keyword = keyword_info['keyword']
    intent = keyword_info['intent']

    prompt = f"""あなたはAI/DX分野のSEOライターです。以下のキーワードで検索する人向けの記事を書いてください。

【ターゲットキーワード】
{keyword}

【検索意図】
{intent}

【記事の要件】
- 2000〜3000文字の実用的な記事
- H2見出しを4-6個使用
- 具体的な数字・事例を含める（一般的な市場データ）
- 専門用語には簡単な説明を添える
- 読者がすぐ行動できるチェックリストや手順を含める
- 「です・ます調」
- SEO: キーワードを自然に3-5回使用、共起語も意識

【構成テンプレート】
## はじめに（検索意図に直接回答）
## [本題1]
## [本題2]
## [本題3]
## よくある質問
## まとめ

Markdown形式で本文のみ出力してください。front matterは不要です。"""

    env = os.environ.copy()
    env['PATH'] = '/home/sol/.local/bin:/home/sol/.nvm/versions/node/v22.17.0/bin:/usr/local/bin:/usr/bin:/bin'

    for attempt in range(3):
        try:
            result = subprocess.run(
                ['claude', '-p', prompt],
                capture_output=True, text=True, timeout=120,
                env=env,
            )
            if result.returncode != 0:
                print(f"  生成失敗 (attempt {attempt + 1})")
                continue

            content = result.stdout.strip()
            if content and len(content) > 500:
                return content
        except subprocess.TimeoutExpired:
            print(f"  タイムアウト (attempt {attempt + 1})")

    return None


def save_article(keyword_info, content):
    """Jekyll形式で記事を保存"""
    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime('%Y-%m-%d')
    keyword_slug = keyword_info['keyword'].replace(' ', '-').replace('　', '-')

    # タイトルを本文の最初のH2から推測、またはキーワードベース
    title = f"{keyword_info['keyword']}｜実践ガイド{datetime.now().year}"
    description = f"{keyword_info['keyword']}について、{keyword_info['intent']}方に向けて、具体的な手順と事例を解説します。"

    tags = keyword_info['keyword'].replace('　', ' ').split(' ')
    tags_str = ', '.join(tags[:5])

    front_matter = FRONT_MATTER_TEMPLATE.format(
        title=title,
        date=f"{date_str} 09:00:00 +0900",
        category=keyword_info['category'],
        tags=tags_str,
        description=description,
        keyword=keyword_info['keyword'],
    )

    full_content = front_matter + content + CTA_BLOCK

    filename = f"{date_str}-{keyword_slug}.md"
    filepath = POSTS_DIR / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_content)

    return filepath


def main():
    import argparse
    parser = argparse.ArgumentParser(description='商用キーワードSEO記事生成')
    parser.add_argument('--keyword', type=str, help='キーワードを指定')
    parser.add_argument('--batch', type=int, default=1, help='生成記事数')
    parser.add_argument('--list', action='store_true', help='キーワード一覧表示')
    args = parser.parse_args()

    if args.list:
        print("\n商用キーワード一覧:")
        for i, kw in enumerate(SEO_KEYWORDS):
            print(f"  {i + 1:2d}. {kw['keyword']:<30} ({kw['intent']})")
        sys.exit(0)

    # キーワード選択
    if args.keyword:
        keywords = [{"keyword": args.keyword, "intent": "指定キーワード", "category": "ai-consulting"}]
    else:
        keywords = random.sample(SEO_KEYWORDS, min(args.batch, len(SEO_KEYWORDS)))

    print(f"[SEO] {len(keywords)}記事を生成")

    for i, kw in enumerate(keywords):
        print(f"\n--- [{i + 1}/{len(keywords)}] {kw['keyword']} ---")
        print(f"  検索意図: {kw['intent']}")
        print(f"  生成中...")

        content = generate_article(kw)
        if not content:
            print(f"  生成失敗 — スキップ")
            continue

        filepath = save_article(kw, content)
        print(f"  保存: {filepath}")
        print(f"  文字数: {len(content)}")

    print(f"\n[SEO] 完了")


if __name__ == '__main__':
    main()
