"""Weekly source appendix: map the notes a weekly read to their Mushroom Notes pages.

usage:
  sources.py <repo_root> <all_out.json> <weekly_page>            # inject into the page (idempotent)
  sources.py <repo_root> <all_out.json> <weekly_page> --html out  # only write the section html
  sources.py <repo_root> <all_out.json> --report                  # match report, no page

<all_out.json>: the issue's KB research-output/<date>-<track>-weekly/data/all_out.json
  (records with title, path, tier; extra keys ignored). Tier X (误命中) is dropped.
<weekly_page>: the issue page in the repo, e.g. track/semis/semicap-weekly-2026-10-15/index.html
Note links carry ?from=<issue path>; notes/back.js turns the note's back link into "返回周报".
"""
import os, re, sys, json, html
from datetime import date as D, timedelta

E = lambda s: html.escape(s or '', quote=True)
START, END = '<!-- weekly-sources:start -->', '<!-- weekly-sources:end -->'

def norm(s):
    return re.sub(r'[^0-9a-z一-鿿]', '', html.unescape(s or '').lower())

def load_notes(repo):
    idx = open(f'{repo}/notes/index.html', encoding='utf-8').read()
    rows = []
    for slug, d, src, name, orig in re.findall(
            r'<a class="row" href="\./([^"/]+)/">\s*<div>\s*<div class="kick num">(\S+) · (\S+) ·[^<]*</div>\s*'
            r'<div class="name">(.*?)</div>\s*<div class="desc">(.*?)</div>', idx, re.S):
        rows.append(dict(slug=slug, date=d.replace('.', '-'), src=src, name=html.unescape(name),
                         orig=html.unescape(orig), n=norm(orig)))
    return rows

TOP = {'Acecamp': 'AC', 'acecamp 2': 'AC', 'ThirdBridge': 'TB', 'GuidePoint': 'GP', 'MeritForum': '9K',
       'Substack': 'Substack', 'Funda': 'FUNDA', 'SemiAnalysis': 'SA'}
NOT_PUBLISHED = {'Tegus': 'Tegus 不公开发布', 'FactSet': 'FactSet 不公开发布', 'VIC': 'VIC 不公开发布'}

def classify(rec):
    """-> (src code, date, title used for matching, reason if never published)"""
    p = rec.get('path') or rec.get('rel') or ''
    top = p.split('/')[0]
    base = os.path.basename(p)[:-3] if p.endswith('.md') else os.path.basename(p)
    title = rec.get('title') or base
    m = re.search(r'(20\d\d-\d\d-\d\d)', base) or re.search(r'(20\d\d-\d\d-\d\d)', p)
    day = rec.get('date') or (m.group(1) if m else '')
    if top in NOT_PUBLISHED:
        return top, day, title, NOT_PUBLISHED[top]
    if top == 'research-output':
        return 'KB', day, title, '内部研究产出，不发布'
    if re.match(r'\d{4}-\d\d-\d\d$', top):
        day = top
        if '(audio)' in base:
            return 'Call', day, base.replace('(audio)', '').strip(), None
        if re.match(r'\d{6} - Merit', base):
            mm = re.search(r'\((\d{4}-\d{2}-\d{2})', title)
            return '9K', (mm.group(1) if mm else day), re.sub(r'^\d{6} - ', '', title), None
        return 'Substack', day, title, None
    return TOP.get(top, top or '?'), day, title, None

def near(day, k):
    try:
        d0 = D.fromisoformat(day)
    except ValueError:
        return set()
    return {(d0 + timedelta(i)).isoformat() for i in range(-k, k + 1)}

def keys_for(rec, title):
    """match strings: the title, plus the KB file name (date-prefixed kebab of the original title),
    which survives a weekly that paraphrased or shortened the title"""
    p = rec.get('path') or rec.get('rel') or ''
    base = os.path.basename(p).rsplit('.', 1)[0]
    ks = [norm(re.sub(r'^\d{4}-\d\d-\d\d-', '', title))]
    if re.match(r'\d{4}-\d\d-\d\d-[a-z0-9-]+$', base):
        ks.append(norm(base[11:]))
    return [k for k in dict.fromkeys(ks) if k]

def match(rec, notes, by_key):
    src, day, title, reason = classify(rec)
    if reason:
        return src, day, title, None, reason
    ks = keys_for(rec, title)
    hit = next((by_key[(day, n)] for n in ks if (day, n) in by_key), None)
    if not hit:
        # prefix match (KB file names are cut at ~60 chars; Merit first line vs file name), date +-1;
        # Substack can be re-dated by a few days between folders
        days = near(day, 3 if src == 'Substack' else 1)
        cands = []
        for n in ks:
            k = min(len(n), 18)
            cands += [r for r in notes if r['date'] in days and len(r['n']) >= 6 and r not in cands and
                      (r['n'].startswith(n[:k]) or n.startswith(r['n'][:min(len(r['n']), 18)]))]
        # best = longest common prefix with any key ("调研II" vs "调研III"), then same day
        def lcp(a, b):
            i = 0
            while i < min(len(a), len(b)) and a[i] == b[i]:
                i += 1
            return i
        cands.sort(key=lambda r: (-max(lcp(r['n'], n) for n in ks), r['date'] != day))
        hit = cands[0] if cands else None
    if hit:
        return src, day, title, hit, None
    return src, day, title, None, 'Notes 尚未收录' if src in ('AC', 'TB', 'GP', '9K', 'Substack', 'FUNDA', 'SA', 'Call') else '未发布到 Notes'

TIER = [('A', '核心'), ('B', '实质'), ('C', '提及'), ('S', '口径外')]

def build(repo, all_out, page_rel=None):
    notes = load_notes(repo)
    by_key = {}
    for r in notes:
        by_key.setdefault((r['date'], r['n']), r)
    recs = json.load(open(all_out, encoding='utf-8'))
    recs = recs if isinstance(recs, list) else list(recs.values())
    out, seen = [], set()
    for rec in recs:
        if not isinstance(rec, dict):
            continue
        t = (rec.get('tier') or '').strip()[:1].upper()
        if t == 'X':
            continue
        src, day, title, hit, reason = match(rec, notes, by_key)
        key = hit['slug'] if hit else (day, norm(title))
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(id=rec.get('id', ''), tier=t, src=src, date=day, title=title, hit=hit, reason=reason))
    order = {k: i for i, (k, _) in enumerate(TIER)}
    out.sort(key=lambda r: (order.get(r['tier'], 9), r['date'], r['src']))
    return out

def section(repo, items, page_rel):
    # weekly page is <dir>/index.html; links are relative so they work on Pages and locally
    page_dir = os.path.dirname(page_rel).strip('/')
    up = '../' * len(page_dir.split('/'))
    frm = page_dir + '/'
    linked = sum(1 for r in items if r['hit'])
    lab = dict(TIER)
    rows = []
    for r in items:
        if r['hit']:
            h = r['hit']
            cell = (f'<a href="{up}notes/{h["slug"]}/?from={E(frm)}">{E(h["name"])}</a>'
                    f'<div class="ws-orig">{E(h["orig"])}</div>')
        else:
            cell = f'{E(r["title"])}<div class="ws-orig">无链接：{E(r["reason"])}</div>'
        rows.append(f'<tr id="src-{E(r["id"])}"><td class="small">{lab.get(r["tier"], r["tier"] or "-")}</td>'
                    f'<td class="small num">{E(r["date"][5:])}</td><td class="small">{E(r["hit"]["src"] if r["hit"] else r["src"])}</td>'
                    f'<td class="small">{cell}</td></tr>')
    miss = len(items) - linked
    tail = f'其余 {miss} 篇没有公开页面，列出原因。' if miss else ''
    return '\n'.join([
        START,
        '<div class="weekly-sources">',
        '<style>.weekly-sources .ws-orig{font-size:12.5px;color:var(--faint,#8A887F);margin-top:2px}'
        '.weekly-sources td a{text-decoration:underline;text-underline-offset:2px}'
        '.weekly-sources .ws-note{font-size:13px;color:var(--muted,#5F5E59)}'
        '.weekly-sources td{white-space:nowrap;vertical-align:top}'
        '.weekly-sources td:last-child{white-space:normal;min-width:220px}</style>',
        '<h2 id="weekly-sources">附 本期引用原文</h2>',
        f'<p class="ws-note">本期逐篇阅读的 {len(items)} 篇纪要，{linked} 篇能在 Notes 打开原文。点标题跳转，'
        f'原文页左上角 "返回周报" 或浏览器后退都能回到这里。{tail}</p>',
        '<div class="tbl"><table><thead><tr><th>分级</th><th>日期</th><th>来源</th><th>标题</th></tr></thead><tbody>',
        *rows, '</tbody></table></div>', '</div>', END])

def inject(page_html, sec):
    if START in page_html:
        return re.sub(re.escape(START) + '.*?' + re.escape(END), lambda m: sec, page_html, flags=re.S)
    i = page_html.rfind('<p class="foot">')
    if i < 0:
        # after the last h2's block: before the script that closes the content column
        j = page_html.rfind('<h2')
        i = page_html.find('<script', j)
        k = page_html.rfind('</div></div>', j, i)
        i = k if k > 0 else i
    if i < 0:
        i = page_html.rfind('</body>')
    return page_html[:i] + sec + '\n' + page_html[i:]

if __name__ == '__main__':
    a = sys.argv[1:]
    repo, all_out = a[0], a[1]
    items = build(repo, all_out)
    if '--report' in a:
        from collections import Counter
        print('items', len(items), 'linked', sum(1 for r in items if r['hit']))
        print(Counter(r['reason'] for r in items if not r['hit']))
        for r in items:
            if not r['hit']:
                print(' -', r['date'], r['src'], r['title'][:70], '|', r['reason'])
        sys.exit()
    page_rel = a[2]
    sec = section(repo, items, page_rel)
    if '--html' in a:
        open(a[a.index('--html') + 1], 'w', encoding='utf-8').write(sec)
    else:
        p = os.path.join(repo, page_rel)
        page = open(p, encoding='utf-8').read()
        open(p, 'w', encoding='utf-8').write(inject(page, sec))
    print('sources', len(items), 'linked', sum(1 for r in items if r['hit']))
