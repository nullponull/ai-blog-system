#!/usr/bin/env python3
"""
複数モデルの記事生成品質を比較するテストスクリプト

テスト対象モデル:
- gemini-2.5-flash (現在のデフォルト)
- gemini-2.0-flash (フォールバック)
- gemini-3.0-flash (新モデル)
- gemma-3-27b (OSS モデル)
"""

import requests
import json
import os
import time
from datetime import datetime
from pathlib import Path

class GeminiModelComparator:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get('GEMINI_API_KEY2') or os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("API key not found in environment")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.results = {}
        
        # テスト対象モデル
        self.models_to_test = [
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-3.0-flash",  # 新モデル
            "gemma-3-27b",        # OSS モデル
        ]
    
    def check_available_models(self):
        """利用可能なモデルを確認"""
        print("\n🔍 利用可能なモデルを確認中...\n")
        headers = {'X-goog-api-key': self.api_key}
        
        try:
            response = requests.get(self.base_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                available = set()
                
                if 'models' in data:
                    for model in data['models']:
                        model_name = model.get('name', '').replace('models/', '')
                        available.add(model_name)
                
                print("✅ API から利用可能なモデル:")
                print("=" * 70)
                for model_name in sorted(available):
                    if any(x in model_name.lower() for x in ['gemini', 'gemma', 'flash']):
                        print(f"  ✓ {model_name}")
                
                return available
            else:
                print(f"⚠️ API エラー: {response.status_code}")
                return set()
        except Exception as e:
            print(f"⚠️ エラー: {e}")
            return set()
    
    def generate_article_with_model(self, model_name, prompt):
        """指定モデルで記事を生成"""
        url = f"{self.base_url}/{model_name}:generateContent"
        headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': self.api_key
        }
        
        data = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        
        try:
            print(f"\n  ⏳ {model_name} でリクエスト送信中...")
            start_time = time.time()
            
            response = requests.post(url, headers=headers, json=data, timeout=60)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 429:
                return {
                    'success': False,
                    'error': 'QUOTA_LIMIT',
                    'time': elapsed_time,
                    'message': f"クォータ制限に達しました"
                }
            elif response.status_code != 200:
                return {
                    'success': False,
                    'error': f'HTTP_{response.status_code}',
                    'time': elapsed_time,
                    'message': response.text[:200]
                }
            
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                content = result['candidates'][0]['content']['parts'][0]['text']
                
                return {
                    'success': True,
                    'content': content,
                    'time': elapsed_time,
                    'tokens_used': len(content.split())  # 粗い推定
                }
            else:
                return {
                    'success': False,
                    'error': 'NO_CONTENT',
                    'time': elapsed_time
                }
        
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'TIMEOUT',
                'time': time.time() - start_time
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(type(e).__name__),
                'time': time.time() - start_time,
                'message': str(e)[:100]
            }
    
    def run_comparison(self):
        """複数モデルで比較テストを実行"""
        print("\n" + "=" * 70)
        print("🧪 Gemini モデル比較テスト")
        print("=" * 70)
        
        # 利用可能モデルを確認
        available_models = self.check_available_models()
        
        # テストプロンプト
        today = datetime.now().strftime('%Y年%m月%d日')
        prompt = f"""今日({today})のAI業界で重要なニュースを1つ想定して、技術者向けのニュース記事を日本語で作成してください。

要件：
- 具体的で詳細な内容
- 企体動向、研究成果、新サービス、規制動向などから選択
- 自然な日本語表現（AI特有の機械的表現は避ける）
- 800-1200文字程度

構成：
## {today}のAI業界ニュース

### [企業名と発表内容]
[詳細内容]

### 背景と影響
[影響分析]

### 今後の展開
[予測]"""
        
        print(f"\n📝 テストプロンプト: {len(prompt)} 文字")
        print("\n🧪 テスト実行中 (各モデル1回ずつ)\n")
        
        results = {}
        for model in self.models_to_test:
            # 利用可能性チェック
            if model not in available_models:
                print(f"⏭️  {model:30s} - 利用不可")
                results[model] = {
                    'available': False,
                    'reason': 'モデル not found in API'
                }
                continue
            
            print(f"🔄 {model:30s} ", end='', flush=True)
            result = self.generate_article_with_model(model, prompt)
            
            if result['success']:
                print(f"✅ {result['time']:.1f}秒, {result['tokens_used']} tokens")
                results[model] = result
            else:
                error = result.get('error', 'Unknown')
                print(f"❌ {error} ({result['time']:.1f}秒)")
                results[model] = result
            
            # API レート制限を考慮
            time.sleep(2)
        
        self.results = results
        return results
    
    def generate_comparison_report(self, output_dir='output/model_comparison'):
        """比較レポートを生成"""
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = Path(output_dir) / f'comparison_report_{timestamp}.md'
        
        report = f"""# Gemini モデル比較テスト結果
## テスト日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### テスト実施モデル

| モデル | 利用可能 | 実行時間 | ステータス | 備考 |
|--------|---------|---------|-----------|------|
"""
        
        for model, result in self.results.items():
            if 'available' in result and not result['available']:
                report += f"| {model} | ❌ | - | 利用不可 | {result.get('reason', '')} |\n"
            elif result.get('success'):
                tokens = result.get('tokens_used', 'N/A')
                report += f"| {model} | ✅ | {result['time']:.1f}s | 成功 | {tokens} tokens |\n"
            else:
                error = result.get('error', 'Unknown')
                report += f"| {model} | ✅ | {result.get('time', 'N/A'):.1f}s | ❌ {error} | {result.get('message', '')} |\n"
        
        report += "\n### 生成された記事\n\n"
        
        # 成功したモデルの記事を記載
        success_models = [m for m, r in self.results.items() if r.get('success')]
        
        for model in success_models:
            result = self.results[model]
            report += f"\n#### {model}\n\n"
            report += f"**生成時間**: {result['time']:.1f}秒\n"
            report += f"**推定トークン**: {result.get('tokens_used', 'N/A')}\n\n"
            report += f"```\n{result['content']}\n```\n\n"
        
        report += "\n### 分析\n\n"
        report += "#### 成功したモデル\n"
        for model in success_models:
            report += f"- ✅ {model}\n"
        
        failed_models = [m for m, r in self.results.items() if not r.get('success') and r.get('available', True)]
        if failed_models:
            report += "\n#### 失敗したモデル\n"
            for model in failed_models:
                error = self.results[model].get('error', 'Unknown')
                report += f"- ❌ {model}: {error}\n"
        
        unavailable = [m for m, r in self.results.items() if 'available' in r and not r['available']]
        if unavailable:
            report += "\n#### 利用不可なモデル\n"
            for model in unavailable:
                report += f"- ⏭️ {model}\n"
        
        # レポートを保存
        report_file.write_text(report, encoding='utf-8')
        print(f"\n📄 レポート保存: {report_file}")
        
        return report_file


def main():
    try:
        comparator = GeminiModelComparator()
        comparator.run_comparison()
        report_file = comparator.generate_comparison_report()
        
        print("\n" + "=" * 70)
        print("✅ テスト完了")
        print(f"📄 詳細レポート: {report_file}")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        exit(1)


if __name__ == '__main__':
    main()
