#!/usr/bin/env python3
"""
Article Generation Pipeline - 6-Stage Orchestrator
Replaces the 749-line bash pipeline with structured Python orchestration.

Stages:
  1. Topic Planning (flash-lite, JSON) - Generate topics with category targets
  2. Article Draft (flash + Web Search) - Write article with knowledge base context
  3. Title Optimization (flash-lite, JSON) - Generate and sanitize title
  4. Metadata Generation (flash-lite, JSON) - Category, tags, slug, excerpt
  5. Quality Gate (Python only) - Score and optionally retry
  6. Post-Processing - textlint, enrich, OGP image

Usage:
  python3 scripts/article_pipeline.py --articles 3
  python3 scripts/article_pipeline.py --articles 1 --dry-run
  python3 scripts/article_pipeline.py --articles 3 --skip-enrich
"""

import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone, timedelta

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gemini_client import GeminiClient
from title_sanitizer import TitleSanitizer
from quality_scorer import QualityScorer
from knowledge_base import KnowledgeBase
from research_loader import ResearchLoader
from persona_to_editorial_filter import load_persona_filter
from internal_linking_strategy import get_internal_linking_engine
try:
    from sectional_article_pipeline import SectionalArticleGenerator
    SECTIONAL_AVAILABLE = True
except ImportError:
    SECTIONAL_AVAILABLE = False
try:
    from compliance_loader import ComplianceLoader
except ImportError:
    ComplianceLoader = None

# Japan timezone
JST = timezone(timedelta(hours=9))

# Valid categories (must match _config.yml)
VALID_CATEGORIES = [
    "AI最新ニュース",
    "AI技術ガイド",
    "AI導入戦略",
    "業界別AI活用",
    "導入事例",
    "研究論文",
]

# Day-of-week category rotation for diversity
DAY_CATEGORY_MAP = {
    0: ["AI技術ガイド", "業界別AI活用", "AI最新ニュース"],      # Monday
    1: ["導入事例", "AI最新ニュース", "AI導入戦略"],              # Tuesday
    2: ["AI技術ガイド", "研究論文", "業界別AI活用"],              # Wednesday
    3: ["AI最新ニュース", "導入事例", "AI技術ガイド"],            # Thursday
    4: ["業界別AI活用", "AI導入戦略", "AI最新ニュース"],          # Friday
    5: ["AI技術ガイド", "AI最新ニュース", "業界別AI活用"],        # Saturday
    6: ["AI導入戦略", "導入事例", "研究論文"],                     # Sunday
}

# ペルソナ情報をDigitalDouble SDK経由で動的読み込み（Growth/Task, platform='ai_media'）
# persona_id='default'のメモリ名前空間を使用
_DD_AVAILABLE = False
_SANITIZER = None
try:
    sys.path.insert(0, os.path.join(os.path.expanduser('~'), 'digital-double'))
    from digital_double import DigitalDouble
    _DD_AVAILABLE = True
    # OutputSanitizer で非公開情報を秘匿化
    try:
        from output_sanitizer import OutputSanitizer
        _SANITIZER = OutputSanitizer()
    except ImportError:
        pass
except ImportError:
    pass

# レガシーフォールバック: PersonaController
_CONTROLLER_AVAILABLE = False
if not _DD_AVAILABLE:
    _PERSONA_SEARCH_PATHS = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'xpost-community', 'config'),
        os.path.join(os.path.expanduser('~'), 'xpost-community', 'config'),
    ]
    for _p in _PERSONA_SEARCH_PATHS:
        if os.path.isdir(_p):
            sys.path.insert(0, _p)
            break
    try:
        from persona_controller import PersonaController as _PC
        _CONTROLLER_AVAILABLE = True
    except ImportError:
        pass

def _load_persona_config():
    """記者ペルソナ設定を読み込む（個人は前面に出さない、知見ベース）

    優先順位:
    1. DigitalDouble SDK (ai_media プラットフォーム)
    2. レガシー PersonaController (xpost-community/config/)
    """
    # DigitalDouble SDK経由 (Growth/Task mode)
    if _DD_AVAILABLE:
        try:
            dd = DigitalDouble(mode='growth')
            base_persona = dd.build_prompt(
                platform='ai_media',
                content_type='technical',
                topic_keywords=['AI', 'テクノロジー'],
                max_tokens=3000
            )
            if base_persona:
                if _SANITIZER:
                    base_persona = _SANITIZER.sanitize(base_persona, context='public')
                return base_persona, "ALLFORCES編集部"
        except Exception as e:
            print(f"  [Persona] DigitalDouble SDK fallback: {e}", file=sys.stderr)

    # レガシー: PersonaController から直接読み込み
    if not _CONTROLLER_AVAILABLE:
        return None, None

    _PERSONA_SEARCH_PATHS = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'xpost-community', 'config'),
        os.path.join(os.path.expanduser('~'), 'xpost-community', 'config'),
    ]
    for search_dir in _PERSONA_SEARCH_PATHS:
        candidate = os.path.join(search_dir, 'x_persona_config.json')
        if os.path.exists(candidate):
            persona_path = candidate
            break
    else:
        return None, None
    try:
        with open(persona_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        expertise = config.get('expertise_map', {})
        branding = config.get('branding_strategy', {})
        work = config.get('work_style', {})
        biz = config.get('business_acumen', {})

        episodes = []
        for domain, info in expertise.items():
            if isinstance(info, dict) and info.get('can_speak_authoritatively') and info.get('achievements'):
                for ach in info['achievements'][:2]:
                    if _SANITIZER:
                        ach = _SANITIZER.sanitize(ach, context='public')
                    episodes.append(ach)

        biz_context = ""
        if biz:
            financial = biz.get('financial_management', {})
            strategic = biz.get('strategic_thinking', {})
            negotiation = biz.get('negotiation_skills', {})
            biz_lines = []
            if financial:
                biz_lines.append(f"- 財務分析: {financial.get('profit_focus', '')}")
            if strategic:
                biz_lines.append(f"- 事業戦略: {strategic.get('portfolio_strategy', '')}")
            if negotiation:
                biz_lines.append(f"- 交渉・契約: {negotiation.get('pricing_strategy', '')}")
            if biz_lines:
                biz_context = "\n【ビジネス知見（記事に深みを加える視点）】\n" + "\n".join(biz_lines)

        leadership_context = ""
        if work:
            leadership = work.get('leadership_approach', {})
            if leadership:
                leadership_context = f"\n【マネジメント知見】\n- {leadership.get('mentoring_style', '')}\n- {leadership.get('style', '')}"

        avoid_rules = "\n".join([f"- {a}" for a in branding.get('avoid', [])])

        ai_media_config = config.get('platform_adaptations', {}).get('ai_media', {})
        prohibited = ai_media_config.get('prohibited', [])
        prohibited_rules = "\n".join([f"- {p}" for p in prohibited])

        base_persona = f"""あなたはALLFORCES編集部の記者です。
AI・テクノロジー分野を専門とし、幅広い技術領域の実務経験に基づいた記事を書きます。

【執筆スタイル】
- 実務経験に基づいた具体的な知見を織り込む（「〜のプロジェクトでは」「〜を構築した際に」等）
- 技術の表面ではなく、実装レベルの本質を捉えた解説
- ビジネスインパクトと技術詳細の両面をバランスよくカバー
- 読者が実務に活かせる実践的な示唆を提供

【避けるべき表現】
{avoid_rules}
- 個人名やプロフィールの前面押し出し
- 「私が」「僕が」等の一人称（「編集部では」「取材によると」等を使用）

【禁止事項（ai_media固有）】
{prohibited_rules}

【語れる実務知見（エピソードベースで織り込む）】
{chr(10).join(['- ' + ep for ep in episodes[:12]])}
{biz_context}
{leadership_context}"""

        return base_persona, "ALLFORCES編集部"
    except Exception as e:
        print(f"  [Persona] Failed to load persona config: {e}", file=sys.stderr)
        return None, None

_PERSONA_BASE, _PERSONA_AUTHOR = _load_persona_config()

# Category-specific personas（記者ペルソナ: カテゴリごとの視点切り替え、個人は前面に出さない）
PERSONAS = {
    "AI技術ガイド": {
        "persona": f"""{_PERSONA_BASE or 'あなたはAI技術に精通した記者です。'}

【このカテゴリでの視点】
AI実装プロジェクトの経験に基づき、複雑な技術を実務者の視点で分かりやすく解説する。""",
        "structure": "1.技術の概要と背景 2.アーキテクチャ詳細 3.実装のポイント 4.パフォーマンス比較 5.導入時の注意点",
        "author": "ALLFORCES編集部",
    },
    "導入事例": {
        "persona": f"""{_PERSONA_BASE or 'あなたはAI導入の実務に精通した記者です。'}

【このカテゴリでの視点】
企業へのAI導入支援の取材・実務知見から、成功要因と失敗パターンをリアルに分析する。""",
        "structure": "1.導入企業の課題 2.選定したAIソリューション 3.実装プロセス 4.定量的な成果 5.成功要因と横展開",
        "author": "ALLFORCES編集部",
    },
    "業界別AI活用": {
        "persona": f"""{_PERSONA_BASE or 'あなたは複数業界のAI活用に精通した記者です。'}

【このカテゴリでの視点】
多業界のAI導入事例を取材・分析した知見から、業界固有の課題とAI活用の現実的な可能性を掘り下げる。""",
        "structure": "1.業界の現状と課題 2.AI活用の最新トレンド 3.導入障壁と克服策 4.ROI試算 5.今後の展望",
        "author": "ALLFORCES編集部",
    },
    "研究論文": {
        "persona": f"""{_PERSONA_BASE or 'あなたはAI研究と実装の両方に精通した記者です。'}

【このカテゴリでの視点】
研究開発の経験に基づき、最新研究の実用化可能性を技術と市場の両面からリアルに評価する。""",
        "structure": "1.研究の背景と動機 2.手法の核心 3.実験結果と比較 4.実用化への道筋 5.この研究が意味すること",
        "author": "ALLFORCES編集部",
    },
    "AI導入戦略": {
        "persona": f"""{_PERSONA_BASE or 'あなたはAI導入戦略に精通した記者です。'}

【このカテゴリでの視点】
幅広い技術選定・導入の知見から、技術選定とビジネス戦略の両面で実践的な提言を行う。""",
        "structure": "1.戦略的背景 2.フレームワーク提示 3.具体的なアクションステップ 4.リスクと対策 5.成功の条件",
        "author": "ALLFORCES編集部",
    },
    "AI最新ニュース": {
        "persona": f"""{_PERSONA_BASE or 'あなたはAI業界の動向に精通した記者です。'}

【このカテゴリでの視点】
AI開発の実務経験から、ニュースの技術的本質と企業への実務インパクトを鋭く分析する。""",
        "structure": "1.印象的な導入 2.背景説明 3.核心分析 4.実践的示唆 5.開かれた結び",
        "author": "ALLFORCES編集部",
    },
}


def get_recent_articles_context(posts_dir="_posts", days=14):
    """Get recent article titles and slugs for duplication avoidance.

    Returns:
        dict with 'titles' (list of str) and 'slugs' (list of str)
    """
    titles = []
    slugs = []
    cutoff = datetime.now() - timedelta(days=days)

    if not os.path.isdir(posts_dir):
        return {"titles": titles, "slugs": slugs}

    for f in sorted(os.listdir(posts_dir), reverse=True)[:60]:
        if not f.endswith('.md'):
            continue
        match = re.match(r'(\d{4})-(\d{2})-(\d{2})', f)
        if match:
            file_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
            if file_date >= cutoff:
                # Extract slug from filename
                slug_match = re.match(r'\d{4}-\d{2}-\d{2}-\d+-(.+)\.md', f)
                if slug_match:
                    slugs.append(slug_match.group(1))

                filepath = os.path.join(posts_dir, f)
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as fh:
                        content = fh.read(2000)
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            for line in parts[1].split('\n'):
                                if line.startswith('title:'):
                                    title = line.replace('title:', '').strip().strip('"').strip("'")
                                    titles.append(title)
                                    break
                except Exception:
                    pass

    return {"titles": titles[:30], "slugs": slugs[:30]}


def fetch_latest_ai_news(client):
    """Fetch latest AI news using Gemini Web Search (NEWS_MODELS rotation).

    Returns:
        list of news dicts, or empty list on failure
    """
    print("\n--- Fetching latest AI news via Web Search ---", file=sys.stderr)
    try:
        news = client.fetch_news(
            query="AI 人工知能 LLM GPT Claude Gemini 最新ニュース 2026",
            max_items=15
        )
        if news:
            print(f"  Fetched {len(news)} news items", file=sys.stderr)
            for i, item in enumerate(news[:5]):
                print(f"    {i+1}. [{item.get('category', '?')}] {item.get('headline', '?')}", file=sys.stderr)
            return news
        else:
            print("  Warning: No news fetched, falling back to static trends", file=sys.stderr)
            return []
    except Exception as e:
        print(f"  Warning: News fetch failed: {e}", file=sys.stderr)
        return []


def stage1_topic_planning(client, kb, num_articles, dry_run=False):
    """Stage 1: Generate topic plans driven by real-time news.

    Uses Gemini Web Search to fetch latest AI news, then plans articles
    based on actual news items instead of static trends.
    """
    print("\n=== Stage 1: Topic Planning (News-Driven) ===", file=sys.stderr)

    now = datetime.now(JST)
    weekday = now.weekday()
    target_cats = DAY_CATEGORY_MAP.get(weekday, VALID_CATEGORIES[:3])[:num_articles]

    # Pad if needed
    while len(target_cats) < num_articles:
        for cat in VALID_CATEGORIES:
            if cat not in target_cats:
                target_cats.append(cat)
                if len(target_cats) >= num_articles:
                    break

    # Get recent articles for deduplication (14 days, 30 items)
    recent_ctx = get_recent_articles_context()
    recent_titles = recent_ctx["titles"]
    recent_slugs = recent_ctx["slugs"]
    recent_str = "、".join(recent_titles[:15]) if recent_titles else "なし"

    # Fetch real-time AI news via Web Search
    news_items = []
    if not dry_run and client:
        news_items = fetch_latest_ai_news(client)

    # Build news context for prompt
    if news_items:
        news_lines = []
        for i, item in enumerate(news_items):
            headline = item.get('headline', '')
            summary = item.get('summary', '')
            category = item.get('category', '')
            source = item.get('source', '')
            date = item.get('date', '')
            news_lines.append(f"  {i+1}. [{category}] {headline} ({source}, {date})")
            if summary:
                news_lines.append(f"     → {summary}")
        news_ctx = "\n".join(news_lines)
    else:
        # Fallback to static trends if news fetch failed
        news_ctx = kb.format_trends_context()

    schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "title_seed": {"type": "STRING"},
                "category": {"type": "STRING"},
                "angle": {"type": "STRING"},
                "news_source": {"type": "STRING"},
                "target_companies": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
            },
            "required": ["title_seed", "category", "angle"]
        }
    }

    prompt = f"""あなたはAIニュースメディアの編集長です。
以下の最新ニュースから、読者にとって価値の高い記事トピックを{num_articles}件企画してください。

【本日の最新AIニュース】
{news_ctx}

【カテゴリ指定】以下のカテゴリで1件ずつ:
{chr(10).join(f'  {i+1}. {cat}' for i, cat in enumerate(target_cats))}

【最近14日間の既存記事（これらと重複しないこと）】
{recent_str}

【禁止スラグ（同一テーマ回避）】
{', '.join(recent_slugs[:20]) if recent_slugs else 'なし'}

【企画条件】
- 上記ニュースから具体的なニュースを選び、それを起点に記事を企画する
- 同じニュースを複数記事で使わない
- 既存記事と同じテーマ・企業・切り口は避ける
- title_seedは30文字以内の仮タイトル（具体的な企業名・製品名を含む）
- angleは「何の視点から書くか」を50文字で
- news_sourceは元にしたニュースの見出し（ニュースがない場合は空文字）
- target_companiesは記事で言及予定の企業ID(openai, google, nvidia, anthropic, meta, microsoft, deepseek, mistral等)を2-4個

日付: {now.strftime('%Y年%m月%d日')}"""

    if dry_run:
        print(f"  [DRY RUN] Would generate {num_articles} topics", file=sys.stderr)
        if news_items:
            # Use actual news for dry-run topics
            topics = []
            for i in range(min(num_articles, len(news_items))):
                topics.append({
                    "title_seed": news_items[i].get('headline', f'テストトピック{i+1}')[:30],
                    "category": target_cats[i],
                    "angle": news_items[i].get('summary', 'テスト')[:50],
                    "news_source": news_items[i].get('headline', ''),
                    "target_companies": ["openai"]
                })
            # Pad remaining
            while len(topics) < num_articles:
                idx = len(topics)
                topics.append({
                    "title_seed": f"テストトピック{idx+1}",
                    "category": target_cats[idx % len(target_cats)],
                    "angle": "テスト",
                    "news_source": "",
                    "target_companies": ["openai"]
                })
            return topics
        return [{"title_seed": f"テストトピック{i+1}", "category": target_cats[i],
                 "angle": "テスト", "news_source": "", "target_companies": ["openai"]}
                for i in range(num_articles)]

    # Use call_json_with_search for additional grounding
    result = client.call_json_with_search(prompt, schema=schema)

    if not result or not isinstance(result, list):
        print("  Warning: JSON topic generation failed, trying call_json...", file=sys.stderr)
        result = client.call_json(prompt, schema=schema)

    if not result or not isinstance(result, list):
        print("  Warning: All JSON modes failed, falling back to text", file=sys.stderr)
        text_result = client.call(prompt)
        if text_result:
            topics = []
            for i, cat in enumerate(target_cats):
                topics.append({
                    "title_seed": f"AI{cat}の最新動向",
                    "category": cat,
                    "angle": "最新動向を分析",
                    "news_source": "",
                    "target_companies": ["openai", "google"]
                })
            result = topics
        else:
            print("  ERROR: Topic generation completely failed", file=sys.stderr)
            return []

    # Validate and fix categories
    for topic in result:
        if topic.get('category') not in VALID_CATEGORIES:
            cat = topic.get('category', '')
            matched = False
            for valid in VALID_CATEGORIES:
                if cat in valid or valid in cat:
                    topic['category'] = valid
                    matched = True
                    break
            if not matched:
                topic['category'] = target_cats[result.index(topic) % len(target_cats)]

    for i, topic in enumerate(result[:num_articles]):
        print(f"  Topic {i+1}: [{topic['category']}] {topic.get('title_seed', 'N/A')}", file=sys.stderr)
        print(f"    Angle: {topic.get('angle', 'N/A')}", file=sys.stderr)
        if topic.get('news_source'):
            print(f"    News: {topic['news_source']}", file=sys.stderr)

    return result[:num_articles]


def stage2_article_draft(client, kb, topic, compliance_loader=None, dry_run=False, persona_filter=None):
    """Stage 2: Generate article draft with knowledge base + research + compliance context.

    If persona_filter is provided, applies Digital Twin SDK persona guidelines to generation."""
    print(f"\n=== Stage 2: Article Draft [{topic['category']}] ===", file=sys.stderr)

    category = topic['category']
    persona_info = PERSONAS.get(category, PERSONAS["AI最新ニュース"])

    # Build knowledge base context for this topic
    company_ids = topic.get('target_companies', [])
    kb_context = kb.build_prompt_context(
        company_ids=company_ids if company_ids else None,
        include_market=True,
        include_benchmarks=(category in ["AI技術ガイド", "研究論文"]),
        include_pricing=(category in ["AI技術ガイド", "AI導入戦略"]),
        include_trends=True
    )

    # Load pre-research data if available (graceful degradation)
    research_context = ""
    try:
        research_loader = ResearchLoader()
        slug = topic.get('slug', '')
        keywords = [topic.get('title_seed', '')] + topic.get('target_companies', [])
        research_data = research_loader.find_research(
            topic_slug=slug if slug else None,
            keywords=[k for k in keywords if k],
            max_age_days=7
        )
        if research_data:
            research_context = research_loader.format_research_context(research_data)
            print(f"  [Research] Injecting pre-research data", file=sys.stderr)
        else:
            print(f"  [Research] No pre-research data found (using KB only)", file=sys.stderr)
    except Exception as e:
        print(f"  [Research] Skipped: {e}", file=sys.stderr)

    # Load compliance context (graceful degradation)
    compliance_context = ""
    try:
        if compliance_loader:
            compliance_context = compliance_loader.build_article_context(
                category=category,
                company_names=company_ids
            )
            print(f"  [Compliance] Injecting compliance rules ({len(compliance_context)} chars)", file=sys.stderr)
    except Exception as e:
        print(f"  [Compliance] Skipped: {e}", file=sys.stderr)

    # Build prompt with KB context + optional research + compliance context
    context_block = kb_context
    if research_context:
        context_block = f"{kb_context}\n\n{research_context}"
    if compliance_context:
        context_block = f"{context_block}\n\n{compliance_context}"

    # Layer in persona filter guidelines from Digital Twin SDK (if available)
    base_persona = persona_info['persona']
    if persona_filter:
        editorial_guidelines = persona_filter.generate_section_guidelines(section_num=0)
        base_persona = f"{base_persona}\n\n{editorial_guidelines}"
        print(f"  [Persona Filter] Applied Digital Twin guidelines", file=sys.stderr)

    prompt = f"""{base_persona}

{context_block}

【トピック】{topic.get('title_seed', '')}
【角度】{topic.get('angle', '')}
【カテゴリ】{category}

【記事構成】{persona_info['structure']}

【文体指示】
- やや丁寧だが堅すぎない、技術者として自然な語り口
- 体験ベースの語り（「〜を作った時に」「〜で気づいたのは」「実際にやってみると」）
- 短い文で注意を引き、長い文で詳しく説明するリズム
- 読者に直接話しかけるスタイル（「あなたも感じているかもしれませんが」「正直なところ」等）
- 読者への問いかけを2回以上含める
- 個人的見解や経験を体験ベースで含める（「知識で示す」スタイル）

【避けること】
- 「結論として」「留意すべき重要な点は」等の常套句
- 「予測されます」の多用
- 「大幅な改善」「革命的な」等の曖昧な表現
- 箇条書きの多用（全体の30%以下に）
- 「SIGGRAPH出展した私が〜」等の権威アピール
- 「15年の経験から言うと〜」等の経験マウント
- 煽り系マーケティング語（「知らないと損」等）

【必須条件】
- 3000-4000文字
- 参照データの数値は「〜によると」「〜年時点で」と出典明示
- 具体的な企業名・製品名・数値を含む
- 必ず完結させる（文章途中で終わらない）
- 最後は読者への問いかけで締める

【出力形式】Markdown形式の記事本文のみ（frontmatterなし）"""

    if dry_run:
        print("  [DRY RUN] Would generate article draft", file=sys.stderr)
        return "# テスト記事\n\nこれはテスト記事です。\n\n## セクション1\n\nテスト内容。"

    # Use heavy model with web search for article generation
    result = client.call_with_search(prompt, max_tokens=8192)

    if not result:
        print("  Warning: Web search generation failed, trying without search", file=sys.stderr)
        result = client.call(prompt, max_tokens=8192)

    if not result:
        print("  ERROR: Article generation failed", file=sys.stderr)
        return None

    # Clean up: remove ALL ---END--- markers (may appear mid-article or at end)
    result = re.sub(r'\n*---END---[^\n]*', '', result).strip()

    print(f"  Generated {len(result)} chars", file=sys.stderr)
    return result


def stage2_article_draft_sectional(topic, dry_run=False):
    """Stage 2 (Sectional): Generate article draft using 5-section pipeline with context.

    Uses SectionalArticleGenerator (Gemma-3-27b-it) instead of standard Gemini pipeline.
    Each section receives previous sections as context for coherence."""
    print(f"\n=== Stage 2: Article Draft (Sectional 5-Section) ===", file=sys.stderr)

    if dry_run:
        print("  [DRY RUN] Would generate 5-section article", file=sys.stderr)
        return "# テスト記事\n\n## セクション1\n\nセクション1の内容。\n\n## セクション2\n\nセクション2の内容。"

    try:
        generator = SectionalArticleGenerator()
        print(f"  [Sectional] Initialized SectionalArticleGenerator (Gemma-3-27b-it)", file=sys.stderr)

        # Generate all 5 sections
        sections_to_generate = [
            ('section_1', 'generate_section_1_introduction'),
            ('section_2', 'generate_section_2_research'),
            ('section_3', 'generate_section_3_applications'),
            ('section_4', 'generate_section_4_market_analysis'),
            ('section_5', 'generate_section_5_future'),
        ]

        for section_name, method_name in sections_to_generate:
            method = getattr(generator, method_name, None)
            if method and callable(method):
                success = method()
                if not success:
                    print(f"  [Sectional] Failed to generate {section_name}", file=sys.stderr)
                    return None
            else:
                print(f"  [Sectional] Method not found: {method_name}", file=sys.stderr)
                return None

        # Combine sections with markdown headers
        sections_text = []
        section_titles = [
            "企業動向・市場の動き",
            "研究開発の進展",
            "新サービス・製品発表",
            "市場動向・投資・規制",
            "今後の展開と予測",
        ]

        for i, (section_name, _) in enumerate(sections_to_generate):
            if section_name in generator.sections:
                title = section_titles[i]
                content = generator.sections[section_name]
                sections_text.append(f"## {title}\n\n{content}")

        combined_body = "\n\n".join(sections_text)
        total_chars = len(combined_body)

        # Log stats
        stats = generator.stats
        total_time = sum(stats['generation_times'].values())
        print(f"  [Sectional] Generated {total_chars} chars in {total_time:.1f}s", file=sys.stderr)
        print(f"    - Sections: {len(generator.sections)}/5 completed", file=sys.stderr)
        timing_str = ', '.join([f"{k.replace('section_', 'S')}:{v:.1f}s" for k, v in stats['generation_times'].items()])
        print(f"    - Timing: {timing_str}", file=sys.stderr)

        return combined_body

    except Exception as e:
        print(f"  [Sectional] Error: {e}", file=sys.stderr)
        return None


def stage3_title_optimization(client, topic, body, dry_run=False):
    """Stage 3: Optimize article title."""
    print(f"\n=== Stage 3: Title Optimization ===", file=sys.stderr)

    # Extract any title from the body (if Gemini included one)
    body_title = ""
    for line in body.split('\n')[:5]:
        if line.startswith('# ') and not line.startswith('##'):
            body_title = line.lstrip('# ').strip()
            break

    seed_title = topic.get('title_seed', '')
    intro = body[:500] if body else ""

    schema = {
        "type": "OBJECT",
        "properties": {
            "titles": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "best_index": {"type": "INTEGER"}
        },
        "required": ["titles", "best_index"]
    }

    prompt = f"""以下の記事に最適なタイトルを3案生成してください。

【仮タイトル】{seed_title}
【本文から抽出したタイトル】{body_title}
【記事冒頭】{intro}

【タイトル条件】
- 25-40文字
- 好奇心を刺激する（「その真意は？」「何が変わるのか？」型）
- 煽り文句禁止（【衝撃】【速報】等）
- Markdown記号禁止（**, ##, []() 等）
- 必ず完全な文として終わる（途中で切れない）
- 具体的な企業名や数値を含むと良い

3案をtitles配列で返し、best_indexで最も良いもののインデックス(0始まり)を指定。"""

    if dry_run:
        title = TitleSanitizer.sanitize(seed_title or "テスト記事タイトル")
        print(f"  [DRY RUN] Title: {title}", file=sys.stderr)
        return title

    result = client.call_json(prompt, schema=schema)

    if result and 'titles' in result and result['titles']:
        idx = result.get('best_index', 0)
        if idx >= len(result['titles']):
            idx = 0
        raw_title = result['titles'][idx]
        title = TitleSanitizer.sanitize(raw_title, max_len=45)

        print(f"  Candidates:", file=sys.stderr)
        for i, t in enumerate(result['titles']):
            marker = " <--" if i == idx else ""
            print(f"    {i+1}. {t}{marker}", file=sys.stderr)
        print(f"  Final: {title}", file=sys.stderr)
        return title

    # Fallback: use seed title or body title
    fallback = body_title or seed_title or "AI最新動向の分析"
    title = TitleSanitizer.sanitize(fallback, max_len=45)
    print(f"  Fallback title: {title}", file=sys.stderr)
    return title


def stage4_metadata(client, title, body, topic, dry_run=False):
    """Stage 4: Generate metadata (category, tags, slug, excerpt)."""
    print(f"\n=== Stage 4: Metadata Generation ===", file=sys.stderr)

    category = topic.get('category', 'AI最新ニュース')

    schema = {
        "type": "OBJECT",
        "properties": {
            "tags": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "slug": {"type": "STRING"},
            "excerpt": {"type": "STRING"},
        },
        "required": ["tags", "slug", "excerpt"]
    }

    prompt = f"""以下の記事のメタデータを生成してください。

【タイトル】{title}
【カテゴリ】{category}
【本文冒頭】{body[:1000]}

【タグ条件】3-6個、以下から選択:
技術: LLM, RAG, AIエージェント, マルチモーダル, 画像生成, 音声AI, 推論最適化, ファインチューニング
企業: OpenAI, Google, Microsoft, NVIDIA, Meta, Anthropic, Amazon, Apple, 日本企業, 中国AI
ビジネス: ROI分析, 導入ロードマップ, PoC設計, AI人材育成, AI規制対応, コスト削減, DX推進, AI投資

【slug条件】英語のURL用スラグ、30文字以内、ハイフン区切り（例: openai-gpt5-enterprise-impact）

【excerpt条件】記事の要約、80-120文字の日本語"""

    if dry_run:
        return {
            "category": category,
            "tags": ["AI", "LLM"],
            "slug": "test-article",
            "excerpt": "テスト記事の要約です。",
            "author": PERSONAS.get(category, {}).get('author', 'ALLFORCES編集部'),
            "reading_time": 8,
        }

    result = client.call_json(prompt, schema=schema)

    # Calculate reading time from body
    char_count = len(body)
    reading_time = max(3, min(15, (char_count // 500) + 1))

    author = PERSONAS.get(category, {}).get('author', 'ALLFORCES編集部')

    if result:
        tags = result.get('tags', [])[:6]
        # Validate tags are not empty
        tags = [t for t in tags if t and len(t) > 0]
        # Ensure minimum 3 tags
        if len(tags) < 3:
            # Add category-based fallback tags
            fallback_tags = {
                "AI技術ガイド": ["LLM", "AI技術", "実装"],
                "導入事例": ["AI導入", "DX推進", "ROI分析"],
                "業界別AI活用": ["業界分析", "DX推進", "AI活用"],
                "研究論文": ["AI研究", "LLM", "機械学習"],
                "AI導入戦略": ["AI投資", "導入ロードマップ", "DX推進"],
                "AI最新ニュース": ["AI動向", "テック企業", "AI投資"],
            }
            extras = fallback_tags.get(category, ["AI", "テクノロジー", "DX推進"])
            for tag in extras:
                if tag not in tags and len(tags) < 3:
                    tags.append(tag)

        slug = result.get('slug', '').strip()
        # Sanitize slug
        slug = re.sub(r'[^a-z0-9-]', '', slug.lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        if not slug:
            slug = f"ai-{category.lower().replace(' ', '-')}"

        excerpt = result.get('excerpt', '')
        if not excerpt:
            # Auto-generate from body
            for line in body.split('\n'):
                stripped = line.strip()
                if stripped and not stripped.startswith('#'):
                    excerpt = stripped[:120]
                    break

        metadata = {
            "category": category,
            "tags": tags,
            "slug": slug[:30],
            "excerpt": excerpt[:150],
            "author": author,
            "reading_time": reading_time,
        }
    else:
        # Fallback metadata
        slug = re.sub(r'[^a-z0-9-]', '',
                      TitleSanitizer.to_slug(title)).strip('-')[:30] or "ai-article"
        metadata = {
            "category": category,
            "tags": ["AI", category],
            "slug": slug,
            "excerpt": body[:120].replace('\n', ' ') if body else "",
            "author": author,
            "reading_time": reading_time,
        }

    print(f"  Category: {metadata['category']}", file=sys.stderr)
    print(f"  Tags: {metadata['tags']}", file=sys.stderr)
    print(f"  Slug: {metadata['slug']}", file=sys.stderr)
    print(f"  Reading time: {metadata['reading_time']}min", file=sys.stderr)
    return metadata


def stage5_quality_gate(title, body, retry_callback=None):
    """Stage 5: Quality gate - score and optionally retry."""
    print(f"\n=== Stage 5: Quality Gate ===", file=sys.stderr)

    total, details, feedback = QualityScorer.score(title, body)
    report = QualityScorer.format_report(total, details, feedback)
    print(f"  {report}", file=sys.stderr)

    if details['passed']:
        print(f"  PASSED ({total}/100)", file=sys.stderr)
        return True, body

    print(f"  FAILED ({total}/100) - Attempting retry...", file=sys.stderr)

    if retry_callback:
        retry_prompt = QualityScorer.generate_retry_prompt(feedback)
        if retry_prompt:
            print(f"  Retry instructions: {retry_prompt[:200]}...", file=sys.stderr)
            revised_body = retry_callback(retry_prompt)
            if revised_body:
                # Re-score
                total2, details2, feedback2 = QualityScorer.score(title, revised_body)
                print(f"  Retry score: {total2}/100 ({'PASS' if details2['passed'] else 'FAIL'})", file=sys.stderr)
                if total2 > total:
                    return details2['passed'], revised_body

    # Return original even if failed (publish with warning)
    return False, body


def stage6_postprocess(filepath, posts_dir="_posts", skip_enrich=False):
    """Stage 6: Post-processing - textlint, enrich, OGP."""
    print(f"\n=== Stage 6: Post-Processing ===", file=sys.stderr)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)

    # 1. textlint --fix (optional, may not be installed)
    try:
        result = subprocess.run(
            ['textlint', '--fix', filepath],
            capture_output=True, text=True, timeout=60,
            cwd=project_dir
        )
        if result.returncode == 0:
            print("  textlint: fixed", file=sys.stderr)
        else:
            print(f"  textlint: skipped ({result.stderr[:100]})", file=sys.stderr)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("  textlint: not available", file=sys.stderr)

    # 2. enrich_article.py
    if not skip_enrich:
        enrich_script = os.path.join(script_dir, 'enrich_article.py')
        if os.path.exists(enrich_script):
            try:
                result = subprocess.run(
                    ['python3', enrich_script, filepath, posts_dir],
                    capture_output=True, text=True, timeout=120,
                    cwd=project_dir
                )
                if result.returncode == 0:
                    print("  enrich: done", file=sys.stderr)
                else:
                    print(f"  enrich: error ({result.stderr[:200]})", file=sys.stderr)
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                print(f"  enrich: failed ({e})", file=sys.stderr)

    # 3. generate_ogp_image.py
    ogp_script = os.path.join(script_dir, 'generate_ogp_image.py')
    if os.path.exists(ogp_script):
        try:
            result = subprocess.run(
                ['python3', ogp_script, filepath],
                capture_output=True, text=True, timeout=60,
                cwd=project_dir
            )
            if result.returncode == 0:
                print("  OGP image: generated", file=sys.stderr)
            else:
                print(f"  OGP image: skipped ({result.stderr[:100]})", file=sys.stderr)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print("  OGP image: not available", file=sys.stderr)


def build_frontmatter(title, metadata, now=None):
    """Build Jekyll frontmatter string."""
    if now is None:
        now = datetime.now(JST)

    date_str = now.strftime('%Y-%m-%d %H:%M:%S +0900')
    tags_str = json.dumps(metadata['tags'], ensure_ascii=False)

    fm = f"""---
layout: post
title: "{title}"
date: {date_str}
categories: [{metadata['category']}]
tags: {tags_str}
author: "{metadata['author']}"
excerpt: "{metadata['excerpt']}"
reading_time: {metadata['reading_time']}"""

    # Add internal linking metadata for E-E-A-T
    if 'related_articles' in metadata and metadata['related_articles']:
        related_str = json.dumps(metadata['related_articles'], ensure_ascii=False)
        fm += f"\nrelated_articles: {related_str}"

    if 'pillar_article' in metadata and metadata['pillar_article']:
        pillar_str = json.dumps(metadata['pillar_article'], ensure_ascii=False)
        fm += f"\npillar_article: {pillar_str}"

    fm += "\n---"
    return fm


def remove_body_title(body):
    """Remove the H1 title from body if present (it's in frontmatter)."""
    lines = body.split('\n')
    result = []
    title_removed = False
    for line in lines:
        if not title_removed and line.startswith('# ') and not line.startswith('##'):
            title_removed = True
            continue
        result.append(line)
    return '\n'.join(result).strip()


def generate_article(client, kb, topic, article_num, posts_dir="_posts",
                     dry_run=False, skip_enrich=False, compliance_loader=None,
                     persona_filter=None, sectional=False, linking_engine=None):
    """Generate a single article through the full pipeline.

    If sectional=True, uses 5-section generation with context preservation (Gemma-3-27b-it).
    Otherwise uses standard 6-stage pipeline (Gemini 2.5).

    If linking_engine is provided, injects internal links to related articles for E-E-A-T."""
    now = datetime.now(JST)

    print(f"\n{'='*60}", file=sys.stderr)
    print(f"ARTICLE {article_num}: [{topic['category']}] {topic.get('title_seed', '')}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Stage 2: Article Draft (choose generation method)
    if sectional and SECTIONAL_AVAILABLE:
        print(f"  [Pipeline] Using sectional generation (5-section with context)", file=sys.stderr)
        body = stage2_article_draft_sectional(topic, dry_run)
    else:
        if sectional and not SECTIONAL_AVAILABLE:
            print(f"  [Warning] Sectional pipeline not available, falling back to standard", file=sys.stderr)
        body = stage2_article_draft(client, kb, topic, compliance_loader, dry_run, persona_filter)

    if not body:
        print(f"  SKIP: Article generation failed", file=sys.stderr)
        return None

    # Apply persona masking to generated article (anonymize personal info)
    # Note: Sectional pipeline doesn't need masking as it doesn't mention individuals
    if persona_filter and body and not sectional:
        body = persona_filter.mask_personal_info(body)
        print(f"  [Persona Filter] Applied anonymization to article", file=sys.stderr)

    # Stage 3: Title Optimization
    title = stage3_title_optimization(client, topic, body, dry_run)

    # Stage 4: Metadata
    metadata = stage4_metadata(client, title, body, topic, dry_run)

    # E-E-A-T Enhancement: Add internal links for SEO (Pillar + Cluster strategy)
    if linking_engine and not dry_run:
        try:
            # Find related articles
            related_articles = linking_engine.find_related_articles(
                title, metadata['category'], body, max_links=3
            )
            if related_articles:
                metadata['related_articles'] = [
                    {'slug': slug, 'title': title, 'reason': reason}
                    for slug, title, reason in related_articles
                ]
                print(f"  [E-E-A-T] Added {len(related_articles)} internal links", file=sys.stderr)

            # Find pillar article (main reference)
            pillar = linking_engine.find_pillar_article(metadata['category'])
            if pillar:
                metadata['pillar_article'] = {'slug': pillar[0], 'title': pillar[1]}
                print(f"  [E-E-A-T] Linked to pillar: {pillar[1]}", file=sys.stderr)
        except Exception as e:
            print(f"  [E-E-A-T] Warning: {e}", file=sys.stderr)

    # Stage 5: Quality Gate (with retry callback)
    def retry_callback(improvement_prompt):
        revised_prompt = f"""以下の記事を改善してください。

【改善指示】
{improvement_prompt}

【元の記事】
{body[:6000]}

改善した記事全文をMarkdown形式で出力してください。"""
        return client.call(revised_prompt, max_tokens=8192)

    passed, final_body = stage5_quality_gate(title, body, retry_callback if not dry_run else None)

    if not passed:
        print(f"  WARNING: Article did not pass quality gate, publishing with warning", file=sys.stderr)

    # Remove H1 from body (title is in frontmatter)
    final_body = remove_body_title(final_body)

    # Build full article
    frontmatter = build_frontmatter(title, metadata, now)
    full_article = f"{frontmatter}\n\n{final_body}\n"

    # Write file
    date_prefix = now.strftime('%Y-%m-%d')
    slug = metadata['slug']
    filename = f"{date_prefix}-{article_num}-{slug}.md"
    filepath = os.path.join(posts_dir, filename)

    if dry_run:
        print(f"\n  [DRY RUN] Would write: {filepath}", file=sys.stderr)
        print(f"  Title: {title}", file=sys.stderr)
        print(f"  Category: {metadata['category']}", file=sys.stderr)
        print(f"  Tags: {metadata['tags']}", file=sys.stderr)
        print(f"  Body length: {len(final_body)} chars", file=sys.stderr)
        print(f"  Quality: {'PASS' if passed else 'FAIL'}", file=sys.stderr)
        return filepath

    os.makedirs(posts_dir, exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(full_article)

    print(f"  Written: {filepath} ({len(full_article)} chars)", file=sys.stderr)

    # Stage 6: Post-processing
    stage6_postprocess(filepath, posts_dir, skip_enrich)

    return filepath


def main():
    parser = argparse.ArgumentParser(
        description='AI Article Generation Pipeline'
    )
    parser.add_argument('--articles', type=int, default=3,
                        help='Number of articles to generate (default: 3)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview without generating')
    parser.add_argument('--skip-enrich', action='store_true',
                        help='Skip enrich_article.py post-processing')
    parser.add_argument('--posts-dir', default='_posts',
                        help='Posts directory (default: _posts)')
    parser.add_argument('--kb-dir', default=None,
                        help='Knowledge base directory')
    parser.add_argument('--sectional', action='store_true',
                        help='Use sectional generation pipeline (5-section with context)')
    args = parser.parse_args()

    print(f"Article Pipeline v2.0 - {datetime.now(JST).strftime('%Y-%m-%d %H:%M JST')}", file=sys.stderr)
    print(f"Articles: {args.articles}, Dry run: {args.dry_run}", file=sys.stderr)

    # Initialize
    try:
        client = GeminiClient()
    except ValueError as e:
        if args.dry_run:
            print(f"WARNING: {e} (dry-run mode, continuing)", file=sys.stderr)
            client = None
        else:
            print(f"ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    kb = KnowledgeBase(args.kb_dir)

    # Initialize compliance loader (optional)
    cl = None
    if ComplianceLoader is not None:
        try:
            cl = ComplianceLoader()
            print(f"Compliance knowledge: {'loaded' if (cl.base_dir / 'compliance').exists() else 'not found'}", file=sys.stderr)
        except Exception as e:
            print(f"Compliance loader init failed (skipping): {e}", file=sys.stderr)

    # Initialize persona filter (optional, for Digital Twin SDK integration)
    pf = None
    try:
        pf = load_persona_filter()
        print(f"Persona filter: loaded from Digital Twin SDK", file=sys.stderr)
    except Exception as e:
        print(f"Persona filter init failed (skipping): {e}", file=sys.stderr)

    # Initialize internal linking engine (E-E-A-T enhancement)
    le = None
    try:
        le = get_internal_linking_engine(args.posts_dir)
        stats = le.get_linking_statistics()
        print(f"Internal linking engine: {stats['total_articles']} articles indexed", file=sys.stderr)
    except Exception as e:
        print(f"Internal linking init failed (skipping): {e}", file=sys.stderr)

    # Stage 1: Topic Planning
    topics = stage1_topic_planning(client, kb, args.articles, args.dry_run)

    if not topics:
        print("ERROR: No topics generated", file=sys.stderr)
        sys.exit(1)

    # Generate articles
    results = []
    for i, topic in enumerate(topics):
        filepath = generate_article(
            client, kb, topic, i + 1,
            posts_dir=args.posts_dir,
            dry_run=args.dry_run,
            skip_enrich=args.skip_enrich,
            compliance_loader=cl,
            persona_filter=pf,
            sectional=args.sectional,
            linking_engine=le
        )
        if filepath:
            results.append(filepath)

    # Summary
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"PIPELINE COMPLETE", file=sys.stderr)
    print(f"  Generated: {len(results)}/{args.articles} articles", file=sys.stderr)
    for r in results:
        print(f"  - {r}", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)

    # Exit with error if no articles generated
    if not results:
        sys.exit(1)


if __name__ == '__main__':
    main()
