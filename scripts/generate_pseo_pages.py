#!/usr/bin/env python3
"""
generate_pseo_pages.py - Programmatic SEO 2.0 ページ生成

カテゴリ:
  comparison  - AI製品比較ページ（高CVR）
  commercial  - サービスLP（最高CVR）
  industry    - 業界別AI活用ガイド
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from gemini_client import GeminiClient

POSTS_DIR = Path("/home/sol/ai-blog-system/_posts")
JST = timezone(timedelta(hours=9))

# ============================================================
# pSEO Page Definitions
# ============================================================

COMPARISON_PAGES = [
    {
        "products": ["ChatGPT", "Claude"],
        "kw": "ChatGPT Claude 比較 企業",
        "focus": "企業導入における性能・コスト・セキュリティの違い",
    },
    {
        "products": ["Azure OpenAI", "Amazon Bedrock", "Google Vertex AI"],
        "kw": "Azure OpenAI Bedrock Vertex AI 比較",
        "focus": "クラウドAIプラットフォームの料金・機能・連携性を比較",
    },
    {
        "products": ["GPT-4o", "Claude 3.5 Sonnet", "Gemini 2.0"],
        "kw": "GPT-4o Claude Gemini 比較 2026",
        "focus": "最新LLMの推論精度・速度・マルチモーダル対応を徹底比較",
    },
    {
        "products": ["GitHub Copilot", "Cursor", "Claude Code"],
        "kw": "GitHub Copilot Cursor Claude Code 比較",
        "focus": "AIコーディングアシスタントの機能・料金・開発効率を比較",
    },
    {
        "products": ["ChatGPT Enterprise", "Microsoft Copilot"],
        "kw": "ChatGPT Enterprise Microsoft Copilot 比較",
        "focus": "エンタープライズAI導入におけるセキュリティ・統合性・ROIを比較",
    },
    {
        "products": ["Stable Diffusion", "Midjourney", "DALL-E 3"],
        "kw": "Stable Diffusion Midjourney DALL-E 比較",
        "focus": "画像生成AIの品質・コスト・商用利用条件を比較",
    },
    {
        "products": ["RAG", "ファインチューニング"],
        "kw": "RAG ファインチューニング 比較 どっち",
        "focus": "企業のLLMカスタマイズ手法としてどちらが適切か",
    },
    {
        "products": ["オンプレミスAI", "クラウドAI"],
        "kw": "オンプレミス クラウド AI 比較",
        "focus": "セキュリティ・コスト・スケーラビリティの観点で比較",
    },
]

COMMERCIAL_PAGES = [
    {
        "service": "AI導入コンサルティング",
        "kw": "AI導入 コンサルティング 企業",
        "focus": "ALLFORCES のAI導入支援サービス。戦略策定からPoC、本番運用まで",
    },
    {
        "service": "生成AI導入支援",
        "kw": "生成AI 導入支援 企業向け",
        "focus": "ChatGPT/Claude等の生成AIを企業業務に導入するための支援サービス",
    },
    {
        "service": "AIエージェント開発",
        "kw": "AIエージェント 開発 依頼",
        "focus": "業務自動化AIエージェントのカスタム開発サービス",
    },
    {
        "service": "AI人材育成研修",
        "kw": "AI 研修 企業向け 人材育成",
        "focus": "非エンジニア向けAIリテラシー研修から、開発者向け実践研修まで",
    },
    {
        "service": "DX推進・AI戦略策定",
        "kw": "DX推進 AI戦略 コンサルティング",
        "focus": "AIを核としたデジタルトランスフォーメーション戦略の策定支援",
    },
]


def generate_comparison_article(client, page_def):
    """Generate a comparison article."""
    products = " vs ".join(page_def["products"])
    product_list = "、".join(page_def["products"])

    prompt = f"""あなたはAI導入コンサルタント「ALLFORCES編集部」です。
以下の比較記事を執筆してください。

【比較対象】{products}
【ターゲットKW】{page_def['kw']}
【比較の焦点】{page_def['focus']}

【記事構成】
1. 導入（120文字以内で検索意図に直接回答）
2. 比較表（主要スペック・料金・特徴を表形式で）
3. 各製品の詳細レビュー（強み・弱み・最適なユースケース）
4. 用途別おすすめ（「〇〇なら△△」形式で3-5パターン）
5. 導入時の注意点（コスト、セキュリティ、スケーラビリティ）
6. まとめ＋CTA（「AI導入でお悩みの方は、ALLFORCESの無料相談をご利用ください」）

【条件】
- 3,000-5,000文字
- 具体的な数字（料金、性能スコア、導入事例の数値）を含める
- 一人称は使わない（「編集部では」「取材によると」を使用）
- 中立的な比較（特定製品を持ち上げすぎない）
- Markdown形式（frontmatterなし）
- 比較表はMarkdownテーブルで
- 内部リンクプレースホルダー: [関連記事]を3箇所以上

【禁止】
- 「革命的」「パラダイムシフト」等のAIクリシェ
- 個人名や一人称"""

    body = client.call_with_search(prompt, temperature=0.7, max_tokens=8192)
    if not body:
        body = client.call(prompt, temperature=0.7, max_tokens=8192)
    return body


def generate_commercial_article(client, page_def):
    """Generate a commercial/service landing page article."""
    prompt = f"""あなたはAI導入コンサルタント「ALLFORCES編集部」です。
以下のサービス紹介記事を執筆してください。

【サービス名】{page_def['service']}
【ターゲットKW】{page_def['kw']}
【サービス概要】{page_def['focus']}

【記事構成】
1. 導入（企業が抱える課題を明確化、120文字以内）
2. サービス概要（ALLFORCES の {page_def['service']} とは）
3. サービスの特徴（3-5つ、数字付き）
4. 導入フロー（ステップ形式、期間・費用感を含む）
5. 導入効果（数字で示す: コスト削減○%、生産性向上○倍等）
6. 対象企業（業界・規模・課題別に3パターン）
7. FAQ（よくある質問5つ）
8. CTA（無料相談への誘導）

【条件】
- 2,500-4,000文字
- 具体的な数字（導入期間、費用感、効果指標）
- 一人称は使わない
- 信頼感のある専門的な文体
- Markdown形式（frontmatterなし）
- 内部リンクプレースホルダー: [関連記事]を3箇所以上

【禁止】
- 「革命的」等のAIクリシェ
- 個人名"""

    body = client.call(prompt, temperature=0.7, max_tokens=8192)
    return body


def generate_title_and_meta(client, page_type, page_def, body):
    """Generate optimized title and metadata."""
    if page_type == "comparison":
        products = " vs ".join(page_def["products"])
        context = f"比較記事: {products}"
    else:
        context = f"サービス紹介: {page_def['service']}"

    schema = {
        "type": "OBJECT",
        "properties": {
            "title": {"type": "STRING"},
            "description": {"type": "STRING"},
            "excerpt": {"type": "STRING"},
            "tags": {"type": "ARRAY", "items": {"type": "STRING"}},
            "slug": {"type": "STRING"},
        },
        "required": ["title", "description", "excerpt", "tags", "slug"]
    }

    prompt = f"""以下の記事のSEOメタデータを生成してください。

【記事種別】{context}
【ターゲットKW】{page_def.get('kw', '')}
【本文冒頭】{body[:500] if body else ''}

【title条件】45-58文字、キーワード前方配置、数字含む、「vs」や「比較」等含む
【description条件】120-155文字、検索意図に直接回答、記事を読むメリット明示
【excerpt条件】80-120文字の要約
【tags条件】3-6個
【slug条件】英語30文字以内、ハイフン区切り"""

    result = client.call_json(prompt, schema=schema)
    return result


def build_frontmatter(title, metadata, page_type, page_def):
    """Build Jekyll front matter."""
    now = datetime.now(JST)
    date_str = now.strftime('%Y-%m-%d %H:%M:%S +0900')
    tags = metadata.get('tags', ['AI', '比較'])
    tags_str = json.dumps(tags, ensure_ascii=False)

    category = "AI技術ガイド" if page_type == "comparison" else "AI導入戦略"

    fm = f"""---
layout: post
title: "{title}"
date: {date_str}
categories: [{category}]
tags: {tags_str}
author: "ALLFORCES編集部"
description: "{metadata.get('description', '')}"
excerpt: "{metadata.get('excerpt', '')}"
reading_time: {max(5, len(metadata.get('description', '')) // 20)}
pseo_type: "{page_type}"
---"""
    return fm


def save_article(title, metadata, body, page_type, page_def):
    """Save article to _posts directory."""
    now = datetime.now(JST)
    date_prefix = now.strftime('%Y-%m-%d')
    slug = metadata.get('slug', 'pseo-article')
    slug = re.sub(r'[^a-z0-9-]', '', slug.lower())[:30]

    # Find next available article number
    existing = list(POSTS_DIR.glob(f"{date_prefix}-*-{slug}*.md"))
    num = len(existing) + 1

    filename = f"{date_prefix}-{num}-{slug}.md"
    filepath = POSTS_DIR / filename

    frontmatter = build_frontmatter(title, metadata, page_type, page_def)
    full_article = f"{frontmatter}\n\n{body}\n"

    filepath.write_text(full_article, encoding='utf-8')
    return filepath


def main():
    category = sys.argv[1] if len(sys.argv) > 1 else None
    dry_run = '--dry-run' in sys.argv

    if not category or category in ('--help', '-h'):
        print("Usage: generate_pseo_pages.py <category> [--dry-run]")
        print("  comparison  - AI製品比較ページ")
        print("  commercial  - サービスLP")
        print("  all         - 全カテゴリ")
        return

    client = GeminiClient()
    pages_to_generate = []

    if category in ('comparison', 'all'):
        pages_to_generate.extend([(p, 'comparison') for p in COMPARISON_PAGES])
    if category in ('commercial', 'all'):
        pages_to_generate.extend([(p, 'commercial') for p in COMMERCIAL_PAGES])

    print(f"生成対象: {len(pages_to_generate)}ページ")

    generated = []
    for i, (page_def, page_type) in enumerate(pages_to_generate):
        label = page_def.get('products', [page_def.get('service', '?')])
        print(f"\n--- [{i+1}/{len(pages_to_generate)}] {page_type}: {label} ---")

        if dry_run:
            print(f"  [DRY RUN] Would generate: {page_def.get('kw', '')}")
            continue

        # Generate body
        if page_type == 'comparison':
            body = generate_comparison_article(client, page_def)
        else:
            body = generate_commercial_article(client, page_def)

        if not body:
            print(f"  FAILED: 本文生成失敗")
            continue

        # Generate title and metadata
        meta = generate_title_and_meta(client, page_type, page_def, body)
        if not meta:
            print(f"  FAILED: メタデータ生成失敗")
            continue

        title = meta.get('title', '')
        if not title:
            if page_type == 'comparison':
                title = f"{' vs '.join(page_def['products'])} 徹底比較｜企業導入で選ぶべきはどっち？"
            else:
                title = f"{page_def['service']}｜ALLFORCES"

        # Save
        filepath = save_article(title, meta, body, page_type, page_def)
        print(f"  SAVED: {filepath.name} ({len(body)}文字)")
        generated.append(filepath.name)

        time.sleep(RATE_LIMIT_SLEEP)

    print(f"\n--- 結果 ---")
    print(f"生成成功: {len(generated)}ページ")
    for name in generated:
        print(f"  {name}")


RATE_LIMIT_SLEEP = 3

if __name__ == '__main__':
    main()
