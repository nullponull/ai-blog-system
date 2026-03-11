#!/usr/bin/env python3
"""
Site Inspector — ページ構造をテキストツリーで出力するCSS/レイアウトデバッグツール

スクリーンショットの代わりにHTML構造をテキストで返すことで:
- トークン消費を1/10以下に削減（画像4000-12000→テキスト500-800トークン）
- CSS class情報を含むためレイアウト問題を即座に特定可能
- diff可能なためイテレーション効率が高い

Usage:
  python3 scripts/site_inspector.py https://ai-media.co.jp/
  python3 scripts/site_inspector.py https://ai-media.co.jp/2026/03/12/... --section post-content
  python3 scripts/site_inspector.py https://ai-media.co.jp/ --mode css-audit
  python3 scripts/site_inspector.py https://ai-media.co.jp/ --mode table-check
  python3 scripts/site_inspector.py https://ai-media.co.jp/ --mode responsive
"""

import argparse
import sys
import urllib.request
from html.parser import HTMLParser


class StructureExtractor(HTMLParser):
    """HTML構造をインデント付きテキストツリーで出力"""

    BLOCK_TAGS = {
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'div', 'section', 'article', 'nav', 'header', 'footer', 'main', 'aside',
        'table', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
        'ul', 'ol', 'li',
        'form', 'fieldset', 'details', 'summary',
        'figure', 'figcaption', 'blockquote', 'pre', 'code',
    }
    INLINE_TAGS = {'a', 'img', 'span', 'strong', 'em', 'br'}
    TEXT_TAGS = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'th', 'td', 'li', 'a', 'summary', 'figcaption', 'blockquote'}

    def __init__(self, target_section=None, max_lines=300):
        super().__init__()
        self.depth = 0
        self.output = []
        self.text_buf = ''
        self.current_tag = None
        self.target_section = target_section
        self.in_target = target_section is None  # if no target, capture everything in body
        self.in_body = False
        self.max_lines = max_lines
        self.tag_stack = []

    def handle_starttag(self, tag, attrs):
        if tag == 'body':
            self.in_body = True

        if not self.in_body:
            return

        attrs_dict = dict(attrs)
        cls = attrs_dict.get('class', '')

        # Check if we entered target section
        if self.target_section and self.target_section in cls:
            self.in_target = True

        if not self.in_target:
            return

        if len(self.output) >= self.max_lines:
            return

        if tag in self.BLOCK_TAGS or tag in self.INLINE_TAGS:
            indent = '  ' * self.depth
            parts = [f'{indent}<{tag}']
            if cls:
                parts.append(f' class="{cls}"')
            if tag == 'img':
                alt = attrs_dict.get('alt', '')
                src = attrs_dict.get('src', '')
                if alt:
                    parts.append(f' alt="{alt[:60]}"')
                if src:
                    parts.append(f' src="{src[:80]}"')
            if tag == 'a':
                href = attrs_dict.get('href', '')
                if href:
                    parts.append(f' href="{href[:60]}"')
            # Table-specific
            if tag in ('th', 'td'):
                colspan = attrs_dict.get('colspan', '')
                if colspan:
                    parts.append(f' colspan="{colspan}"')
                style = attrs_dict.get('style', '')
                if style:
                    parts.append(f' style="{style[:60]}"')
            parts.append('>')
            self.output.append(''.join(parts))

        if tag in self.BLOCK_TAGS:
            self.depth += 1
            self.tag_stack.append(tag)

        self.current_tag = tag
        self.text_buf = ''

    def handle_endtag(self, tag):
        if not self.in_target:
            return

        if tag in self.BLOCK_TAGS and self.tag_stack and self.tag_stack[-1] == tag:
            self.depth = max(0, self.depth - 1)
            self.tag_stack.pop()

            if self.text_buf.strip() and tag in self.TEXT_TAGS:
                text = self.text_buf.strip()[:100]
                indent = '  ' * (self.depth + 1)
                if len(self.output) < self.max_lines:
                    self.output.append(f'{indent}"{text}"')
            self.text_buf = ''

        # Check if we left target section
        if self.target_section and tag in ('div', 'section', 'article', 'main'):
            if self.depth == 0:
                self.in_target = False

    def handle_data(self, data):
        if self.in_target:
            self.text_buf += data

    def get_output(self):
        return '\n'.join(self.output)


class CSSAuditor(HTMLParser):
    """CSS class使用状況を集計"""

    def __init__(self):
        super().__init__()
        self.classes = {}
        self.tag_counts = {}
        self.tables = []
        self.current_table = None
        self.in_body = False

    def handle_starttag(self, tag, attrs):
        if tag == 'body':
            self.in_body = True
        if not self.in_body:
            return

        attrs_dict = dict(attrs)
        cls = attrs_dict.get('class', '')

        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1

        if cls:
            for c in cls.split():
                self.classes[c] = self.classes.get(c, 0) + 1

        if tag == 'table':
            self.current_table = {'rows': 0, 'cols': 0, 'has_wrapper': False, 'classes': cls}
        if tag == 'tr' and self.current_table:
            self.current_table['rows'] += 1
        if tag in ('th', 'td') and self.current_table:
            self.current_table['cols'] = max(self.current_table.get('cols', 0), 1)
        if tag == 'div' and 'table-wrapper' in cls and self.current_table is None:
            # Next table will have a wrapper
            pass

    def handle_endtag(self, tag):
        if tag == 'table' and self.current_table:
            self.tables.append(self.current_table)
            self.current_table = None

    def report(self):
        lines = ['=== CSS Audit Report ===', '']

        lines.append('--- Tag Counts ---')
        for tag, count in sorted(self.tag_counts.items(), key=lambda x: -x[1])[:20]:
            lines.append(f'  <{tag}>: {count}')

        lines.append('')
        lines.append('--- Top CSS Classes ---')
        for cls, count in sorted(self.classes.items(), key=lambda x: -x[1])[:30]:
            lines.append(f'  .{cls}: {count}')

        if self.tables:
            lines.append('')
            lines.append(f'--- Tables ({len(self.tables)}) ---')
            for i, t in enumerate(self.tables):
                lines.append(f'  Table {i+1}: {t["rows"]} rows, classes="{t["classes"]}"')

        return '\n'.join(lines)


class TableChecker(HTMLParser):
    """テーブル構造の詳細チェック"""

    def __init__(self):
        super().__init__()
        self.tables = []
        self.current_table = None
        self.current_row = None
        self.cell_text = ''
        self.in_cell = False
        self.depth = 0
        self.wrapper_depth = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        cls = attrs_dict.get('class', '')

        if tag == 'div' and 'table-wrapper' in cls:
            self.wrapper_depth = self.depth

        if tag == 'table':
            self.current_table = {
                'classes': cls,
                'has_wrapper': self.wrapper_depth is not None,
                'style': attrs_dict.get('style', ''),
                'rows': [],
            }
        if tag == 'tr' and self.current_table is not None:
            self.current_row = []
        if tag in ('th', 'td') and self.current_row is not None:
            self.in_cell = True
            self.cell_text = ''

        self.depth += 1

    def handle_endtag(self, tag):
        self.depth -= 1

        if tag in ('th', 'td') and self.in_cell:
            self.in_cell = False
            if self.current_row is not None:
                self.current_row.append(self.cell_text.strip()[:40])
        if tag == 'tr' and self.current_row is not None and self.current_table is not None:
            self.current_table['rows'].append(self.current_row)
            self.current_row = None
        if tag == 'table' and self.current_table is not None:
            self.tables.append(self.current_table)
            self.current_table = None
        if tag == 'div' and self.depth == self.wrapper_depth:
            self.wrapper_depth = None

    def handle_data(self, data):
        if self.in_cell:
            self.cell_text += data

    def report(self):
        if not self.tables:
            return 'No tables found on this page.'

        lines = [f'=== Table Check: {len(self.tables)} table(s) ===', '']
        for i, table in enumerate(self.tables):
            wrapper = 'YES' if table['has_wrapper'] else 'NO (mobile overflow risk!)'
            lines.append(f'Table {i+1}: wrapper={wrapper}, classes="{table["classes"]}"')
            if table['style']:
                lines.append(f'  inline style: {table["style"]}')
            for j, row in enumerate(table['rows'][:5]):  # Show first 5 rows
                cols = ' | '.join(row)
                lines.append(f'  Row {j}: [{len(row)} cols] {cols}')
            if len(table['rows']) > 5:
                lines.append(f'  ... +{len(table["rows"]) - 5} more rows')
            lines.append('')
        return '\n'.join(lines)


class ResponsiveChecker(HTMLParser):
    """レスポンシブデザイン問題の検出"""

    def __init__(self):
        super().__init__()
        self.issues = []
        self.in_body = False
        self.meta_viewport = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == 'meta' and attrs_dict.get('name') == 'viewport':
            self.meta_viewport = True

        if tag == 'body':
            self.in_body = True
        if not self.in_body:
            return

        style = attrs_dict.get('style', '')
        cls = attrs_dict.get('class', '')

        # Fixed width detection
        if 'width:' in style and 'px' in style and 'max-width' not in style:
            self.issues.append(f'Fixed width in style: <{tag} class="{cls}" style="{style[:80]}">')

        # Table without wrapper
        if tag == 'table' and 'table-wrapper' not in cls:
            self.issues.append(f'Table without .table-wrapper class: <table class="{cls}">')

        # Large images without responsive class
        if tag == 'img':
            width = attrs_dict.get('width', '')
            if width and width.isdigit() and int(width) > 600:
                self.issues.append(f'Large image (width={width}): src="{attrs_dict.get("src", "")[:60]}"')

    def report(self):
        lines = ['=== Responsive Check ===', '']
        lines.append(f'meta viewport: {"YES" if self.meta_viewport else "MISSING!"}')
        lines.append('')
        if self.issues:
            lines.append(f'Issues found: {len(self.issues)}')
            for issue in self.issues:
                lines.append(f'  - {issue}')
        else:
            lines.append('No responsive issues detected.')
        return '\n'.join(lines)


def fetch_html(url):
    """URLからHTMLを取得"""
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')


def main():
    parser = argparse.ArgumentParser(description='Site Inspector — ページ構造をテキストで確認')
    parser.add_argument('url', help='検査対象のURL')
    parser.add_argument('--section', default=None,
                        help='特定セクションのみ抽出 (CSS class名, e.g. post-content)')
    parser.add_argument('--mode', default='structure',
                        choices=['structure', 'css-audit', 'table-check', 'responsive', 'all'],
                        help='検査モード')
    parser.add_argument('--max-lines', type=int, default=200,
                        help='構造出力の最大行数')
    args = parser.parse_args()

    print(f'Fetching: {args.url}', file=sys.stderr)
    html = fetch_html(args.url)
    print(f'HTML size: {len(html):,} bytes', file=sys.stderr)

    if args.mode in ('structure', 'all'):
        ext = StructureExtractor(target_section=args.section, max_lines=args.max_lines)
        ext.feed(html)
        print('\n=== Structure Tree ===')
        print(ext.get_output())

    if args.mode in ('css-audit', 'all'):
        auditor = CSSAuditor()
        auditor.feed(html)
        print()
        print(auditor.report())

    if args.mode in ('table-check', 'all'):
        checker = TableChecker()
        checker.feed(html)
        print()
        print(checker.report())

    if args.mode in ('responsive', 'all'):
        checker = ResponsiveChecker()
        checker.feed(html)
        print()
        print(checker.report())


if __name__ == '__main__':
    main()
