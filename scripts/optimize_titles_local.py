#!/usr/bin/env python3
"""
optimize_titles_local.py - タイトルをローカルルールベースで45-58文字に最適化

Gemini APIを使わず、カテゴリ・タグ・本文からルールベースでタイトルを拡張する。
- 引数なし: dry run (プレビューのみ)
- --fix: 実際にファイルを修正
- --limit=N: 先頭N件のみ処理
"""

from __future__ import annotations

import random
import re
import sys
from collections import Counter
from pathlib import Path

POSTS_DIR = Path("/home/sol/ai-blog-system/_posts")
MIN_TITLE_LEN = 40
TARGET_MIN = 45
TARGET_MAX = 58
YEAR = "2026年"

# ── カテゴリ別の接尾辞パターン ──────────────────────────────────

SUFFIXES = {
    "AI最新ニュース": [
        "｜最新動向と今後の展望",
        "｜注目ポイントと業界への影響",
        "｜最新トレンドを徹底分析",
        "｜知っておくべき最新情報まとめ",
        "｜業界が注目する理由とは",
        "｜今後の展開と注目ポイント",
        "｜最前線レポートと今後の見通し",
    ],
    "AI技術ガイド": [
        "｜企業導入のポイントを徹底解説",
        "｜仕組みと活用法を完全ガイド",
        "｜技術的背景と実践的な活用法",
        "｜基礎から応用まで徹底解説",
        "｜導入前に知るべき要点まとめ",
        "｜エンジニア視点で読み解く要点",
        "｜技術進化がもたらすビジネス変革",
    ],
    "導入事例": [
        "｜具体的な数値効果と成功のカギ",
        "｜現場の声と導入プロセスを紹介",
        "｜ROI改善につながった施策とは",
        "｜導入から成果までの実践記録",
        "｜成功企業に学ぶ導入のコツ",
        "｜効果測定と運用の実際を解説",
    ],
    "業界別AI活用": [
        "｜業界別の活用事例と導入戦略",
        "｜各業界で進むAI活用の最前線",
        "｜業種特化型AI活用の成功パターン",
        "｜現場で成果を出すAI活用術",
        "｜業界変革を加速させるAI戦略",
        "｜競争優位を生むAI活用の実態",
    ],
    "AI導入戦略": [
        "｜戦略策定から実装まで完全ガイド",
        "｜成功する導入計画の立て方",
        "｜経営視点で考えるAI投資戦略",
        "｜失敗しない導入ロードマップとは",
        "｜意思決定者が押さえるべき要点",
        "｜段階的導入で成果を最大化する方法",
    ],
    "研究論文": [
        "｜最新研究が示す技術的ブレイクスルー",
        "｜論文から読み解く次世代AI技術",
        "｜研究最前線と実用化への道筋",
        "｜学術知見が示す今後の方向性",
        "｜注目論文のポイントをわかりやすく解説",
    ],
}

# カテゴリ不明時のフォールバック
FALLBACK_SUFFIXES = [
    "｜最新動向と今後の展望を解説",
    "｜知っておきたい重要ポイントまとめ",
    "｜注目すべき変化と対応策を紹介",
    "｜ビジネス視点で読み解く最新トレンド",
]

# ── 「とは」系キーワード拡張 ──────────────────────────────

TOHA_PATTERNS = [
    "とは？基礎知識と最新活用法を解説",
    "とは何か？仕組みと実践的な使い方",
    "とは｜初心者向けにわかりやすく解説",
]


def parse_front_matter(content: str) -> tuple[str, str, dict]:
    """Parse front matter and body."""
    match = re.match(r'^(---\n)(.*?)\n(---\n)(.*)', content, re.DOTALL)
    if not match:
        return '', content, {}
    fm_text = match.group(2)
    body = match.group(4)
    fm = {}
    for line in fm_text.split('\n'):
        if ':' in line:
            key = line.split(':', 1)[0].strip()
            value = line.split(':', 1)[1].strip()
            fm[key] = value
    return fm_text, body, fm


def extract_tags(tags_str: str) -> list[str]:
    """Extract tag list from front matter tags value."""
    tags_str = tags_str.strip().strip('[]')
    tags = []
    for t in re.findall(r'"([^"]+)"', tags_str):
        tags.append(t)
    if not tags:
        for t in tags_str.split(','):
            t = t.strip().strip('"').strip("'")
            if t:
                tags.append(t)
    return tags


def extract_body_keywords(body: str, title: str, n: int = 3) -> list[str]:
    """Extract distinctive keywords from body first ~500 chars."""
    # Get first meaningful paragraph
    text = ''
    for line in body.split('\n'):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('```') and not stripped.startswith('|'):
            clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', stripped)
            clean = re.sub(r'[*_`~{}]', '', clean)
            text += clean + ' '
            if len(text) > 500:
                break

    # Extract katakana/kanji compound words (3+ chars)
    candidates = re.findall(r'[\u30A0-\u30FF\u4E00-\u9FFF]{3,}', text)
    # Also extract English terms (3+ chars)
    eng = re.findall(r'[A-Za-z]{3,}', text)
    candidates.extend(eng)

    # Filter out words already in title
    title_lower = title.lower()
    keywords = []
    seen = set()
    for w in candidates:
        w_lower = w.lower()
        if w_lower not in title_lower and w_lower not in seen and len(w) >= 3:
            seen.add(w_lower)
            keywords.append(w)
            if len(keywords) >= n:
                break
    return keywords


def _pick_tag_keywords(tags: list[str], title: str, n: int = 2) -> list[str]:
    """Pick tag keywords not already in title."""
    title_lower = title.lower()
    result = []
    for t in tags:
        if t.lower() not in title_lower and len(t) >= 2:
            result.append(t)
            if len(result) >= n:
                break
    return result


# タイトルが短い場合に挿入する中間フレーズ（カテゴリ非依存）
MIDDLE_PHRASES = [
    "の最新動向と企業への影響",
    "が変えるビジネスの未来",
    "の全貌と実践的な活用法",
    "の注目ポイントと導入効果",
    "による業務効率化と競争力強化",
    "の技術革新がもたらす変化",
    "がもたらす産業構造の転換",
    "の進化と実用化への道筋",
]


def build_optimized_title(
    title: str,
    category: str,
    tags: list[str],
    body: str,
    used_suffixes: dict[str, int],
    is_duplicate: bool = False,
) -> str:
    """Build an optimized title using rules."""
    original = title

    # Already long enough
    if len(title) >= MIN_TITLE_LEN:
        return title

    # Step 1: Add year if not present
    has_year = any(y in title for y in [YEAR, "2025", "2024", "2023"])
    if not has_year and len(title) + 5 <= TARGET_MAX:
        title = YEAR + title

    # Step 2: For very short titles (<30 chars after year), expand with tag keywords + middle phrase
    if len(title) < 30:
        tag_kws = _pick_tag_keywords(tags, title, n=2)
        if tag_kws:
            kw_insert = "・".join(tag_kws)
            candidate = f"{title}（{kw_insert}）"
            if len(candidate) <= TARGET_MAX:
                title = candidate

    # Step 3: If still short, add a middle phrase to reach target
    if len(title) < TARGET_MIN:
        # Pick least-used middle phrase that fits
        scored_mid = []
        for p in MIDDLE_PHRASES:
            count = used_suffixes.get("mid:" + p, 0)
            scored_mid.append((count, random.random(), p))
        scored_mid.sort()

        base = title.rstrip('）')
        has_paren = '（' in title
        for _, _, phrase in scored_mid:
            if has_paren:
                candidate = base + "）" + phrase
            else:
                candidate = title + phrase
            if TARGET_MIN <= len(candidate) <= TARGET_MAX:
                used_suffixes["mid:" + phrase] = used_suffixes.get("mid:" + phrase, 0) + 1
                title = candidate
                break

    # Step 4: If still short, add category-based suffix
    if len(title) < TARGET_MIN:
        suffix_list = SUFFIXES.get(category, FALLBACK_SUFFIXES)

        # Pick least-used suffix to avoid repetition
        scored = []
        for s in suffix_list:
            count = used_suffixes.get(s, 0)
            scored.append((count, random.random(), s))
        scored.sort()

        for _, _, suffix in scored:
            candidate = title + suffix
            if TARGET_MIN <= len(candidate) <= TARGET_MAX:
                used_suffixes[suffix] = used_suffixes.get(suffix, 0) + 1
                title = candidate
                break
        else:
            # Try truncating
            for _, _, suffix in scored:
                candidate = title + suffix
                if len(candidate) > TARGET_MAX:
                    truncated = _truncate(candidate, TARGET_MAX)
                    if len(truncated) >= TARGET_MIN:
                        used_suffixes[suffix] = used_suffixes.get(suffix, 0) + 1
                        title = truncated
                        break

    # Step 5: If STILL short (very rare), pad with body keywords
    if len(title) < TARGET_MIN:
        body_kws = extract_body_keywords(body, title, n=3)
        if body_kws:
            kw_str = "・".join(body_kws)
            if "｜" in title:
                parts = title.split("｜", 1)
                candidate = f"{parts[0]}（{kw_str}）｜{parts[1]}"
            else:
                candidate = f"{title}（{kw_str}）"
            if len(candidate) > TARGET_MAX:
                candidate = _truncate(candidate, TARGET_MAX)
            title = candidate

    # Step 6: For duplicates, differentiate using body keywords
    if is_duplicate:
        keywords = extract_body_keywords(body, title, n=2)
        if keywords:
            kw_str = "・".join(keywords[:2])
            if "｜" in title:
                parts = title.split("｜", 1)
                candidate = f"{parts[0]}（{kw_str}）｜{parts[1]}"
            else:
                candidate = f"{title}（{kw_str}）"
            if len(candidate) <= TARGET_MAX:
                title = candidate
            else:
                title = _truncate(candidate, TARGET_MAX)

    # Step 7: Final length check
    if len(title) > TARGET_MAX:
        title = _truncate(title, TARGET_MAX)

    return title


def _truncate(text: str, max_len: int) -> str:
    """Truncate text at natural break point."""
    if len(text) <= max_len:
        return text

    truncated = text[:max_len]

    # Try to cut at a natural break point
    for sep in ['｜', '・', '（', '、', 'の', 'と', 'を']:
        idx = truncated.rfind(sep)
        if idx > max_len * 0.6:
            truncated = truncated[:idx]
            break

    # Remove trailing partial brackets
    if '（' in truncated and '）' not in truncated:
        idx = truncated.rfind('（')
        truncated = truncated[:idx]

    return truncated.rstrip('｜・、。 ')


def get_articles():
    """Get all articles with parsed metadata."""
    posts = sorted(POSTS_DIR.glob("*.md"))
    articles = []

    for post_path in posts:
        try:
            content = post_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue

        fm_text, body, fm = parse_front_matter(content)
        if not fm_text:
            continue

        title = fm.get('title', '').strip('"').strip("'")
        category = fm.get('categories', '').strip('[]"').split(',')[0].strip().strip('"')
        tags_str = fm.get('tags', '')
        tags = extract_tags(tags_str)

        articles.append({
            'path': post_path,
            'title': title,
            'title_len': len(title),
            'category': category,
            'tags': tags,
            'body': body,
            'content': content,
        })

    return articles


def update_title_in_file(post_path: Path, old_title: str, new_title: str) -> bool:
    """Update title in file's front matter."""
    content = post_path.read_text(encoding='utf-8', errors='ignore')
    new_content = content.replace(f'title: "{old_title}"', f'title: "{new_title}"', 1)
    if new_content == content:
        new_content = content.replace(f"title: '{old_title}'", f'title: "{new_title}"', 1)
    if new_content != content:
        post_path.write_text(new_content, encoding='utf-8')
        return True
    return False


def main():
    dry_run = '--fix' not in sys.argv
    limit = None
    for arg in sys.argv:
        if arg.startswith('--limit='):
            limit = int(arg.split('=')[1])

    if dry_run:
        print("DRY RUNモード (--fix で実際に修正)")
    else:
        print("FIXモード: タイトルを修正します")

    # Set random seed for reproducibility in dry run
    random.seed(42)

    articles = get_articles()
    print(f"総記事数: {len(articles)}")

    # Find short titles and duplicates
    title_counts = Counter(a['title'] for a in articles)
    duplicates = {t for t, c in title_counts.items() if c > 1}

    needs_fix = []
    for art in articles:
        reasons = []
        if art['title_len'] < MIN_TITLE_LEN:
            reasons.append(f"short({art['title_len']}文字)")
        if art['title'] in duplicates:
            reasons.append("duplicate")
        if reasons:
            art['reason'] = ', '.join(reasons)
            needs_fix.append(art)

    print(f"修正対象: {len(needs_fix)}件 (短いタイトル or 重複)")

    if limit:
        needs_fix = needs_fix[:limit]
        print(f"制限: 先頭{limit}件のみ処理")

    if not needs_fix:
        print("修正対象なし")
        return

    # Process
    used_suffixes: dict[str, int] = {}
    results = []

    for art in needs_fix:
        is_dup = art['title'] in duplicates
        new_title = build_optimized_title(
            art['title'],
            art['category'],
            art['tags'],
            art['body'],
            used_suffixes,
            is_duplicate=is_dup,
        )

        if new_title != art['title']:
            results.append({
                'path': art['path'],
                'old_title': art['title'],
                'new_title': new_title,
                'old_len': art['title_len'],
                'new_len': len(new_title),
                'reason': art['reason'],
                'category': art['category'],
            })

    # Summary
    print(f"\n変更件数: {len(results)}件")
    unchanged = len(needs_fix) - len(results)
    if unchanged:
        print(f"変更なし: {unchanged}件")

    # Length distribution
    len_ranges = Counter()
    for r in results:
        nl = r['new_len']
        if nl < TARGET_MIN:
            len_ranges['<45'] += 1
        elif nl <= TARGET_MAX:
            len_ranges['45-58'] += 1
        else:
            len_ranges['>58'] += 1

    print(f"\n文字数分布:")
    for k in ['<45', '45-58', '>58']:
        print(f"  {k}: {len_ranges.get(k, 0)}件")

    # Category breakdown
    cat_counts = Counter(r['category'] for r in results)
    print(f"\nカテゴリ別:")
    for c, n in cat_counts.most_common():
        print(f"  {c}: {n}件")

    # Show samples
    print(f"\n--- サンプル (先頭30件) ---")
    for r in results[:30]:
        mark = "OK" if TARGET_MIN <= r['new_len'] <= TARGET_MAX else "!!"
        print(f"  [{mark}] [{r['old_len']}→{r['new_len']}] {r['old_title']}")
        print(f"       → {r['new_title']}")

    # Check for new duplicates
    new_titles = Counter()
    for r in results:
        new_titles[r['new_title']] += 1
    new_dups = {t for t, c in new_titles.items() if c > 1}
    if new_dups:
        print(f"\n⚠ 新規重複タイトル: {len(new_dups)}件")
        for t in list(new_dups)[:5]:
            print(f"  {t}")

    if dry_run:
        print(f"\n[DRY RUN] --fix オプションで実際に修正を実行")
        return

    # Apply fixes
    fixed = 0
    failed = 0
    for r in results:
        if update_title_in_file(r['path'], r['old_title'], r['new_title']):
            fixed += 1
        else:
            print(f"  FAIL: {r['old_title']}")
            failed += 1

    print(f"\n--- 結果 ---")
    print(f"修正成功: {fixed}件")
    if failed:
        print(f"修正失敗: {failed}件")

    # Verify
    print(f"\n--- 修正後の検証 ---")
    articles_after = get_articles()
    still_short = sum(1 for a in articles_after if a['title_len'] < MIN_TITLE_LEN)
    title_counts_after = Counter(a['title'] for a in articles_after)
    still_dup = sum(1 for t, c in title_counts_after.items() if c > 1)
    print(f"残り短いタイトル(<40文字): {still_short}件")
    print(f"残り重複タイトル: {still_dup}種類")


if __name__ == '__main__':
    main()
