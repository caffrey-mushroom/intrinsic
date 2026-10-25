"""Write note pages + update notes/index.html and the home Notes block (handover sec. 5/7).
usage: render.py <repo_root> <records.json> <meta.json>   (meta: [{id,name,sector,tags}])
"""
import os, re, sys, json, html, shutil
repo, rec_f, meta_f = sys.argv[1:4]
recs = {r['id']: r for r in json.load(open(rec_f))}
meta = {m['id']: m for m in json.load(open(meta_f))}
E = lambda s: html.escape(s, quote=False)

SRC_META = {'AC': 'AceCamp', 'TB': 'Third Bridge', 'GP': 'GuidePoint', '9K': 'Meritco 久谦',
            'Substack': 'Substack', 'FUNDA': 'Funda', 'SA': 'SemiAnalysis', 'Call': 'Expert Call'}
SRC_SLUG = {'AC': 'ac', 'TB': 'tb', 'GP': 'gp', '9K': '9k', 'Substack': 'substack', 'FUNDA': 'funda', 'SA': 'sa', 'Call': 'call'}
SRC_ORDER = ['AC', 'TB', 'GP', '9K', 'Call', 'Substack', 'FUNDA', 'SA', 'Weekly']
ROMAN = re.compile(r'\b(i{1,3}|iv|v|vi{1,3}|ix|x)\b')

def kebab(name):
    s = name.lower().replace('&', ' ').replace('.', '-')
    s = re.sub(r"['’]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    return re.sub(r'-+', '-', s)

tpl = open(f'{repo}/notes/2026-09-29-ac-supernode-bottlenecks-pt-2/index.html', encoding='utf-8').read()
head = tpl[:tpl.index('<title>')] + '<title>{title}</title>' + tpl[tpl.index('</title>') + 8:tpl.index('<body>') + 6]

# PDF-sourced notes (FUNDA/SA) embed the original PDF instead of extracted text
PDF_CSS = '''<style>
.pdfwrap{margin-top:var(--s4); padding-top:var(--s3); border-top:var(--hair)}
.pdfbar{display:flex; gap:var(--s3); font-size:13.5px; margin-bottom:var(--s2)} .pdfbar a{color:var(--muted)}
.pdfwrap iframe{display:block; width:100%; height:calc(100vh - 120px); min-height:640px; border:var(--hair); background:#fff}
.pdfwrap .note{font-size:13px; color:var(--faint); margin-top:var(--s1)}
</style>'''
PDF_BODY = ('<div class="pdfwrap"><div class="pdfbar"><a href="doc.pdf" target="_blank" rel="noopener">在新窗口打开 PDF</a>'
            '<a href="doc.pdf" download>下载</a></div><iframe src="doc.pdf#view=FitH&amp;toolbar=1" title="PDF 原文"></iframe>'
            '<p class="note">手机浏览器若只显示第一页，点上面"在新窗口打开 PDF"。</p></div>')

existing = set(d for d in os.listdir(f'{repo}/notes') if os.path.isdir(f'{repo}/notes/{d}'))
new_rows = []
for i, r in sorted(recs.items(), key=lambda kv: (kv[1]['date'], kv[1].get('time', ''))):
    m = meta[i]
    name, sector, tags = m['name'].strip(), m['sector'].strip(), m['tags'].strip()
    slug = f"{r['date']}-{SRC_SLUG[r['src']]}-{kebab(name)}"
    base, n = slug, 2
    while slug in existing:
        slug = f'{base}-{n}'; n += 1
    existing.add(slug)
    d = r['date'].replace('-', '.')
    mt = f"{SRC_META[r['src']]} · {r['date']}"
    if r['src'] == 'AC':
        if r.get('time'):
            mt += ' ' + r['time']
        if r.get('article'):
            mt += f" · article {r['article']}"
    title = f"{d} | {r['src']} | {sector} | {name}"
    is_pdf = r['path'].lower().endswith('.pdf')
    h0 = head.replace('</head>', PDF_CSS + '</head>') if is_pdf else head
    body = [PDF_BODY] if is_pdf else ['<div class="body">', r['body'], '</div>']
    page = h0.replace('{title}', E(title)) + '\n' + '\n'.join([
        '<div class="backrow"><a class="back" href="../" aria-label="返回 Notes">←&#8201;返回</a></div>',
        '<main class="page">',
        f'<h1>{E(title)}</h1>',
        f'<p class="orig">原标题：{E(r["orig"])}</p>',
        f'<p class="tags">{E(tags)}</p>',
        f'<p class="meta">{E(mt)}</p>',
        *body, '</main>', '</body></html>', ''])
    os.makedirs(f'{repo}/notes/{slug}')
    if is_pdf:
        shutil.copyfile(r['path'], f'{repo}/notes/{slug}/doc.pdf')
    open(f'{repo}/notes/{slug}/index.html', 'w', encoding='utf-8').write(page)
    row = (f'    <a class="row" href="./{slug}/">\n      <div>\n'
           f'        <div class="kick num">{d} · {r["src"]} · {E(sector)}</div>\n'
           f'        <div class="name">{E(name)}</div>\n'
           f'        <div class="desc">{E(r["orig"])}</div>\n'
           f'        <div class="tags">{E(tags)}</div>\n'
           f'        <div class="meta">{E(mt)}</div>\n      </div>\n    </a>\n')
    new_rows.append(row)

# ---- list page: merge and sort all rows
p = f'{repo}/notes/index.html'
idx = open(p, encoding='utf-8').read()
anchor = re.search(r'(<div class="list" id="notes"[^>]*>\s*<p class="empty"[^>]*>[^<]*</p>\n)', idx)
start = anchor.end()
end_m = re.compile(r'    </a>\n(?!    <a class="row")').search(idx, start)
old_block = idx[start:end_m.end()]
old_rows = re.findall(r'    <a class="row" href=.*?    </a>\n', old_block, re.S)
rows = old_rows + new_rows
def key(row):
    d = re.search(r'kick num">(\S+) · (\S+)', row)
    t = re.search(r'class="meta">[^<]*?\d{4}-\d{2}-\d{2} (\d{2}:\d{2})', row)
    src = d.group(2)
    so = SRC_ORDER.index(src) if src in SRC_ORDER else 99
    # newest date first; timed entries latest first; untimed after, by source
    return (d.group(1), 1 if t else 0, t.group(1) if t else '', -so)
rows.sort(key=key, reverse=True)
idx = idx[:start] + ''.join(rows) + idx[end_m.end():]
open(p, 'w', encoding='utf-8').write(idx)

# ---- home page Notes block
names = re.findall(r'<div class="name">(.*?)</div>', ''.join(rows[:2]))
d0 = re.search(r'kick num">(\S+)', rows[0]).group(1)
total = len([d for d in os.listdir(f'{repo}/notes') if os.path.isdir(f'{repo}/notes/{d}')])
hp = f'{repo}/index.html'
h = open(hp, encoding='utf-8').read()
h = re.sub(r'(<a class="row" href="\./notes/">\s*<div><div class="name">全部 notes</div><div class="desc">)最新：.*?(</div></div>\s*<div class="side">)\d+ 篇',
           lambda m: f'{m.group(1)}最新：{names[0]}、{names[1]} ({d0}){m.group(2)}{total} 篇', h, flags=re.S)
open(hp, 'w', encoding='utf-8').write(h)
print('pages', len(new_rows), 'rows', len(rows), 'dirs', total)
