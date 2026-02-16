#!/usr/bin/env python3
"""
記事エンリッチメントスクリプト
- 内部リンク自動生成（関連記事への参照を本文中に挿入）
- Amazonアソシエイトリンク自動挿入（記事末尾、ASIN直リンク対応）
- コンサルティングCTA自動挿入
- FAQスキーマ自動生成

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

# AI関連のおすすめ書籍（キーワードマッチで選択、ASIN直リンク対応）
AMAZON_RECOMMENDATIONS = [
    {
        "keywords": ["openai", "chatgpt", "gpt", "プロンプト", "llm"],
        "title": "生成AIプロンプトエンジニアリング入門",
        "asin": "4798181986",
        "search": "ChatGPT+プロンプトエンジニアリング+入門",
        "description": "ChatGPTとMidjourneyで学ぶプロンプト設計の基本と実践テクニック",
    },
    {
        "keywords": ["投資", "市場", "資金調達", "評価額", "roi", "株"],
        "title": "生成AI活用の最前線",
        "asin": "4492558454",
        "search": "生成AI+ビジネス活用+企業事例",
        "description": "世界の企業100社超のAI活用事例から投資・導入判断のヒントを得る",
    },
    {
        "keywords": ["nvidia", "gpu", "チップ", "半導体", "blackwell", "cuda"],
        "title": "増補改訂 GPUを支える技術",
        "asin": "4297119544",
        "search": "GPU+技術+並列処理+NVIDIA",
        "description": "超並列ハードウェアの仕組みからAI半導体の最新動向まで網羅的に解説",
    },
    {
        "keywords": ["google", "gemini", "deepmind"],
        "title": "Google Gemini 100%活用ガイド",
        "asin": "4297142651",
        "search": "Google+Gemini+活用+ガイド",
        "description": "無料で使えるAIアシスタントGeminiの機能と実践的な活用法を完全網羅",
    },
    {
        "keywords": ["エージェント", "agent", "自動化", "ワークフロー", "自律"],
        "title": "AIエージェント開発/運用入門",
        "asin": "4815636605",
        "search": "AIエージェント+開発+運用+入門",
        "description": "自律型AIエージェントの設計・開発から本番運用までを体系的に解説",
    },
    {
        "keywords": ["規制", "法律", "ガバナンス", "倫理", "eu", "法務"],
        "title": "生成AI法務・ガバナンス",
        "asin": "4785730706",
        "search": "生成AI+法務+ガバナンス+規制",
        "description": "AI法規制の最新動向と企業が取るべきガバナンス体制を実務視点で解説",
    },
    {
        "keywords": ["microsoft", "azure", "copilot"],
        "title": "Microsoft Copilot for Microsoft 365活用大全",
        "asin": "4296080342",
        "search": "Copilot+Microsoft+365+活用",
        "description": "Copilot×Microsoft 365の全機能を活用して業務効率を劇的に改善する方法",
    },
    {
        "keywords": ["anthropic", "claude", "安全性", "アライメント"],
        "title": "ゼロからわかる 生成AI法律入門",
        "asin": "402251938X",
        "search": "生成AI+法律+入門+著作権",
        "description": "AI安全性・著作権・個人情報など、分野別の法的課題と対策を丁寧に解説",
    },
    {
        "keywords": ["dx", "デジタル", "変革", "トランスフォーメーション", "製造"],
        "title": "デジタルトランスフォーメーション・ジャーニー",
        "asin": "4798172561",
        "search": "DX+組織変革+ジャーニー",
        "description": "組織のデジタル化から分断を乗り越えて変革にたどりつくまでの実践ガイド",
    },
    {
        "keywords": ["ビジネス", "活用", "導入", "戦略", "経営"],
        "title": "AI白書 2025 生成AIエディション",
        "asin": "4049112388",
        "search": "AI白書+2025+生成AI",
        "description": "松尾研究室監修、国内外の生成AI動向を網羅した年次レポート決定版",
    },
]

# デフォルト推薦（どのキーワードにもマッチしない場合）
DEFAULT_RECOMMENDATION = {
    "title": "AI白書 2025 生成AIエディション",
    "asin": "4049112388",
    "search": "AI白書+2025+生成AI",
    "description": "松尾研究室監修、国内外の生成AI動向を網羅した年次レポート決定版",
}


def amazon_search_url(search_term: str) -> str:
    """Amazonアソシエイト検索URLを生成"""
    import urllib.parse
    encoded = urllib.parse.quote_plus(search_term)
    return f"https://www.amazon.co.jp/s?k={encoded}&tag={AMAZON_STORE_ID}"


def amazon_asin_url(asin: str) -> str:
    """AmazonアソシエイトASIN直リンクURLを生成"""
    return f"https://www.amazon.co.jp/dp/{asin}/?tag={AMAZON_STORE_ID}"


def select_recommendations(content: str, max_items: int = 3) -> list:
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
    """Amazon推薦セクションのMarkdownを生成（ASIN直リンク対応）"""
    lines = []
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## この記事に関連するおすすめ書籍")
    lines.append("")

    for rec in recommendations:
        if rec.get("asin"):
            url = amazon_asin_url(rec["asin"])
        else:
            url = amazon_search_url(rec["search"])
        lines.append(f"### [{rec['title']}]({url})")
        lines.append("")
        lines.append(rec["description"])
        lines.append("")
        lines.append(f"[Amazonで詳しく見る →]({url})")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("*※ 本ページのリンクにはアフィリエイトリンクが含まれます。購入によりサイト運営をサポートいただけます。*")
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
        "text": "AI導入支援の経験から、実践的な戦略策定をお手伝いしています。",
        "cta_text": "お問い合わせはこちら",
        "cta_url": "/contact/?utm_source=article&utm_medium=cta&utm_campaign=strategy",
    },
    "AI技術ガイド": {
        "heading": "技術選定のご相談を承っています",
        "text": "実装経験に基づく技術選定のアドバイスをしています。PoC開発もお気軽にご相談ください。",
        "cta_text": "お問い合わせはこちら",
        "cta_url": "/services/?utm_source=article&utm_medium=cta&utm_campaign=tech_guide",
    },
    "業界別AI活用": {
        "heading": "業界に合わせたAI活用をご提案しています",
        "text": "多業界での開発経験を活かし、業界特有の課題に合わせたAI活用戦略をご提案しています。",
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
    """記事にAmazonリンク、内部リンク、CTAを追加"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # 既にエンリッチ済みかチェック
    if f"tag={AMAZON_STORE_ID}" in content:
        print(f"  [SKIP] 既にエンリッチ済み: {os.path.basename(filepath)}")
        return False

    # 中間広告の挿入
    content = insert_mid_article_ad(content)

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
