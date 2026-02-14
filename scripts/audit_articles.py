#!/usr/bin/env python3
"""記事品質監査スクリプト - 既存記事の品質問題を特定・レポート"""

import os
import re
import yaml
import json
from collections import Counter, defaultdict
from pathlib import Path

POSTS_DIR = Path(__file__).parent.parent / "_posts"
REPORT_PATH = Path(__file__).parent.parent / "_data" / "audit_report.json"

GENERIC_EXCERPTS = [
    "最新のAI技術動向と市場分析をお届けします。",
    "最新のAI技術動向と市場分析をお届けします",
]


def parse_frontmatter(filepath):
    """記事のfrontmatterとbodyを解析"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        return None, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None, content

    try:
        fm = yaml.safe_load(parts[1])
    except yaml.YAMLError:
        fm = None

    body = parts[2].strip()
    return fm, body


def extract_first_paragraph(body):
    """本文から最初の意味のある段落を抽出（見出し・空行をスキップ）"""
    lines = body.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        if line.startswith("!["):
            continue
        if line.startswith("{%"):
            continue
        # 意味のある段落を発見
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        clean = re.sub(r'[*_`]', '', clean)
        if len(clean) > 30:
            return clean[:200]
    return None


def audit_articles():
    """全記事を監査してレポート生成"""
    files = sorted(POSTS_DIR.glob("*.md"))
    print(f"監査対象: {len(files)} 記事\n")

    issues = {
        "generic_excerpt": [],
        "no_excerpt": [],
        "no_image": [],
        "short_body": [],
        "garbled_filename": [],
        "duplicate_title": [],
        "no_categories": [],
        "no_tags": [],
    }

    all_titles = defaultdict(list)
    stats = {
        "total": len(files),
        "by_month": Counter(),
        "by_category": Counter(),
        "with_image": 0,
        "with_custom_excerpt": 0,
    }

    for fp in files:
        fm, body = parse_frontmatter(fp)
        fname = fp.name

        if fm is None:
            issues["no_excerpt"].append(fname)
            continue

        title = fm.get("title", "")
        excerpt = fm.get("excerpt", "")
        image = fm.get("image", "")
        categories = fm.get("categories", [])
        tags = fm.get("tags", [])
        date_str = fm.get("date", "")

        # 月別集計
        match = re.match(r"(\d{4}-\d{2})", fname)
        if match:
            stats["by_month"][match.group(1)] += 1

        # カテゴリ集計
        if isinstance(categories, list):
            for c in categories:
                stats["by_category"][c] += 1
        elif isinstance(categories, str):
            stats["by_category"][categories] += 1

        # タイトル重複チェック
        if title:
            all_titles[title].append(fname)

        # 定型excerpt チェック
        if not excerpt:
            issues["no_excerpt"].append(fname)
        elif excerpt.strip() in GENERIC_EXCERPTS:
            issues["generic_excerpt"].append(fname)
        else:
            stats["with_custom_excerpt"] += 1

        # OGP画像チェック
        if image:
            stats["with_image"] += 1
        else:
            issues["no_image"].append(fname)

        # 本文が短すぎ (500文字未満)
        body_text = re.sub(r'\s+', '', body)
        if len(body_text) < 500:
            issues["short_body"].append({"file": fname, "chars": len(body_text)})

        # ファイル名の文字化け/日本語チェック
        if re.search(r'[\u3000-\u9fff\uff00-\uffef]', fname):
            issues["garbled_filename"].append(fname)

        # カテゴリ・タグなし
        if not categories:
            issues["no_categories"].append(fname)
        if not tags:
            issues["no_tags"].append(fname)

    # 重複タイトル
    for title, fnames in all_titles.items():
        if len(fnames) > 1:
            issues["duplicate_title"].append({"title": title, "files": fnames})

    # レポート出力
    print("=" * 60)
    print("品質監査レポート")
    print("=" * 60)

    print(f"\n総記事数: {stats['total']}")
    print(f"固有excerpt: {stats['with_custom_excerpt']} ({stats['with_custom_excerpt']*100//stats['total']}%)")
    print(f"OGP画像あり: {stats['with_image']} ({stats['with_image']*100//stats['total']}%)")

    print(f"\n--- 問題別件数 ---")
    print(f"定型excerpt (要改善): {len(issues['generic_excerpt'])}")
    print(f"excerpt なし: {len(issues['no_excerpt'])}")
    print(f"OGP画像なし: {len(issues['no_image'])}")
    print(f"本文500文字未満: {len(issues['short_body'])}")
    print(f"日本語ファイル名: {len(issues['garbled_filename'])}")
    print(f"タイトル重複: {len(issues['duplicate_title'])}")
    print(f"カテゴリなし: {len(issues['no_categories'])}")
    print(f"タグなし: {len(issues['no_tags'])}")

    if issues["short_body"]:
        print(f"\n--- 短すぎる記事 (上位10件) ---")
        for item in sorted(issues["short_body"], key=lambda x: x["chars"])[:10]:
            print(f"  {item['chars']}文字: {item['file']}")

    if issues["duplicate_title"]:
        print(f"\n--- タイトル重複 (上位10件) ---")
        for item in issues["duplicate_title"][:10]:
            print(f"  [{item['title']}]")
            for f in item["files"]:
                print(f"    - {f}")

    if issues["garbled_filename"]:
        print(f"\n--- 日本語ファイル名 (上位10件) ---")
        for f in issues["garbled_filename"][:10]:
            print(f"  {f}")

    print(f"\n--- 月別記事数 ---")
    for month, count in sorted(stats["by_month"].items()):
        print(f"  {month}: {count}本")

    print(f"\n--- カテゴリ分布 (上位15) ---")
    for cat, count in stats["by_category"].most_common(15):
        print(f"  {cat}: {count}本")

    # JSON保存
    report = {
        "stats": {
            "total": stats["total"],
            "with_custom_excerpt": stats["with_custom_excerpt"],
            "with_image": stats["with_image"],
            "by_month": dict(sorted(stats["by_month"].items())),
        },
        "issues": {
            "generic_excerpt_count": len(issues["generic_excerpt"]),
            "generic_excerpt_files": issues["generic_excerpt"],
            "no_image_count": len(issues["no_image"]),
            "short_body": issues["short_body"],
            "garbled_filename": issues["garbled_filename"],
            "duplicate_title": issues["duplicate_title"],
        },
    }
    os.makedirs(REPORT_PATH.parent, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n詳細レポート保存: {REPORT_PATH}")


if __name__ == "__main__":
    audit_articles()
