#!/usr/bin/env python3
"""Publish one Daily Notes issue to track/daily-notes/.

usage: publish.py <repo> <issue.html> <YYYY-MM-DD> <am|pm> <window> "<one-line desc>" <n_in_window> <n_relevant>

<issue.html> is the artifact page (no <html>/<head>; starts with <title>). Absolute links to
https://caffrey-mushroom.github.io/intrinsic/notes/<slug>/ are rewritten to relative ones.
Writes track/daily-notes/<date>-<am|pm>/index.html, updates track/daily-notes/issues.json,
re-renders track/daily-notes/index.html and the Daily notes row on the home page.
"""
import html, json, re, sys
from pathlib import Path

SITE = 'https://caffrey-mushroom.github.io/intrinsic/'
LABEL = {'am': '早间版', 'pm': '晚间版'}


def page(src, title):
    body = src.split('</style>', 1)
    head_css = body[0].split('<style>', 1)[1]
    rest = body[1]
    rest = rest.replace(SITE + 'notes/', '../../../notes/').replace(SITE, '../../../')
    bar = ('<header class="mbar"><div class="mbar-in">'
           '<a class="back" href="../" aria-label="返回 Daily notes">←&#8201;返回</a>'
           '<a class="mark" href="../../../" aria-label="Mushroom 首页"><span>Mushroom</span></a>'
           '<span class="crumb">Track · Daily notes</span><span class="sp"></span></div></header>')
    bar_css = ('.mbar{position:sticky;top:env(safe-area-inset-top,0px);z-index:20;background:var(--bg);border-bottom:var(--hair)}'
               '.mbar-in{max-width:1180px;margin:0 auto;padding:0 max(16px,env(safe-area-inset-left,0px));height:56px;display:flex;align-items:center;gap:16px}'
               '.mark{font-family:var(--serif);font-weight:500;font-size:19px;color:var(--text)}.mark:hover{text-decoration:none}'
               '.back{display:flex;align-items:center;gap:16px;color:var(--muted);white-space:nowrap}'
               '.back::after{content:"";width:1px;height:16px;background:var(--rule)}'
               '.crumb{color:var(--muted);display:flex;align-items:center;gap:16px;white-space:nowrap}'
               '.crumb::before{content:"";width:1px;height:16px;background:var(--rule)}.mbar .sp{flex:1}'
               'nav.toc{top:calc(env(safe-area-inset-top,0px) + 96px)}')
    return ('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            f'<title>{html.escape(title)}</title>\n'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Noto+Serif+SC:wght@500&display=swap">\n'
            f'<style>{head_css}{bar_css}</style>\n</head><body>\n{bar}\n{rest}\n</body></html>\n')


def index(repo, issues):
    tpl = (repo / 'track/cpu/index.html').read_text(encoding='utf-8')
    head = tpl.split('<body>', 1)[0].replace('<title>CPU</title>', '<title>Daily notes</title>')
    head = re.sub(r'<title>[^<]*</title>', '<title>Daily notes</title>', head)
    rows = []
    for it in issues:
        d = it['date'].replace('-', '.')
        rows.append(
            f'      <a class="row" href="./{it["slug"]}/">\n        <div>\n'
            f'          <div class="kick num">{d} · {LABEL[it["edition"]]} · {html.escape(it["window"])}</div>\n'
            f'          <div class="name">Daily Notes · {LABEL[it["edition"]]}</div>\n'
            f'          <div class="desc">{html.escape(it["desc"])}</div>\n'
            f'          <div class="meta">窗口内入库 {it["n"]} 篇 · AI 供需相关 {it["rel"]} 篇</div>\n'
            '        </div>\n      </a>')
    body = ('<body>\n<header class="mbar"><div class="mbar-in">\n'
            '  <a class="back" href="../../" aria-label="返回首页">←&#8201;返回</a>\n'
            '  <a class="mark" href="../../" aria-label="Mushroom 首页"><span>Mushroom</span></a>\n'
            '  <span class="crumb">Track · Daily notes</span>\n  <span class="sp"></span>\n</div></header>\n\n'
            '<main class="page">\n  <h1 class="ptitle">Daily notes</h1>\n'
            '  <p class="psub">每天两期：05:00 早间版 (前一天 20:00 到 05:00)，20:00 晚间版 (05:00 到 20:00)。挑出值得读的 notes 和 AI 供需的核心信息，每条链到 Notes 原文页</p>\n\n'
            '  <section class="sec">\n    <h2 class="sec-t">全部期数</h2>\n    <div class="list">\n'
            + '\n'.join(rows) + '\n    </div>\n  </section>\n</main>\n</body>\n</html>\n')
    (repo / 'track/daily-notes/index.html').write_text(head + body, encoding='utf-8')


def home(repo, issues):
    p = repo / 'index.html'
    t = p.read_text(encoding='utf-8')
    latest = issues[0]
    row = ('      <a class="row" href="./track/daily-notes/">\n'
           f'        <div><div class="name">Daily notes</div><div class="desc">最新：{latest["date"].replace("-", ".")} {LABEL[latest["edition"]]}</div></div>\n'
           f'        <div class="side">{len(issues)} 期</div>\n      </a>\n')
    t = re.sub(r'      <a class="row" href="\./track/daily-notes/">.*?</a>\n', '', t, flags=re.S)
    anchor = '      <a class="row" href="./track/ai-demands/">'
    t = t.replace(anchor, row + anchor, 1)
    p.write_text(t, encoding='utf-8')


def main():
    repo, src, date, ed, window, desc, n, rel = sys.argv[1:9]
    repo = Path(repo)
    slug = f'{date}-{ed}'
    srctext = Path(src).read_text(encoding='utf-8')
    title = re.search(r'<title>([^<]*)</title>', srctext).group(1)
    out = repo / 'track/daily-notes' / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / 'index.html').write_text(page(srctext, title), encoding='utf-8')
    jp = repo / 'track/daily-notes/issues.json'
    issues = json.loads(jp.read_text()) if jp.exists() else []
    issues = [i for i in issues if i['slug'] != slug]
    issues.append({'slug': slug, 'date': date, 'edition': ed, 'window': window, 'desc': desc, 'n': int(n), 'rel': int(rel)})
    issues.sort(key=lambda i: (i['date'], i['edition'] == 'pm'), reverse=True)
    jp.write_text(json.dumps(issues, ensure_ascii=False, indent=1), encoding='utf-8')
    index(repo, issues)
    home(repo, issues)
    print('published', slug)


if __name__ == '__main__':
    main()
