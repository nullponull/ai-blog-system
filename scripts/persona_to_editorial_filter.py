#!/usr/bin/env python3
"""
Persona to Editorial Filter Layer
Digital Twin SDK から長谷川ペルソナを抽出 → セクショナル生成用プロンプトに inject

統合フロー:
1. Digital Double SDK で長谷川ペルソナを抽出
2. ペルソナ情報を「編集方針」に変換
3. セクショナル生成プロンプトへ inject
4. 生成記事から個人情報をマスク
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, Optional, List, Tuple

# Digital Twin SDK の読み込み
try:
    sys.path.insert(0, os.path.join(os.path.expanduser('~'), 'digital-double'))
    from digital_double import DigitalDouble
    DD_AVAILABLE = True
except ImportError:
    DD_AVAILABLE = False

# Output Sanitizer
try:
    from output_sanitizer import OutputSanitizer
    SANITIZER = OutputSanitizer()
except ImportError:
    SANITIZER = None


class PersonaToEditorialFilter:
    """
    デジタルツインペルソナから編集方針を生成し、セクショナル生成に適用
    """

    def __init__(self, persona_source: str = "digital-double"):
        """
        初期化

        Args:
            persona_source: "digital-double" (SDK経由) | "config" (JSONファイル直読)
        """
        self.persona_source = persona_source
        self.persona_data = None
        self.editorial_guidelines = None
        self.loaded = False

    def load_persona_from_digital_double(self) -> Dict:
        """
        Digital Double SDK から長谷川ペルソナを抽出

        Returns:
            ペルソナ情報の辞書
        """
        if not DD_AVAILABLE:
            return None

        try:
            dd = DigitalDouble(mode='growth')

            # Platform: ai_media, Content Type: technical
            persona_prompt = dd.build_prompt(
                platform='ai_media',
                content_type='technical',
                topic_keywords=['AI', 'テクノロジー', 'DX', '企業経営'],
                max_tokens=4000
            )

            # ペルソナデータの抽出
            persona_dict = {
                'base_prompt': persona_prompt,
                'platform': 'ai_media',
                'content_type': 'technical',
                'tone': 'professional_but_accessible',
                'target_audience': 'executives_and_engineers',
                'expertise_areas': ['AI', 'DX', 'Enterprise Technology', 'Business Strategy'],
                'writing_style': 'experience_based',
                'avoid_patterns': [
                    'いかがでしたか',
                    'さあ始めましょう',
                    'つまり',
                    'まずは',
                    '権威的なアピール',
                    '上から目線',
                ],
                'must_include': [
                    '体験ベースの語り',
                    '複数視点の検討',
                    '読者への問いかけ',
                    'ビジネスインパクト',
                ],
            }

            # Sanitizer で非公開情報を秘匿化
            if SANITIZER and persona_prompt:
                sanitized_prompt = SANITIZER.sanitize(persona_prompt, context='public')
                persona_dict['base_prompt'] = sanitized_prompt

            return persona_dict

        except Exception as e:
            print(f"[Persona] Digital Double SDK load failed: {e}", file=sys.stderr)
            return None

    def load_persona_from_config(self) -> Dict:
        """
        既存の設定ファイル（x_persona_config.json等）からペルソナを読み込み

        Returns:
            ペルソナ情報の辞書
        """
        config_paths = [
            Path.home() / 'digital-double' / 'config' / 'x_persona_config.json',
            Path.home() / 'digital-double' / 'config' / 'persona_database_v2.json',
        ]

        for config_path in config_paths:
            if config_path.exists():
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)

                    # 長谷川のセクションを抽出（可能なら）
                    if isinstance(config, dict):
                        # 複数形式に対応
                        if 'personas' in config:
                            for persona in config['personas'].values():
                                if '長谷川' in str(persona) or 'hasegawa' in str(persona).lower():
                                    return self._normalize_persona(persona)
                        elif 'hasegawa' in config or '長谷川' in config:
                            return self._normalize_persona(config.get('hasegawa') or config.get('長谷川'))

                    # フォールバック: 最初のペルソナを使用
                    return self._normalize_persona(config)

                except Exception as e:
                    print(f"[Persona] Config load failed ({config_path}): {e}", file=sys.stderr)
                    continue

        return None

    def _normalize_persona(self, raw_persona: dict) -> Dict:
        """
        様々な形式のペルソナデータを統一形式に正規化
        """
        normalized = {
            'tone': 'professional_but_accessible',
            'target_audience': 'executives_and_engineers',
            'writing_style': 'experience_based',
            'avoid_patterns': [],
            'must_include': [],
        }

        # 既存フィールドを取り込み
        if isinstance(raw_persona, dict):
            if 'expertise' in raw_persona or 'expertise_areas' in raw_persona:
                normalized['expertise_areas'] = raw_persona.get('expertise_areas') or \
                                               list(raw_persona.get('expertise', {}).keys())
            if 'tone' in raw_persona:
                normalized['tone'] = raw_persona['tone']
            if 'writing_style' in raw_persona:
                normalized['writing_style'] = raw_persona['writing_style']

        return normalized

    def load(self) -> bool:
        """
        ペルソナを読み込む（優先順位: Digital Double > Config）

        Returns:
            成功時True
        """
        # Digital Double SDK から優先的に読み込み
        if self.persona_source == "digital-double":
            self.persona_data = self.load_persona_from_digital_double()

        # フォールバック: Config から読み込み
        if not self.persona_data:
            self.persona_data = self.load_persona_from_config()

        if self.persona_data:
            self.loaded = True
            print(f"[Persona] Loaded from {self.persona_source}", file=sys.stderr)
            return True

        print("[Persona] Failed to load, using fallback defaults", file=sys.stderr)
        self.persona_data = {
            'tone': 'professional_but_accessible',
            'target_audience': 'executives_and_engineers',
            'expertise_areas': ['AI', 'DX', 'Enterprise Technology'],
            'writing_style': 'experience_based',
        }
        return False

    def generate_section_guidelines(self, section_num: int) -> str:
        """
        セクショナル生成用のセクション別ガイドラインを生成

        Args:
            section_num: セクション番号 (1-5)

        Returns:
            プロンプト注入用のガイドラインテキスト
        """
        if not self.persona_data:
            self.load()

        tone = self.persona_data.get('tone', 'professional_but_accessible')
        expertise = ', '.join(self.persona_data.get('expertise_areas', ['AI']))
        avoid = '; '.join(self.persona_data.get('avoid_patterns', []))
        must_include = '; '.join(self.persona_data.get('must_include', []))

        guidelines = f"""
【編集部ペルソナ】
- トーン: {tone}（やや丁寧だが堅すぎない、技術者として自然な語り口）
- 対象読者: {self.persona_data.get('target_audience', 'executives_and_engineers')}
- 専門領域: {expertise}
- 執筆スタイル: {self.persona_data.get('writing_style', 'experience_based')}（体験ベースの語り）

【必ず含める要素】
{must_include or '- 体験ベースの具体例; - 複数視点の検討; - 読者への問いかけ'}

【避ける表現・パターン】
{avoid or '- いかがでしたか; - さあ始めましょう; - 権威的なアピール'}

【セクション{section_num}の役割】
"""

        section_roles = {
            1: "テーマの背景と最初の印象を率直に述べ、読者の関心を引く",
            2: "核心的な技術・ビジネス詳細を専門家の視点で解説",
            3: "実装例・応用分野を具体的に示す",
            4: "市場・投資への影響を客観的に分析",
            5: "今後の展望を予測し、読者への問いかけで締める",
        }

        guidelines += section_roles.get(section_num, "セクションの内容を深掘りする")

        return guidelines

    def apply_to_prompt(self, base_prompt: str, section_num: int = 0) -> str:
        """
        ペルソナガイドラインをベースプロンプトに inject

        Args:
            base_prompt: セクショナル生成のベースプロンプト
            section_num: セクション番号（0 = 全体）

        Returns:
            ペルソナを適用したプロンプト
        """
        if not self.persona_data:
            self.load()

        guidelines = self.generate_section_guidelines(section_num) if section_num > 0 else \
                    f"【編集部ペルソナ】{self.persona_data.get('tone', '')}"

        # プロンプトの最後に編集方針を追加
        enhanced_prompt = f"""{base_prompt}

{guidelines}"""

        return enhanced_prompt

    def mask_personal_info(self, article_text: str) -> str:
        """
        記事内の個人名・会社名をマスク（匿名化）

        Args:
            article_text: 生成記事のテキスト

        Returns:
            匿名化済みの記事テキスト
        """
        masked = article_text

        # 個人名のマスク
        personal_masks = {
            r'長谷川': 'AI編集部',
            r'nullpodesu': '編集チーム',
            r'ヌルポデス': '編集チーム',
        }

        for pattern, replacement in personal_masks.items():
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)

        # 会社名のマスク（不自然な固有企業は「某企業」に）
        company_masks = {
            r'Anthropic': '某大規模言語モデル企業',
            r'(?<!AWS )OpenAI': '某生成AI企業',  # AWS OpenAI を除外
        }

        for pattern, replacement in company_masks.items():
            masked = re.sub(pattern, replacement, masked, flags=re.IGNORECASE)

        # Sanitizer で追加的な秘匿化
        if SANITIZER:
            masked = SANITIZER.sanitize(masked, context='public')

        return masked

    def get_byline(self) -> Tuple[str, str]:
        """
        記事のByline（著者情報）を取得

        Returns:
            (著者名, 著者URL/SNS)
        """
        author = "AI編集部"
        author_url = ""  # note.com では表示されない可能性があるため空

        return author, author_url


# ===== ユーティリティ関数 =====

def load_persona_filter() -> PersonaToEditorialFilter:
    """
    ペルソナフィルターを初期化して返す
    """
    pf = PersonaToEditorialFilter(persona_source="digital-double")
    pf.load()
    return pf


if __name__ == '__main__':
    # テスト用
    pf = load_persona_filter()

    print("\n[Test] Persona loaded:")
    print(json.dumps(pf.persona_data, indent=2, ensure_ascii=False))

    print("\n[Test] Section guidelines:")
    for section in range(1, 6):
        print(f"\n--- Section {section} ---")
        print(pf.generate_section_guidelines(section))

    print("\n[Test] Masking example:")
    test_text = "長谷川とnullpodsuが Anthropic で記事を作成しました"
    masked = pf.mask_personal_info(test_text)
    print(f"Before: {test_text}")
    print(f"After:  {masked}")
