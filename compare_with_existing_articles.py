#!/usr/bin/env python3
"""
セクショナル生成記事 vs 既存 AI メディア記事 の品質比較分析

比較項目：
- 文字数
- AI臭スコア（機械的表現の検出）
- 具体性スコア（企業名、数値、実装例）
- 読みやすさ（段落数、平均段落長）
- SEOスコア（キーワード密度、見出し構成）
"""

import re
import json
from pathlib import Path
from collections import Counter
from typing import Dict, List, Tuple


class ArticleQualityComparer:
    def __init__(self):
        self.ai_smell_patterns = {
            'いかがでしたか': r'いかがでしたか|いかがでしょう',
            'さあ始めましょう': r'さあ始めましょう|さっそく始めましょう',
            '本当の価値': r'本当の価値|真の価値',
            '間違いなく': r'間違いなく|確実に',
            'ぜひ': r'\bぜひ\b',
            'つまり': r'\bつまり\b|\bすなわち\b',
            'まずは': r'まずは|最初は',
        }

    def analyze_article(self, content: str, article_name: str = "Unknown") -> Dict:
        """記事を分析してスコアを計算"""
        if not content:
            return None

        # テキスト統計
        lines = content.split('\n')
        paragraphs = [l for l in lines if l.strip() and not l.startswith('#')]
        words = content.split()
        sentences = len(re.split(r'[。！？]', content))

        stats = {
            'article_name': article_name,
            'total_chars': len(content),
            'total_words': len(words),
            'sentences': sentences,
            'paragraphs': len(paragraphs),
            'avg_paragraph_chars': len(content) / len(paragraphs) if paragraphs else 0,
            'avg_sentence_length': len(content) / sentences if sentences > 0 else 0,
        }

        # AI臭検出
        ai_smell_score = 0
        ai_smell_details = {}

        for pattern_name, pattern in self.ai_smell_patterns.items():
            matches = len(re.findall(pattern, content))
            if matches > 0:
                ai_smell_details[pattern_name] = matches
                ai_smell_score += matches * 3

        # 具体性スコア（企業名、数値）
        company_matches = len(re.findall(r'[A-Z][a-z]+|[ァ-ヶー]+(?:会社|Inc|Ltd|Corp|AI|サービス)', content))
        number_matches = len(re.findall(r'\d+(?:%|万|億|年|月|日|時間|分|秒|ドル|円)?', content))

        specificity_score = min(100, (company_matches + number_matches) * 2)

        # 見出し分析
        headings = len(re.findall(r'^#{1,3}\s+', content, re.MULTILINE))
        heading_ratio = (headings / max(1, len(lines))) * 100

        # キーワード密度（AI, 企業, 技術など）
        ai_keywords = len(re.findall(r'AI|機械学習|深層学習|モデル|生成|ニューラル|アルゴリズム', content, re.IGNORECASE))

        # 総合スコア（0-100）
        quality_score = 100
        quality_score -= ai_smell_score  # AI臭減点
        quality_score -= abs(stats['avg_paragraph_chars'] - 300) / 10  # 段落長の最適性
        quality_score = max(0, quality_score)

        return {
            'article_name': article_name,
            'stats': stats,
            'quality_score': quality_score,
            'ai_smell_score': max(0, 100 - ai_smell_score),  # 低いほど悪い
            'ai_smell_details': ai_smell_details,
            'specificity_score': specificity_score,
            'company_mentions': company_matches,
            'number_mentions': number_matches,
            'headings_count': headings,
            'heading_ratio': heading_ratio,
            'ai_keyword_density': (ai_keywords / len(words) * 100) if words else 0,
        }

    def compare_articles(self, articles_dict: Dict[str, str]) -> Dict:
        """複数の記事を比較分析"""
        results = {}

        for article_name, content in articles_dict.items():
            analysis = self.analyze_article(content, article_name)
            if analysis:
                results[article_name] = analysis

        return results

    def generate_comparison_report(self, results: Dict, output_file: str = None) -> str:
        """比較レポートを生成"""
        report = """# セクショナル生成記事 vs 既存 AI メディア記事 — 品質比較分析

## 📊 比較結果

### 総合スコア比較

| 記事 | 総合点 | AI臭 | 具体性 | 見出し | キーワード密度 |
|------|--------|--------|--------|--------|-----------|
"""

        # スコア順にソート
        sorted_articles = sorted(results.items(), key=lambda x: x[1]['quality_score'], reverse=True)

        for article_name, analysis in sorted_articles:
            report += f"| {article_name:30s} | {analysis['quality_score']:6.1f} | {analysis['ai_smell_score']:6.1f} | {analysis['specificity_score']:6.1f} | {analysis['heading_ratio']:6.1f}% | {analysis['ai_keyword_density']:6.2f}% |\n"

        # 詳細統計
        report += "\n### 文字数・構成の比較\n\n"
        report += "| 記事 | 文字数 | 文数 | 段落数 | 平均段落長 | 見出し数 |\n"
        report += "|------|--------|--------|--------|-----------|----------|\n"

        for article_name, analysis in sorted_articles:
            stats = analysis['stats']
            report += f"| {article_name:30s} | {stats['total_chars']:7d} | {stats['sentences']:5d} | {stats['paragraphs']:6d} | {stats['avg_paragraph_chars']:9.0f} | {analysis['headings_count']:8d} |\n"

        # AI臭詳細
        report += "\n### AI臭パターン検出\n\n"
        for article_name, analysis in sorted_articles:
            if analysis['ai_smell_details']:
                report += f"**{article_name}** (スコア: {analysis['ai_smell_score']:.1f}):\n"
                for pattern, count in sorted(analysis['ai_smell_details'].items(), key=lambda x: -x[1]):
                    report += f"  - {pattern}: {count}回\n"
            else:
                report += f"**{article_name}**: AI臭なし ✅\n"

        # 具体性分析
        report += "\n### 具体性指標\n\n"
        report += "| 記事 | 企業名 | 数値 | 具体性スコア |\n"
        report += "|------|--------|--------|-------|\n"

        for article_name, analysis in sorted_articles:
            report += f"| {article_name:30s} | {analysis['company_mentions']:6d} | {analysis['number_mentions']:6d} | {analysis['specificity_score']:6.1f} |\n"

        # 総合評価
        report += "\n## 🎯 総合評価\n\n"

        best_article = sorted_articles[0]
        worst_article = sorted_articles[-1]

        report += f"### 🥇 最高品質: {best_article[0]}\n\n"
        report += f"- **総合スコア**: {best_article[1]['quality_score']:.1f}/100\n"
        report += f"- **AI臭度**: {best_article[1]['ai_smell_score']:.1f}/100\n"
        report += f"- **具体性**: {best_article[1]['specificity_score']:.1f}/100\n"
        report += f"- **文字数**: {best_article[1]['stats']['total_chars']}字\n"
        report += f"- **特徴**: "

        if best_article[1]['specificity_score'] > 80:
            report += "具体性が高い、"
        if best_article[1]['ai_smell_score'] > 90:
            report += "AI臭がない、"
        if best_article[1]['heading_ratio'] > 5:
            report += "見出しが適切、"
        report += "\n\n"

        # 推奨用途
        report += "## 💡 推奨事項\n\n"
        report += "### セクショナル生成パイプラインの活用\n\n"

        if 'sectional_article' in results:
            sectional_score = results['sectional_article']['quality_score']
            avg_existing_score = sum(results[k]['quality_score'] for k in results if k != 'sectional_article') / max(1, len(results) - 1)

            if sectional_score >= avg_existing_score:
                report += f"✅ **セクショナル生成記事は既存記事と同等かそれ以上の品質を達成**\n\n"
                report += f"- セクショナル生成スコア: {sectional_score:.1f}\n"
                report += f"- 既存記事平均スコア: {avg_existing_score:.1f}\n"
                report += f"- 実現可能: gemma-3-27b-it でも高品質記事を自動生成できる\n\n"
                report += "**推奨**: セクショナル生成パイプラインを本運用化\n"
            else:
                report += f"⚠️ **セクショナル生成記事は既存記事より品質が劣る**\n\n"
                report += f"- セクショナル生成スコア: {sectional_score:.1f}\n"
                report += f"- 既存記事平均スコア: {avg_existing_score:.1f}\n"
                report += f"- 改善点: プロンプト最適化、セクション追加、モデルのファインチューニング\n\n"

        report += "\n---\n\n"
        report += "**分析日時**: " + __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"📄 レポート保存: {output_file}")

        return report


def main():
    # セクショナル生成記事を読み込み
    sectional_article_path = Path('/home/sol/ai-blog-system/output/sectional_articles/article_20260302_161144.md')

    if not sectional_article_path.exists():
        print("❌ セクショナル生成記事が見つかりません")
        return

    with open(sectional_article_path, 'r', encoding='utf-8') as f:
        sectional_content = f.read()

    # 既存の AI メディア記事をサンプル取得（最新5件）
    posts_dir = Path('/home/sol/ai-blog-system/_posts')
    existing_articles = {}

    if posts_dir.exists():
        markdown_files = sorted(posts_dir.glob('*.md'), reverse=True)[:5]

        for md_file in markdown_files:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # front matter を除去
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        content = parts[2]
                existing_articles[md_file.stem] = content

    # 比較分析
    articles_to_compare = {
        'sectional_article': sectional_content,
        **{f'existing_{i}': content for i, content in enumerate(existing_articles.values(), 1)}
    }

    comparer = ArticleQualityComparer()
    results = comparer.compare_articles(articles_to_compare)

    # レポート生成
    output_dir = Path('output/comparison_reports')
    output_dir.mkdir(parents=True, exist_ok=True)

    report = comparer.generate_comparison_report(
        results,
        output_file=str(output_dir / f"comparison_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
    )

    # コンソール出力
    print("\n" + "=" * 70)
    print("📊 セクショナル生成記事 vs 既存 AI メディア記事 — 品質比較")
    print("=" * 70)
    print(report)


if __name__ == '__main__':
    main()
