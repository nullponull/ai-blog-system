#!/usr/bin/env python3
"""
記事エンリッチメントスクリプト
- 内部リンク自動生成（関連記事への参照を本文中に挿入）
- Amazonアソシエイトリンク自動挿入（記事末尾）
- 比較表テンプレート挿入（企業/技術比較がある記事）

使い方:
  python3 scripts/enrich_article.py _posts/2025-12-10-*.md
  python3 scripts/enrich_article.py _posts/  # ディレクトリ指定で今日の記事全て
"""

import os
import sys
import re
import glob
from datetime import datetime

# ============================================================
# Amazon アソシエイト設定
# ============================================================
AMAZON_STORE_ID = "nullpodesu-22"

# AI関連のおすすめ書籍/ツール（キーワードマッチで選択）
AMAZON_RECOMMENDATIONS = [
    {
        "keywords": ["openai", "chatgpt", "gpt", "プロンプト"],
        "title": "ChatGPT/LLMプログラミング実践入門",
        "search": "ChatGPT+プログラミング+実践",
        "description": "LLMを活用した開発の実践ガイド",
    },
    {
        "keywords": ["投資", "市場", "資金調達", "評価額", "roi"],
        "title": "AI投資の最前線",
        "search": "AI+投資+最前線",
        "description": "AI企業への投資判断に役立つ分析手法",
    },
    {
        "keywords": ["nvidia", "gpu", "チップ", "半導体", "blackwell"],
        "title": "GPU・AIチップの技術動向",
        "search": "GPU+AI+半導体+技術",
        "description": "AI半導体の最新アーキテクチャ解説",
    },
    {
        "keywords": ["google", "gemini", "deepmind"],
        "title": "Googleの生成AI戦略",
        "search": "Google+AI+戦略+生成AI",
        "description": "Googleが目指すAIの未来像を読み解く",
    },
    {
        "keywords": ["エージェント", "agent", "自動化", "ワークフロー"],
        "title": "AIエージェント開発入門",
        "search": "AI+エージェント+開発+入門",
        "description": "自律型AIエージェントの設計と実装",
    },
    {
        "keywords": ["規制", "法律", "ガバナンス", "倫理", "eu"],
        "title": "AI規制とガバナンスの実務",
        "search": "AI+規制+ガバナンス+法律",
        "description": "AI法規制の最新動向と企業対応",
    },
    {
        "keywords": ["microsoft", "azure", "copilot"],
        "title": "Microsoft AI活用ガイド",
        "search": "Microsoft+Azure+AI+Copilot",
        "description": "CopilotとAzure AIの実践活用",
    },
    {
        "keywords": ["anthropic", "claude", "安全性", "アライメント"],
        "title": "AI安全性とアライメント",
        "search": "AI+安全性+アライメント+入門",
        "description": "責任あるAI開発の基礎知識",
    },
]

# デフォルト推薦（どのキーワードにもマッチしない場合）
DEFAULT_RECOMMENDATION = {
    "title": "AI白書 2025",
    "search": "AI白書+2025+人工知能",
    "description": "国内外のAI動向を網羅した年次レポート",
}


def amazon_search_url(search_term: str) -> str:
    """Amazonアソシエイト検索URLを生成"""
    import urllib.parse
    encoded = urllib.parse.quote_plus(search_term)
    return f"https://www.amazon.co.jp/s?k={encoded}&tag={AMAZON_STORE_ID}"


def select_recommendations(content: str, max_items: int = 2) -> list:
    """記事内容に基づいて最適なAmazon推薦を選択"""
    content_lower = content.lower()
    scored = []

    for rec in AMAZON_RECOMMENDATIONS:
        score = sum(1 for kw in rec["keywords"] if kw in content_lower)
        if score > 0:
            scored.append((score, rec))

    scored.sort(key=lambda x: -x[0])
    selected = [item[1] for item in scored[:max_items]]

    if not selected:
        selected = [DEFAULT_RECOMMENDATION]

    return selected


def build_amazon_section(recommendations: list) -> str:
    """Amazon推薦セクションのMarkdownを生成"""
    lines = []
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## この記事に関連するおすすめ書籍")
    lines.append("")

    for rec in recommendations:
        url = amazon_search_url(rec["search"])
        lines.append(f"**[{rec['title']}]({url})**")
        lines.append(f"  {rec['description']}")
        lines.append("")

    lines.append(f"*※ 上記リンクはAmazonアソシエイトリンクです*")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# コンサルティングCTA自動挿入
# ============================================================
# カテゴリ別CTA設定（個人ブランド→ALLFORCES導線）
CONSULTING_CTA_MAP = {
    "導入事例": {
        "heading": "AI導入のご相談を承っています",
        "text": "本記事のようなAI導入プロジェクトの実務経験を活かし、戦略策定からPoC開発、本番システム構築までお手伝いしています。お気軽にご相談ください。",
        "cta_text": "お問い合わせはこちら",
        "cta_url": "/contact/?utm_source=article&utm_medium=cta&utm_campaign=case_study",
    },
    "AI導入戦略": {
        "heading": "AI導入戦略のご相談を承っています",
        "text": "AI実装プロジェクト開発や多業界のAI導入支援の経験から、実践的な戦略策定をお手伝いしています。",
        "cta_text": "お問い合わせはこちら",
        "cta_url": "/contact/?utm_source=article&utm_medium=cta&utm_campaign=strategy",
    },
    "AI技術ガイド": {
        "heading": "技術選定のご相談を承っています",
        "text": "AI対話システムからMLOpsまで、実装経験に基づく技術選定のアドバイスをしています。PoC開発もお気軽にご相談ください。",
        "cta_text": "お問い合わせはこちら",
        "cta_url": "/services/?utm_source=article&utm_medium=cta&utm_campaign=tech_guide",
    },
    "業界別AI活用": {
        "heading": "業界に合わせたAI活用をご提案しています",
        "text": "公共・金融・通信・教育・エンタメなど多業界での開発経験を活かし、業界特有の課題に合わせたAI活用戦略をご提案しています。",
        "cta_text": "お問い合わせはこちら",
        "cta_url": "/services/?utm_source=article&utm_medium=cta&utm_campaign=industry",
    },
    "AI最新ニュース": {
        "heading": "AI活用の実践ノウハウを発信中",
        "text": "AI技術の最新動向と実務へのインパクトを、実装経験を交えて解説しています。",
        "cta_text": "他の記事も読む",
        "cta_url": "/?utm_source=article&utm_medium=cta&utm_campaign=news",
    },
    "研究論文": {
        "heading": "研究成果のビジネス応用をお手伝いしています",
        "text": "研究開発の経験を活かし、最新研究の実務応用についてアドバイスしています。",
        "cta_text": "お問い合わせはこちら",
        "cta_url": "/services/?utm_source=article&utm_medium=cta&utm_campaign=research",
    },
}


def get_article_category(content: str) -> str:
    """記事のfront matterからカテゴリを取得"""
    in_frontmatter = False
    for line in content.split("\n"):
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break
        if in_frontmatter and line.startswith("categories:"):
            cat_str = line.replace("categories:", "").strip().strip("[]")
            cats = [c.strip().strip('"').strip("'") for c in cat_str.split(",")]
            return cats[0] if cats else ""
    return ""


def build_consulting_cta_section(category: str) -> str:
    """カテゴリに基づくコンサルティングCTAセクションを生成"""
    cta_config = CONSULTING_CTA_MAP.get(category)
    if not cta_config:
        return ""

    lines = []
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(f"## {cta_config['heading']}")
    lines.append("")
    lines.append(f"{cta_config['text']}")
    lines.append("")
    lines.append(f"[{cta_config['cta_text']}]({cta_config['cta_url']})")
    lines.append("{: .consulting-cta-link}")
    lines.append("")

    return "\n".join(lines)


# ============================================================
# 記事内中間広告の挿入
# ============================================================
def insert_mid_article_ad(content: str) -> str:
    """2番目のH2見出しの前に中間広告を挿入"""
    # frontmatterの終了位置を特定
    fm_end = content.find("---", content.find("---") + 3)
    if fm_end == -1:
        return content

    # frontmatter以降のH2見出しを全て検出
    body = content[fm_end:]
    h2_positions = [m.start() + fm_end for m in re.finditer(r'\n## ', body)]

    # 2番目のH2がある場合、その前に広告を挿入
    if len(h2_positions) >= 2:
        insert_pos = h2_positions[1]
        ad_html = '\n\n{% include ads-mid-article.html %}\n\n'
        content = content[:insert_pos] + ad_html + content[insert_pos:]

    return content


# ============================================================
# FAQスキーマ自動生成
# ============================================================
def generate_faq_schema(content: str) -> str:
    """H2/H3見出しから疑問形のものをFAQスキーマとして抽出"""
    # frontmatterの終了位置を特定
    fm_end = content.find("---", content.find("---") + 3)
    if fm_end == -1:
        return ""

    body = content[fm_end:]

    # 疑問形の見出しを検出（？で終わるか、「とは」「なぜ」「どう」を含む）
    faq_pattern = re.compile(r'^#{2,3}\s+(.+(?:\？|とは|なぜ|どう|どの|何が|いつ).*)$', re.MULTILINE)
    headings = faq_pattern.findall(body)

    if not headings:
        return ""

    # 各見出しの直後のパラグラフを回答として抽出
    faq_items = []
    for heading in headings[:5]:  # 最大5件
        # 見出しの後の本文を取得
        heading_escaped = re.escape(heading)
        answer_match = re.search(
            rf'^#{{{2,3}}}\s+{heading_escaped}\s*\n+(.+?)(?=\n#|\n---|\Z)',
            body,
            re.MULTILINE | re.DOTALL
        )
        if answer_match:
            answer = answer_match.group(1).strip()
            # 最初の段落のみ使用
            first_para = answer.split('\n\n')[0].strip()
            # Markdownの装飾を除去
            first_para = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', first_para)
            first_para = re.sub(r'[*_`]', '', first_para)
            if len(first_para) > 30:  # 短すぎる回答は除外
                faq_items.append({
                    "question": heading.strip().replace('"', '\\"'),
                    "answer": first_para[:500].replace('"', '\\"')
                })

    if not faq_items:
        return ""

    # JSON-LD構造化データを生成
    faq_entries = []
    for item in faq_items:
        faq_entries.append(f'''    {{
      "@type": "Question",
      "name": "{item['question']}",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "{item['answer']}"
      }}
    }}''')

    separator = ",\n"
    entries_str = separator.join(faq_entries)
    schema = f'''
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
{entries_str}
  ]
}}
</script>
'''
    return schema


# ============================================================
# 比較表テンプレート自動挿入
# ============================================================
# 企業/技術比較の文脈を検出するパターン
COMPARISON_PATTERNS = [
    # "A vs B", "A対B", "AとBの比較" パターン
    re.compile(r'(\w+)\s*(?:vs\.?|VS\.?|対)\s*(\w+)', re.IGNORECASE),
    re.compile(r'(\w+)\s*と\s*(\w+)\s*の(?:比較|違い|差)', re.IGNORECASE),
]

# 企業/技術の比較テンプレートデータ
COMPARISON_TEMPLATES = {
    frozenset({"openai", "google"}): {
        "title": "OpenAI vs Google AI 比較",
        "headers": ["項目", "OpenAI", "Google"],
        "rows": [
            ["主力モデル", "GPT-4o / o1", "Gemini 2.0"],
            ["API価格帯", "中〜高", "低〜中"],
            ["強み", "推論・コード生成", "マルチモーダル・検索統合"],
            ["エコシステム", "ChatGPT / API", "Google Cloud / Android"],
        ],
    },
    frozenset({"openai", "anthropic"}): {
        "title": "OpenAI vs Anthropic 比較",
        "headers": ["項目", "OpenAI", "Anthropic"],
        "rows": [
            ["主力モデル", "GPT-4o / o1", "Claude 4.5"],
            ["重視する価値", "汎用性・スケール", "安全性・誠実性"],
            ["API価格帯", "中〜高", "中"],
            ["強み", "広範なエコシステム", "長文処理・コーディング"],
        ],
    },
    frozenset({"nvidia", "amd"}): {
        "title": "NVIDIA vs AMD AI半導体 比較",
        "headers": ["項目", "NVIDIA", "AMD"],
        "rows": [
            ["主力AI GPU", "H100 / B200", "MI300X"],
            ["市場シェア", "約80%", "約15%"],
            ["ソフトウェア基盤", "CUDA（業界標準）", "ROCm"],
            ["強み", "エコシステム支配力", "コスト競争力"],
        ],
    },
    frozenset({"microsoft", "google"}): {
        "title": "Microsoft vs Google AI戦略 比較",
        "headers": ["項目", "Microsoft", "Google"],
        "rows": [
            ["AI投資先", "OpenAIパートナーシップ", "DeepMind自社開発"],
            ["統合製品", "Copilot / Azure AI", "Gemini / Google Cloud"],
            ["戦略", "企業向けAI統合", "消費者+クラウド両面"],
            ["強み", "エンタープライズ基盤", "データ量・研究力"],
        ],
    },
}


def detect_comparison_context(content: str) -> list:
    """記事内の企業/技術比較コンテキストを検出"""
    content_lower = content.lower()
    matches = []

    for template_key, template_data in COMPARISON_TEMPLATES.items():
        entities = list(template_key)
        if all(e in content_lower for e in entities):
            matches.append(template_data)

    return matches


def build_comparison_table(template: dict) -> str:
    """Markdown形式の比較表を生成"""
    lines = []
    lines.append("")
    lines.append(f"### {template['title']}")
    lines.append("")

    # ヘッダー
    lines.append("| " + " | ".join(template["headers"]) + " |")
    lines.append("|" + "|".join(["---"] * len(template["headers"])) + "|")

    # データ行
    for row in template["rows"]:
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    return "\n".join(lines)


# ============================================================
# 内部リンク自動生成
# ============================================================
def find_related_posts(current_file: str, posts_dir: str, max_links: int = 3) -> list:
    """タグとカテゴリに基づいて関連記事を検索"""
    current_tags = set()
    current_category = ""
    current_title = ""

    # 現在の記事のメタデータを取得
    with open(current_file, "r", encoding="utf-8") as f:
        content = f.read()

    in_frontmatter = False
    for line in content.split("\n"):
        if line.strip() == "---":
            if not in_frontmatter:
                in_frontmatter = True
                continue
            else:
                break
        if in_frontmatter:
            if line.startswith("tags:"):
                tags_str = line.replace("tags:", "").strip()
                tags_str = tags_str.strip("[]")
                current_tags = {t.strip().strip('"').strip("'") for t in tags_str.split(",")}
            elif line.startswith("categories:"):
                cat_str = line.replace("categories:", "").strip()
                cat_str = cat_str.strip("[]")
                cats = [c.strip().strip('"').strip("'") for c in cat_str.split(",")]
                current_category = cats[0] if cats else ""
            elif line.startswith("title:"):
                current_title = line.replace("title:", "").strip().strip('"')

    if not current_tags:
        return []

    # 他の記事をスキャン
    candidates = []
    current_basename = os.path.basename(current_file)

    for post_file in glob.glob(os.path.join(posts_dir, "*.md")):
        if os.path.basename(post_file) == current_basename:
            continue

        try:
            with open(post_file, "r", encoding="utf-8") as f:
                post_content = f.read(2000)  # frontmatterだけ読む
        except Exception:
            continue

        post_tags = set()
        post_title = ""
        post_date = ""
        in_fm = False

        for line in post_content.split("\n"):
            if line.strip() == "---":
                if not in_fm:
                    in_fm = True
                    continue
                else:
                    break
            if in_fm:
                if line.startswith("tags:"):
                    tags_str = line.replace("tags:", "").strip().strip("[]")
                    post_tags = {t.strip().strip('"').strip("'") for t in tags_str.split(",")}
                elif line.startswith("title:"):
                    post_title = line.replace("title:", "").strip().strip('"')
                elif line.startswith("date:"):
                    post_date = line.replace("date:", "").strip()[:10]

        if not post_title or not post_tags:
            continue

        # タグの重複度でスコアリング
        overlap = len(current_tags & post_tags)
        if overlap > 0:
            # ファイル名からURLパスを生成
            basename = os.path.basename(post_file).replace(".md", "")
            # YYYY-MM-DD-slug → /YYYY/MM/DD/slug/
            parts = basename.split("-", 3)
            if len(parts) >= 4:
                slug_part = parts[3]
                # 日本語を含むslugはURLエンコード
                import urllib.parse
                slug_part = urllib.parse.quote(slug_part, safe='-_')
                url_path = f"/{parts[0]}/{parts[1]}/{parts[2]}/{slug_part}/"
            else:
                url_path = f"/{basename}/"

            candidates.append({
                "title": post_title,
                "url": url_path,
                "score": overlap,
                "date": post_date,
            })

    # スコア順、同スコアなら新しい記事優先
    candidates.sort(key=lambda x: (-x["score"], x["date"]), reverse=False)
    candidates.sort(key=lambda x: -x["score"])

    return candidates[:max_links]


def build_internal_links_section(related: list) -> str:
    """内部リンクセクションのMarkdownを生成"""
    if not related:
        return ""

    lines = []
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("### あわせて読みたい")
    lines.append("")

    for post in related:
        lines.append(f"- [{post['title']}]({post['url']})")

    lines.append("")
    return "\n".join(lines)


# ============================================================
# メイン処理
# ============================================================
def enrich_article(filepath: str, posts_dir: str):
    """記事にAmazonリンク、内部リンク、比較表を追加"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 既にエンリッチ済みかチェック
    if f"tag={AMAZON_STORE_ID}" in content:
        print(f"  [SKIP] 既にエンリッチ済み: {os.path.basename(filepath)}")
        return False

    # 中間広告の挿入
    content = insert_mid_article_ad(content)

    # 比較表を本文中に挿入（最初のH2セクション後、2番目のH2の前に配置）
    comparison_tables = detect_comparison_context(content)
    comparison_count = 0
    if comparison_tables:
        table_md = ""
        for tpl in comparison_tables[:2]:  # 最大2テーブル
            table_md += build_comparison_table(tpl)
        comparison_count = len(comparison_tables[:2])

        # frontmatterの後のH2見出しを全て検出し、2番目のH2前に挿入
        fm_end = content.find("---", content.find("---") + 3)
        if fm_end != -1:
            body_after_fm = content[fm_end:]
            h2_positions = [m.start() + fm_end for m in re.finditer(r'\n## ', body_after_fm)]
            if len(h2_positions) >= 2:
                # 2番目のH2の前に挿入（最初のセクション後）
                insert_pos = h2_positions[1]
                content = content[:insert_pos] + "\n" + table_md + content[insert_pos:]
            elif len(h2_positions) == 1:
                # H2が1個のみ: その直後の次の空行の後に挿入
                first_h2 = h2_positions[0]
                # 最初のH2の後のセクション末尾を探す
                next_section = content.find("\n\n", first_h2 + 4)
                if next_section != -1:
                    content = content[:next_section] + "\n" + table_md + content[next_section:]

    # Amazonアソシエイト推薦を選択
    recommendations = select_recommendations(content)
    amazon_section = build_amazon_section(recommendations)

    # 内部リンクを検索
    related = find_related_posts(filepath, posts_dir)
    internal_section = build_internal_links_section(related)

    # コンサルティングCTAを生成
    category = get_article_category(content)
    consulting_section = build_consulting_cta_section(category)

    # 記事末尾に追加（---END---マーカーがあれば除去して末尾に追加）
    content = content.rstrip()
    content = re.sub(r'\n*---END---\s*$', '', content)

    content += internal_section
    content += consulting_section
    content += amazon_section

    # FAQスキーマの生成と挿入
    faq_schema = generate_faq_schema(content)
    if faq_schema:
        content += faq_schema

    content += "\n"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    rec_titles = [r["title"] for r in recommendations]
    related_count = len(related)
    print(f"  [OK] {os.path.basename(filepath)}")
    print(f"       比較表: {comparison_count}件")
    print(f"       Amazon: {', '.join(rec_titles)}")
    print(f"       内部リンク: {related_count}件")

    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 enrich_article.py <file_or_dir> [posts_dir]")
        print("  file_or_dir: 記事ファイルまたは_postsディレクトリ")
        print("  posts_dir: 内部リンク検索用ディレクトリ（デフォルト: _posts）")
        sys.exit(1)

    target = sys.argv[1]
    posts_dir = sys.argv[2] if len(sys.argv) > 2 else "_posts"

    if os.path.isdir(target):
        # ディレクトリ指定: 今日の記事を処理
        today = datetime.now().strftime("%Y-%m-%d")
        files = sorted(glob.glob(os.path.join(target, f"{today}-*.md")))
        if not files:
            # 今日の記事がなければ最新の記事を処理
            files = sorted(glob.glob(os.path.join(target, "*.md")))[-3:]
        posts_dir = target
    else:
        files = [target]
        if not os.path.isdir(posts_dir):
            posts_dir = os.path.dirname(target) or "_posts"

    print(f"記事エンリッチメント開始 ({len(files)}件)")
    print(f"  Amazon Store ID: {AMAZON_STORE_ID}")
    print(f"  内部リンク検索: {posts_dir}")
    print()

    enriched = 0
    for f in files:
        if os.path.isfile(f) and f.endswith(".md"):
            if enrich_article(f, posts_dir):
                enriched += 1

    print(f"\n完了: {enriched}/{len(files)}件をエンリッチ")


if __name__ == "__main__":
    main()
