#!/usr/bin/env python3
"""
複数モデルで生成された記事の品質・スタイルを比較分析
"""

import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter

class ArticleQualityAnalyzer:
    def __init__(self):
        self.ai_smell_patterns = {
            'いかがでしたか': r'いかがでしたか|いかがでしょう',
            'さあ始めましょう': r'さあ始めましょう|さっそく始めましょう',
            '本当の価値': r'本当の価値|真の価値',
            '間違いなく': r'間違いなく|確実に|必ず',
            '素晴らしい': r'素晴らしい|素敵な|素晴らしさ',
            'ぜひ': r'\bぜひ\b',
            'つまり': r'\bつまり\b|\bすなわち\b',
            'まずは': r'まずは|まず|最初は',
        }
    
    def analyze_article(self, content):
        """記事の品質スコアを計算"""
        if not content:
            return None
        
        # テキスト統計
        lines = content.split('\n')
        words = content.split()
        
        stats = {
            'total_chars': len(content),
            'total_words': len(words),
            'sentences': len(re.split(r'[。！？]', content)),
            'paragraphs': len([l for l in lines if l.strip()]),
            'avg_word_length': sum(len(w) for w in words) / len(words) if words else 0,
        }
        
        # AI臭検出
        ai_smell_score = 0
        ai_smell_details = {}
        
        for pattern_name, pattern in self.ai_smell_patterns.items():
            matches = len(re.findall(pattern, content))
            if matches > 0:
                ai_smell_details[pattern_name] = matches
                ai_smell_score += matches * 3  # 各マッチに3点減点
        
        # 具体性スコア（企業名、数字の出現）
        company_matches = len(re.findall(r'[A-Z][a-z]+|[ァ-ヶー]+(?:会社|Inc|Ltd|Corp)', content))
        number_matches = len(re.findall(r'\d+(?:%|万|億|年|月|日|時間|分|秒)?', content))
        specificity_score = min(100, (company_matches + number_matches) * 5)
        
        # 文体分析
        respectful_words = len(re.findall(r'させていただ|お力添え|恐れ入り|失礼', content))
        casual_words = len(re.findall(r'だから|だって|なんて|マジで|ヤバい', content))
        
        # 総合スコア（100点満点）
        quality_score = 100
        quality_score -= ai_smell_score  # AI臭減点
        quality_score -= abs(stats['avg_word_length'] - 5) * 2  # 単語長の最適性
        quality_score = max(0, quality_score)
        
        return {
            'stats': stats,
            'quality_score': quality_score,
            'ai_smell_score': 100 - ai_smell_score,  # 低いほど悪い
            'ai_smell_details': ai_smell_details,
            'specificity_score': specificity_score,
            'company_mentions': company_matches,
            'number_mentions': number_matches,
            'respectful_words': respectful_words,
            'casual_words': casual_words,
            'formality_score': 100 * respectful_words / max(1, respectful_words + casual_words),
        }
    
    def compare_articles(self, articles_dict):
        """複数記事を比較分析"""
        print("\n" + "=" * 70)
        print("📊 記事品質分析")
        print("=" * 70)
        
        results = {}
        for model_name, content in articles_dict.items():
            if content:
                analysis = self.analyze_article(content)
                results[model_name] = analysis
        
        # 比較テーブル
        print("\n### 統計情報\n")
        print("| モデル | 文字数 | 単語数 | 文数 | 平均単語長 |")
        print("|--------|--------|--------|--------|-----------|")
        for model, analysis in results.items():
            if analysis:
                stats = analysis['stats']
                print(f"| {model:20s} | {stats['total_chars']:6d} | {stats['total_words']:6d} | {stats['sentences']:6d} | {stats['avg_word_length']:6.2f} |")
        
        # スコア比較
        print("\n### 品質スコア\n")
        print("| モデル | 総合点 | AI臭 | 具体性 | 敬語度 |")
        print("|--------|--------|--------|--------|--------|")
        for model, analysis in sorted(results.items(), key=lambda x: x[1]['quality_score'] if x[1] else 0, reverse=True):
            if analysis:
                print(f"| {model:20s} | {analysis['quality_score']:6.1f} | {analysis['ai_smell_score']:6.1f} | {analysis['specificity_score']:6.1f} | {analysis['formality_score']:6.1f} |")
        
        # AI臭詳細
        print("\n### AI臭パターン検出\n")
        for model, analysis in results.items():
            if analysis and analysis['ai_smell_details']:
                print(f"**{model}**:")
                for pattern, count in analysis['ai_smell_details'].items():
                    print(f"  - {pattern}: {count}回")
        
        return results


def main():
    # テスト用にダミーデータを使用（実際の実行時は compare_models.py の結果を使用）
    print("\n📊 記事品質分析スクリプト作成完了")
    print("\nこのスクリプトは compare_models.py の結果を分析します。")
    print("\n使用方法:")
    print("  1. compare_models.py を実行して記事を生成")
    print("  2. 出力ディレクトリから記事を抽出")
    print("  3. analyze_articles_quality.py で分析\n")


if __name__ == '__main__':
    main()
