#!/usr/bin/env python3
"""
テーマ: AIエージェント × 製造業DX
セクショナル生成で同じテーマを再生成し、既存記事と比較検証
"""

import requests
import time
from pathlib import Path
from datetime import datetime
import os


class ComparisonSectionalGenerator:
    """AIエージェント × 製造業DX をセクショナル生成"""

    def __init__(self, model: str = "gemma-3-27b-it"):
        self.api_key = os.environ.get('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("API key not found")

        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.headers = {
            'Content-Type': 'application/json',
            'X-goog-api-key': self.api_key
        }
        self.sections = {}
        self.stats = {}

    def _call_api(self, prompt: str) -> dict:
        """API呼び出し"""
        url = f"{self.base_url}/{self.model}:generateContent"
        request_data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        try:
            start_time = time.time()
            response = requests.post(url, headers=self.headers, json=request_data, timeout=60)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                if 'candidates' in data and len(data['candidates']) > 0:
                    content = data['candidates'][0]['content']['parts'][0]['text']
                    return {
                        'success': True,
                        'content': content,
                        'time': elapsed,
                        'chars': len(content)
                    }
            return {'success': False, 'error': f'HTTP {response.status_code}', 'time': 0}
        except Exception as e:
            return {'success': False, 'error': str(e), 'time': 0}

    def generate_section_1(self) -> bool:
        """セクション1: AIエージェントとは（定義と製造業への応用）"""
        prompt = """【セクション1: AIエージェントとは】

「AIエージェント」をテーマに、製造業DXの背景と定義について説明してください。

要件：
- 400-500文字
- AIエージェントの基本定義と製造業での応用可能性
- Gartnerの「2026年までに企業アプリの40%がAIエージェント対応」という予測を引用可能
- 具体的な製造現場での活用例（異常検知、在庫管理等）
- AI臭なし、自然な日本語
- 架空の数値やベンチマークは使用しない

【出力】
"""

        print("\n🔄 セクション1: AIエージェントとは を生成中...", end='', flush=True)
        result = self._call_api(prompt)

        if result['success']:
            self.sections['section_1'] = result['content']
            self.stats['section_1_time'] = result['time']
            print(f" ✅ {result['time']:.1f}秒, {result['chars']}字")
            return True
        else:
            print(f" ❌ {result['error']}")
            return False

    def generate_section_2(self) -> bool:
        """セクション2: 技術仕様とアーキテクチャ"""
        if 'section_1' not in self.sections:
            return False

        prompt = f"""【セクション2: 技術仕様とアーキテクチャ】

前のセクション:
{self.sections['section_1']}

---

上記のAIエージェントの技術的な仕組みについて、詳しく説明してください。

要件：
- 400-500文字
- LLMの役割（脳としての機能）
- 知覚・思考・行動の3つの要素
- 実在するLLMモデル名を引用する場合は正確な名称のみ（例: OpenAI GPT-4o、Google Gemini）
- ベンチマーク数値は、公開されているもののみ（GPT-4o: MMLU 88.7等）
- GPU性能の説明が必要な場合は実在するスペック（NVIDIA B200等）のみ
- セクション1の内容と矛盾しない
- 架空の数値は一切使用しない

【出力】
"""

        print("🔄 セクション2: 技術仕様とアーキテクチャ を生成中...", end='', flush=True)
        result = self._call_api(prompt)

        if result['success']:
            self.sections['section_2'] = result['content']
            self.stats['section_2_time'] = result['time']
            print(f" ✅ {result['time']:.1f}秒, {result['chars']}字")
            return True
        else:
            print(f" ❌ {result['error']}")
            return False

    def generate_section_3(self) -> bool:
        """セクション3: 実装事例と応用分野"""
        if not all(k in self.sections for k in ['section_1', 'section_2']):
            return False

        context = f"\n\n".join([
            f"セクション1: {self.sections['section_1']}",
            f"セクション2: {self.sections['section_2']}"
        ])

        prompt = f"""【セクション3: 実装事例と応用分野】

前のセクション:
{context}

---

上記の技術を実際に製造業に適用する場合の実装事例と応用分野について説明してください。

要件：
- 400-500文字
- 具体的な実装例：在庫管理の自動化、品質検査、予知保全等
- 複数の製造業分野での応用可能性
- 前のセクションとの整合性を保つ
- 架空の企業や製品名は使用しない
- 実際に存在する企業/技術のみ言及可能

【出力】
"""

        print("🔄 セクション3: 実装事例と応用分野 を生成中...", end='', flush=True)
        result = self._call_api(prompt)

        if result['success']:
            self.sections['section_3'] = result['content']
            self.stats['section_3_time'] = result['time']
            print(f" ✅ {result['time']:.1f}秒, {result['chars']}字")
            return True
        else:
            print(f" ❌ {result['error']}")
            return False

    def generate_section_4(self) -> bool:
        """セクション4: 市場規模、競争構図、投資動向"""
        if not all(k in self.sections for k in ['section_1', 'section_2', 'section_3']):
            return False

        context = "\n\n".join([
            f"S1: {self.sections['section_1']}",
            f"S2: {self.sections['section_2']}",
            f"S3: {self.sections['section_3']}"
        ])

        prompt = f"""【セクション4: 市場規模、競争構図、投資動向】

前のセクション（要約）:
{context[:800]}...

---

AIエージェントと製造業DXに関連する市場規模、企業の競争状況、投資動向について説明してください。

要件：
- 400-500文字
- 市場規模推定（可能であれば根拠のある数値）
- 競争企業の言及（OpenAI、Google、Meta、Anthropic等の実在企業のみ）
- API価格比較（公開されているもののみ）
- 投資動向（実在する投資ファンド、VC等）
- 架空の数値・企業名は一切使用しない
- 全セクションと矛盾しない

【出力】
"""

        print("🔄 セクション4: 市場規模・競争構図 を生成中...", end='', flush=True)
        result = self._call_api(prompt)

        if result['success']:
            self.sections['section_4'] = result['content']
            self.stats['section_4_time'] = result['time']
            print(f" ✅ {result['time']:.1f}秒, {result['chars']}字")
            return True
        else:
            print(f" ❌ {result['error']}")
            return False

    def generate_section_5(self) -> bool:
        """セクション5: 規制動向、倫理的課題、今後の展開"""
        if not all(k in self.sections for k in ['section_1', 'section_2', 'section_3', 'section_4']):
            return False

        context = "\n\n".join([
            f"S1: {self.sections['section_1']}",
            f"S2: {self.sections['section_2']}",
            f"S3: {self.sections['section_3']}",
            f"S4: {self.sections['section_4']}"
        ])

        prompt = f"""【セクション5: 規制動向、倫理的課題、今後の展開】

前のセクション（要約）:
{context[:800]}...

---

AIエージェント導入における規制動向、倫理的課題、および今後の展開について説明してください。

要件：
- 400-500文字
- 規制：EU AI Act（正式名称、施行予定日：2026年8月）、日本のAIガイドラインについて言及
- 倫理的課題：プライバシー、バイアス、差別、責任についての記述
- セキュリティ、コンプライアンスへの配慮
- 今後の展開：製造業でのAIエージェント導入の見通し
- 架空の規制名や日付は使用しない（正確な情報のみ）
- 全セクション間で矛盾なし

【出力】
"""

        print("🔄 セクション5: 規制動向・倫理的課題 を生成中...", end='', flush=True)
        result = self._call_api(prompt)

        if result['success']:
            self.sections['section_5'] = result['content']
            self.stats['section_5_time'] = result['time']
            print(f" ✅ {result['time']:.1f}秒, {result['chars']}字")
            return True
        else:
            print(f" ❌ {result['error']}")
            return False

    def assemble_article(self) -> str:
        """全セクションを結合"""
        if not all(k in self.sections for k in ['section_1', 'section_2', 'section_3', 'section_4', 'section_5']):
            return ""

        article = f"""# AIエージェントで製造業DXはどこまで進化するのか

## AIエージェントとは

{self.sections['section_1']}

## 技術仕様とアーキテクチャ

{self.sections['section_2']}

## 実装事例と応用分野

{self.sections['section_3']}

## 市場規模、競争構図、投資動向

{self.sections['section_4']}

## 規制動向、倫理的課題、今後の展開

{self.sections['section_5']}
"""

        # 統計更新
        self.stats['total_chars'] = sum(len(self.sections[k]) for k in self.sections)
        self.stats['total_time'] = sum(self.stats.get(f'{k}_time', 0) for k in self.sections)

        return article

    def generate_full_article(self) -> str:
        """全セクション生成して記事完成"""
        print("\n" + "=" * 70)
        print("🧪 セクショナル生成: AIエージェント × 製造業DX")
        print("=" * 70)
        print(f"\n📅 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🤖 モデル: {self.model}\n")

        sections = [
            self.generate_section_1,
            self.generate_section_2,
            self.generate_section_3,
            self.generate_section_4,
            self.generate_section_5,
        ]

        for section_func in sections:
            if not section_func():
                return None
            time.sleep(1)

        article = self.assemble_article()

        print("\n" + "=" * 70)
        print("✅ 生成完了")
        print("=" * 70)
        print(f"\n📝 総文字数: {self.stats['total_chars']}字")
        print(f"⏱️ 総生成時間: {self.stats['total_time']:.1f}秒")

        return article


def main():
    generator = ComparisonSectionalGenerator(model="gemma-3-27b-it")

    article = generator.generate_full_article()

    if article:
        # 記事を保存
        output_dir = Path('output/comparison_sectional')
        output_dir.mkdir(parents=True, exist_ok=True)

        article_file = output_dir / f"comparison_sectional_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(article_file, 'w', encoding='utf-8') as f:
            f.write(article)

        print(f"\n📄 記事保存: {article_file}")

        # 統計レポート
        stats_file = output_dir / f"stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        import json
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(generator.stats, f, indent=2, ensure_ascii=False)

        print(f"📊 統計保存: {stats_file}")

    else:
        print("\n❌ 生成失敗")


if __name__ == '__main__':
    main()
