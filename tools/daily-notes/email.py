#!/usr/bin/env python3
"""Build the email version of a published Daily Notes issue.

usage: email.py <repo> <YYYY-MM-DD-am|pm> <out.html>
Prints the subject. The body keeps 主线 and 先读这 N 篇 with absolute links,
plus a link to the full issue. Fonts: Times New Roman for Latin, STKaiti for Chinese.
"""
import re, sys
from pathlib import Path

SITE = 'https://caffrey-mushroom.github.io/intrinsic/'
FONT = "font-family:'Times New Roman',STKaiti,'华文楷体',KaiTi,serif;"
TEXT = FONT + 'font-size:15px;line-height:1.7;color:#1f2933;'
STY = {
    'h1': FONT + 'font-size:22px;font-weight:500;color:#1f2933;margin:0 0 6px;',
    'h2': FONT + 'font-size:18px;font-weight:500;color:#7189A7;margin:24px 0 8px;border-bottom:1px solid #d8dee6;padding-bottom:4px;',
    'h3': FONT + 'font-size:16px;font-weight:500;color:#1f2933;margin:18px 0 4px;',
    'p': TEXT + 'margin:6px 0;',
    'li': TEXT + 'margin:2px 0;',
    'ul': TEXT + 'margin:4px 0 4px 20px;padding:0;',
    'a': 'color:#4f6a8c;text-decoration:none;',
}


def main():
    repo, slug, out = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
    page = (repo / 'track/daily-notes' / slug / 'index.html').read_text(encoding='utf-8')
    title = re.search(r'<h1[^>]*>(.*?)</h1>', page, re.S).group(1)
    meta = re.search(r'<p class="meta">(.*?)</p>', page, re.S)
    start = page.find('<h2>今天的主线')
    ends = [i for i in (page.find('<h2>分层速览'), page.find('<h2>数字速查'), page.find('</main>')) if i > 0]
    body = page[start:min(ends)]
    body = re.sub(r'<section class="sec" id="s\d">\s*$', '', body)
    body = body.replace('</span><span class="chip">', ' / ')
    body = re.sub(r'<(?!/?(a|h2|h3|li|ul|ol|p)\b)[^>]*>', '', body)
    body = re.sub(r'<(h2|h3|li|ul|p)\b[^>]*>', lambda m: f'<{m[1]} style="{STY[m[1]]}">', body)
    body = re.sub(r'<ol\b[^>]*>', f'<ul style="{STY["ul"]}">', body).replace('</ol>', '</ul>')
    if '<li' in body and '<ul' not in body:
        body = re.sub(r'((?:\s*<li .*?</li>)+)', rf'<ul style="{STY["ul"]}">\1</ul>', body, flags=re.S)
    url = f'{SITE}track/daily-notes/{slug}/'
    def link(m):
        href = m[1]
        href = re.sub(r'^(\.\./)+', SITE, href) if href.startswith('..') else href
        return f'<a href="{href}" style="{STY["a"]}">'
    body = re.sub(r'<a\b[^>]*href="([^"]+)"[^>]*>', link, body)
    body = re.sub(r'(?m)^\s*\d+\s*$', '', body)
    body = re.sub(r'(?m)^\s*([^<\s][^\n]*)$',
                  lambda m: f'<p style="{TEXT}font-size:13px;color:#6b7785;margin:0 0 4px;">{m[1]}</p>', body)
    body = re.sub(r'\n\s*\n+', '\n', body)
    meta_txt = re.sub(r'<[^>]+>', '', meta[1]) if meta else ''
    html = (f'<div style="{TEXT}max-width:720px;">'
            f'<h1 style="{STY["h1"]}">{title}</h1>'
            f'<p style="{TEXT}font-size:13px;color:#6b7785;margin:0 0 12px;">{meta_txt}</p>'
            f'{body}'
            f'<p style="{STY["p"]}margin-top:24px;">完整版 (分层速览、反方信号、数字速查、全部篇目)：'
            f'<a href="{url}" style="{STY["a"]}">{url}</a></p></div>')
    Path(out).write_text(html, encoding='utf-8')
    print(f'Daily Notes · {re.sub(r"<[^>]+>", "", title).split("|")[0].strip()} {"早间版" if slug.endswith("am") else "晚间版"}')


if __name__ == '__main__':
    main()
