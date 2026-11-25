#!/usr/bin/env python3
"""Publish one Hypothesis Weekly issue to track/weekly/ (grouped by week).

usage: publish.py <repo> <issue.html> <slug> <week_id> "<week_label>" "<hypothesis>" "<verdict>" "<one-line desc>" <notes_total> <notes_read> <twitter_count>

Example:
  publish.py . issue.html 2026-11-25-soxx-is-a-short 2026-11-19..2026-11-25 "2026.11.19–11.25" "Hypothesis - SOXX is a short" "基本面偏空 · 估值压赔率" "一句话摘要" 356 46 6

<issue.html> starts with <title>...</title> and <style>...</style> (no <html>/<head>/<body>).
Writes track/weekly/<slug>/index.html, updates track/weekly/issues.json,
re-renders track/weekly/index.html (grouped by week, newest week first),
and updates the Weekly row on index.html (replacing legacy Semis/Infra/Application display rows if present).
"""
import html, json, re, sys
from pathlib import Path
from collections import OrderedDict

SITE = 'https://caffrey-mushroom.github.io/intrinsic/'


def page(src, title, crumb):
    body = src.split('</style>', 1)
    head_css = body[0].split('<style>', 1)[1]
    rest = body[1]
    rest = rest.replace(SITE + 'notes/', '../../../notes/').replace(SITE + 'twitter/', '../../../twitter/').replace(SITE, '../../../')
    bar = ('<header class="mbar"><div class="mbar-in">'
           '<a class="back" href="../" aria-label="返回 Weekly">←&#8201;返回</a>'
           '<a class="mark" href="../../../" aria-label="Mushroom 首页"><span>Mushroom</span></a>'
           f'<span class="crumb">{html.escape(crumb)}</span><span class="sp"></span></div></header>')
    bar_css = ('.mbar{position:sticky;top:env(safe-area-inset-top,0px);z-index:20;background:var(--bg);border-bottom:var(--hair)}'
               '.mbar-in{max-width:1320px;margin:0 auto;padding:0 max(16px,env(safe-area-inset-left,0px));height:56px;display:flex;align-items:center;gap:16px}'
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


def render_index(repo, issues):
    tpl = (repo / 'track/semis/index.html').read_text(encoding='utf-8')
    head = re.sub(r'<title>[^<]*</title>', '<title>Weekly · Mushroom</title>', tpl.split('<body>', 1)[0])
    # Widen index shell to match user preference
    head = head.replace(':root{--page-w:960px}', ':root{--page-w:1120px}')
    head = head.replace('max-width:64ch', 'max-width:none')
    head = head.replace('max-width:72ch', 'max-width:none')

    # Group by week_id (newest week first)
    by_week = OrderedDict()
    for it in issues:
        by_week.setdefault((it['week'], it['week_label']), []).append(it)

    secs = []
    for (wk, wk_label), items in by_week.items():
        rows = []
        for it in items:
            rows.append(
                f'      <a class="row" href="./{it["slug"]}/">\n'
                '        <div>\n'
                f'          <div class="kick num">{html.escape(it["week_label"])} · {html.escape(it["verdict"])}</div>\n'
                f'          <div class="name">{html.escape(it["hypothesis"])}</div>\n'
                f'          <div class="desc">{html.escape(it["desc"])}</div>\n'
                f'          <div class="meta">覆盖 Notes {it["notes_total"]} 篇（核心精读 {it["notes_read"]} 篇）· Twitter {it["twitter_count"]} 期</div>\n'
                '        </div>\n'
                '      </a>')
        secs.append(
            f'  <section class="sec" id="wk-{html.escape(wk)}">\n'
            f'    <h2 class="sec-t">{html.escape(wk_label)}</h2>\n'
            '    <div class="list">\n' + '\n'.join(rows) + '\n    </div>\n'
            '  </section>')

    body = ('<body>\n<header class="mbar"><div class="mbar-in">\n'
            '  <a class="back" href="../../" aria-label="返回首页">←&#8201;返回</a>\n'
            '  <a class="mark" href="../../" aria-label="Mushroom 首页"><span>Mushroom</span></a>\n'
            '  <span class="crumb">Track · Weekly</span>\n  <span class="sp"></span>\n</div></header>\n\n'
            '<main class="page">\n  <h1 class="ptitle">Weekly</h1>\n'
            '  <p class="psub">按周归类的 Hypothesis 深度证据周报：整合过去 7 日 Knowledge Base 纪要与麻薯站 Twitter 动态，围绕 Notion 最新 Hypothesis 做正反证据检验、反常识原文核对与置信度审计。</p>\n\n'
            + '\n\n'.join(secs) + '\n</main>\n</body>\n</html>\n')
    out_dir = repo / 'track/weekly'
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'index.html').write_text(head + body, encoding='utf-8')


def update_home(repo, issues):
    p = repo / 'index.html'
    t = p.read_text(encoding='utf-8')
    latest = issues[0]
    weeks = len({i['week'] for i in issues})
    row = ('      <a class="row" href="./track/weekly/">\n'
           f'        <div><div class="name">Weekly</div><div class="desc">最新：{html.escape(latest["week_label"])} · {html.escape(latest["hypothesis"])}</div></div>\n'
           f'        <div class="side">{weeks} 周 · {len(issues)} 篇</div>\n      </a>\n')
    # Remove legacy Semis / Infra / Application display rows (files remain archived in repo)
    for legacy in ('./track/semis/', './track/infra/', './track/application/', './track/weekly/'):
        t = re.sub(r'      <a class="row" href="' + re.escape(legacy) + r'">.*?</a>\n', '', t, flags=re.S)
    # Place Weekly right below Daily notes
    anchor = '      <a class="row" href="./track/ai-demands/">'
    t = t.replace(anchor, row + anchor, 1)
    p.write_text(t, encoding='utf-8')


def main():
    repo, src, slug, week, week_label, hyp, verdict, desc, n_tot, n_read, n_tw = sys.argv[1:12]
    repo = Path(repo)
    srctext = Path(src).read_text(encoding='utf-8')
    title = re.search(r'<title>([^<]*)</title>', srctext).group(1)
    out = repo / 'track/weekly' / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / 'index.html').write_text(page(srctext, title, f'Track · Weekly · {week_label}'), encoding='utf-8')

    jp = repo / 'track/weekly/issues.json'
    issues = json.loads(jp.read_text(encoding='utf-8')) if jp.exists() else []
    issues = [i for i in issues if i['slug'] != slug]
    issues.append({
        'slug': slug, 'week': week, 'week_label': week_label,
        'hypothesis': hyp, 'verdict': verdict, 'desc': desc,
        'notes_total': int(n_tot), 'notes_read': int(n_read), 'twitter_count': int(n_tw),
    })
    issues.sort(key=lambda i: (i['week'], i['slug']), reverse=True)
    jp.write_text(json.dumps(issues, ensure_ascii=False, indent=1), encoding='utf-8')
    render_index(repo, issues)
    update_home(repo, issues)
    print('published weekly', slug)


if __name__ == '__main__':
    main()
