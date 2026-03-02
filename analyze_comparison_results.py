#!/usr/bin/env python3
"""
比較レポートから記事を抽出して品質分析を実施
"""

import re
import json
from pathlib import Path
from collections import Counter
from analyze_articles_quality import ArticleQualityAnalyzer

def extract_articles_from_report(report_path):
    """Markdown レポートから記事を抽出"""
    with open(report_path, 'r', encoding='utf-8') as f:
        content = f.read()

    articles = {}

    # #### モデル名 の直後から次のセクションまでを抽出
    pattern = r'#### (gemini[\w\-\.]+|gemma[\w\-\.]+)\n\n\*\*生成時間\*\*: .*?\n\*\*推定トークン\*\*: .*?\n\n```\n(.*?)\n```'
    matches = re.finditer(pattern, content, re.DOTALL)

    for match in matches:
        model_name = match.group(1)
        article_content = match.group(2)
        articles[model_name] = article_content

    return articles

def main():
    report_path = Path('output/model_comparison/comparison_report_20260302_155937.md')

    if not report_path.exists():
        print(f"❌ レポートファイルが見つかりません: {report_path}")
        return

    print("\n" + "=" * 70)
    print("📊 Gemini モデル比較 — 詳細品質分析")
    print("=" * 70)

    # 記事抽出
    articles = extract_articles_from_report(report_path)

    if not articles:
        print("❌ レポートから記事を抽出できませんでした")
        return

    print(f"\n✅ {len(articles)}個の記事を抽出しました\n")

    # 品質分析
    analyzer = ArticleQualityAnalyzer()
    results = {}

    for model_name, content in articles.items():
        analysis = analyzer.analyze_article(content)
        results[model_name] = analysis

    # === 統計情報 ===
    print("\n### 📈 テキスト統計\n")
    print("| モデル | 文字数 | 単語数 | 文数 | 段落数 | 平均単語長 |")
    print("|--------|--------|--------|--------|--------|-----------|")
    for model, analysis in sorted(results.items()):
        if analysis:
            stats = analysis['stats']
            print(f"| {model:25s} | {stats['total_chars']:6d} | {stats['total_words']:6d} | {stats['sentences']:6d} | {stats['paragraphs']:6d} | {stats['avg_word_length']:6.2f} |")

    # === スコア比較 ===
    print("\n### 🎯 品質スコア（100点満点）\n")
    print("| モデル | 総合点 | AI臭スコア | 具体性 | 敬語度 |")
    print("|--------|--------|-----------|--------|--------|")
    for model, analysis in sorted(results.items(), key=lambda x: x[1]['quality_score'] if x[1] else 0, reverse=True):
        if analysis:
            print(f"| {model:25s} | {analysis['quality_score']:6.1f} | {analysis['ai_smell_score']:6.1f} | {analysis['specificity_score']:6.1f} | {analysis['formality_score']:6.1f} |")

    # === AI臭詳細 ===
    print("\n### ⚠️ AI臭パターン検出\n")
    for model, analysis in sorted(results.items()):
        if analysis:
            if analysis['ai_smell_details']:
                print(f"**{model}** (AI臭スコア: {analysis['ai_smell_score']:.1f})")
                for pattern, count in sorted(analysis['ai_smell_details'].items(), key=lambda x: -x[1]):
                    print(f"  - {pattern}: {count}回")
            else:
                print(f"**{model}**: AI臭なし ✅")

    # === 企業・数字メンション ===
    print("\n### 📊 具体性分析\n")
    print("| モデル | 企業名 | 数字 | 具体性スコア |")
    print("|--------|--------|--------|-----------|")
    for model, analysis in sorted(results.items()):
        if analysis:
            print(f"| {model:25s} | {analysis['company_mentions']:6d} | {analysis['number_mentions']:6d} | {analysis['specificity_score']:6.1f} |")

    # === スタイル分析 ===
    print("\n### 🎨 文体分析\n")
    print("| モデル | 敬語数 | 会話的表現数 | 敬語度スコア |")
    print("|--------|--------|----------|-----------|")
    for model, analysis in sorted(results.items()):
        if analysis:
            print(f"| {model:25s} | {analysis['respectful_words']:6d} | {analysis['casual_words']:6d} | {analysis['formality_score']:6.1f}% |")

    # === 総合評価 ===
    print("\n### 📋 総合評価\n")
    sorted_models = sorted(results.items(), key=lambda x: x[1]['quality_score'] if x[1] else 0, reverse=True)

    for rank, (model, analysis) in enumerate(sorted_models, 1):
        if analysis:
            score = analysis['quality_score']

            # スコアに基づいた評価
            if score >= 80:
                rating = "⭐⭐⭐⭐⭐ 優秀"
            elif score >= 70:
                rating = "⭐⭐⭐⭐ 良好"
            elif score >= 60:
                rating = "⭐⭐⭐ 合格"
            elif score >= 50:
                rating = "⭐⭐ 要改善"
            else:
                rating = "⭐ 要大幅改善"

            print(f"{rank}. **{model}** — {rating}")
            print(f"   - 総合スコア: {score:.1f}/100")
            print(f"   - AI臭度: {100 - analysis['ai_smell_score']:.1f}% (低いほど良い)")
            print(f"   - 文字数: {analysis['stats']['total_chars']} 文字")
            print(f"   - 具体性: {analysis['specificity_score']:.1f}/100\n")

    # === 推奨事項 ===
    print("\n### 💡 推奨事項\n")

    if sorted_models:
        best_model = sorted_models[0][0]
        worst_model = sorted_models[-1][0]

        best_score = sorted_models[0][1]['quality_score']
        worst_score = sorted_models[-1][1]['quality_score']

        print(f"**最高品質**: {best_model} ({best_score:.1f}/100)")
        print(f"  - 記事品質が最も高く、AI臭が少ない")
        print(f"  - note.com有料記事向けに推奨\n")

        if len(sorted_models) > 1:
            second_best = sorted_models[1][0]
            print(f"**次点**: {second_best}")
            print(f"  - バックアップまたは特定テーマの最適化用\n")

    # === 記事別詳細 ===
    print("\n### 📝 記事別の詳細情報\n")

    for model, analysis in sorted(results.items()):
        if analysis:
            print(f"#### {model}\n")
            print(f"- **テキスト統計**: {analysis['stats']['total_chars']} 文字、{analysis['stats']['sentences']} 文")
            print(f"- **専門用語数**: {analysis['company_mentions']} 社名、{analysis['number_mentions']} 件の数値")
            print(f"- **文体バランス**: 敬語 {analysis['respectful_words']} 箇所、会話的 {analysis['casual_words']} 箇所")

            if analysis['ai_smell_details']:
                print(f"- **AI臭パターン**: ", end='')
                patterns = ', '.join([f"{k}({v})" for k, v in analysis['ai_smell_details'].items()])
                print(patterns)
            else:
                print(f"- **AI臭パターン**: なし ✅")

            print()

if __name__ == '__main__':
    main()
