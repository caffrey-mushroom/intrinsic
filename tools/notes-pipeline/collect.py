"""Collect staged Knowledge Base files -> records.json (handover sec. 2/4/8).
usage: collect.py <kb_root> <repo_root> <since YYYY-MM-DD> <new_src_since YYYY-MM-DD> <ac_times.json> <out.json>
"""
import os, re, sys, json, glob, html, subprocess
sys.path.insert(0, os.path.dirname(__file__))
from md2html import md_to_html, pdftext_to_html

kb, repo, since, new_since, times_f, out_f = sys.argv[1:7]
ac_times = json.load(open(times_f)) if os.path.exists(times_f) else {}
# AceCamp publish times also come from any staged mirror files
for _p in glob.glob(f'{kb}/acecamp 2/*/*.md'):
    _h = open(_p, encoding='utf-8', errors='replace').read(800)
    _a = re.search(r'articleId:\s*(\d+)', _h); _t = re.search(r'时间:\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})', _h)
    if _a and _t:
        ac_times.setdefault(_a.group(1), _t.group(1))
_CONF = re.compile(r' \d+(\.md)$')
class _Conf:
    # a Nutstore conflict copy is "name N.md" whose sibling "name.md" exists
    def search(self, p):
        m = _CONF.search(p)
        return bool(m) and os.path.exists(p[:m.start()] + m.group(1))
CONF = _Conf()
MONTHS = dict(January=1, February=2, March=3, April=4, May=5, June=6, July=7, August=8, September=9, October=10, November=11, December=12)

def norm(s):
    return re.sub(r'[^0-9a-z一-鿿]', '', html.unescape(s).lower())

def read(p):
    return open(p, encoding='utf-8', errors='replace').read()

def front(t):
    fm = {}
    if t.startswith('---\n'):
        end = t.find('\n---', 4)
        for l in t[4:end].split('\n'):
            m = re.match(r'(\w+):\s*(.*)', l)
            if m:
                fm[m.group(1)] = m.group(2).strip().strip('"')
        t = t[end + 4:].lstrip('\n')
    return fm, t

def strip_header(t, title):
    lines = t.split('\n')
    # drop leading "# title"
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r'^#\s+', lines[0]) and norm(lines[0][1:])[:20] == norm(title)[:20]:
        lines.pop(0)
    # drop **key:** value header block (multi-line values allowed) up to first --- rule
    out, i, in_hdr = [], 0, True
    while i < len(lines):
        s = lines[i].strip()
        if in_hdr and re.match(r'^\*\*[^*]{1,12}[:：]\*\*', s):
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r'^\*\*[^*]{1,12}[:：]\*\*', lines[i].strip()) and not re.fullmatch(r'-{3,}', lines[i].strip()):
                i += 1
            continue
        if in_hdr and s and not re.fullmatch(r'-{3,}', s):
            in_hdr = False
        out.append(lines[i]); i += 1
    return '\n'.join(out)

JUNK = re.compile(r'^(\[?view in browser|forwarded this email|read in app|subscribe|share|like|comment|restack|\[?\s*\]?$)', re.I)
FOOTER = re.compile(r'^(subscription information|unsubscribe|you received this|\\?©|copyright ©|manage your subscription)', re.I)
def unwrap_email(t, title):
    out = []
    for l in t.split('\n'):
        s = l.strip()
        if s.startswith('@media') or s.startswith('.msg-') or re.fullmatch(r'\|?(\s*:?-{3,}:?\s*\|)+\s*', s):
            out.append(''); continue
        if s.startswith('|'):
            cells = [x.strip() for x in s.strip('|').split('|') if x.strip()]
            for x in cells:
                out += [x, '']
            continue
        out.append(l)
    keep = []
    for l in out:
        s = l.strip()
        if FOOTER.match(re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)):
            break
        if s.startswith('#') and norm(s)[:20] == norm(title)[:20]:
            continue
        txt = s
        for _ in range(2):
            txt = re.sub(r'!?\[([^\]]*)\]\([^)]*\)', r'\1', txt)
        txt = txt.strip()
        if s and (txt in ('∙', 'Paid') or (JUNK.match(txt) and len(txt) < 40 and (not txt or '![' not in s or txt.lower() in ('like', 'comment', 'restack', 'share')))):
            continue
        keep.append(l)
    return '\n'.join(keep)

recs = []
def add(**r):
    recs.append(r)

# ---- source folders with front matter
FOLDERS = {'Acecamp': 'AC', 'ThirdBridge': 'TB', 'GuidePoint': 'GP', 'MeritForum': '9K', 'Substack': 'Substack'}
ac_ids = set()
for d, src in FOLDERS.items():
    for p in sorted(glob.glob(f'{kb}/{d}/*/*.md')):
        if CONF.search(p):
            continue
        fm, body = front(read(p))
        date = fm.get('date', '')[:10]
        if not date or date < since:
            continue
        title = fm.get('title', '')
        extra = {}
        if src == 'AC':
            m = re.search(r'article/(\d+)', fm.get('url', ''))
            if m:
                extra['article'] = m.group(1); ac_ids.add(m.group(1))
        body = strip_header(body, title)
        if src == 'GP':
            # GP repeats the (wrapped) title as the first lines
            ls = body.split('\n'); acc = ''
            for k, l in enumerate(ls[:6]):
                acc += l.strip()
                if norm(acc) == norm(title):
                    body = '\n'.join(ls[k + 1:]); break
            body = body.replace('SU MMARY', 'SUMMARY')
        add(src=src, date=date, orig=title, path=p, md=body, **extra)

# ---- acecamp mirror: only ids not in Acecamp/
for p in sorted(glob.glob(f'{kb}/acecamp 2/*/*.md')):
    if CONF.search(p):
        continue
    t = read(p)
    m = re.search(r'articleId:\s*(\d+)', t)
    if not m or m.group(1) in ac_ids:
        continue
    ac_ids.add(m.group(1))
    tm = re.search(r'时间:\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})', t)
    title = re.search(r'^#\s+(.*)', t, re.M).group(1).strip()
    date = tm.group(1) if tm else os.path.basename(os.path.dirname(p))
    if date < since:
        continue
    body = re.sub(r'^#\s+.*\n', '', t, count=1)
    body = re.sub(r'## 文章信息\n.*?(?=\n## )', '', body, flags=re.S)
    add(src='AC', date=date, orig=title, path=p, md=body, article=m.group(1), time=tm.group(2) if tm else '')

# ---- top-level date folders: Merit audio (9K), own expert calls (Call) and Substack copies not in Substack/
sub_norm = {}
for r in recs:
    if r['src'] == 'Substack':
        sub_norm.setdefault(r['date'], []).append(norm(r['orig']))
for p in sorted(glob.glob(f'{kb}/20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]/*.md')):
    if CONF.search(p):
        continue
    day = os.path.basename(os.path.dirname(p)); name = os.path.basename(p)[:-3]
    if '(audio)' in name:
        # own expert calls: any date (the published-list dedupe skips repeats)
        t = read(p)
        first, _, rest = t.partition('\n')
        orig = name.replace('(audio)', '').strip() or first.strip()
        add(src='Call', date=day, orig=orig, path=p, md=rest, top=1)
        continue
    if day < since:
        continue
    t = read(p)
    if re.match(r'\d{6} - Merit', name):
        first = t.split('\n', 1)[0].strip()
        orig = re.sub(r'^\d{6} - ', '', first)
        m = re.search(r'\((\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?', first)
        add(src='9K', date=m.group(1) if m else day, time=(m.group(2) or '') if m else '', orig=orig, path=p, md=t.split('\n', 1)[1], top=1)
        continue
    m = re.search(r'^#\s+(.*)', t, re.M)
    title = m.group(1).strip() if m else name
    if title in ('音频信息', '纪要总结', '音频纪要总结'):
        first = t.split('\n', 1)[0].strip()
        title = first if first and not first.startswith('#') else name
        t = t.split('\n', 1)[1] if first == title else t
    n = norm(title)[:25]
    from datetime import date as D, timedelta
    d0 = D.fromisoformat(day)
    if any(s.startswith(n) or n.startswith(s[:25]) for k in (d0, d0 - timedelta(1), d0 + timedelta(1)) for s in sub_norm.get(k.isoformat(), [])):
        continue
    body = unwrap_email(t, title)
    add(src='Substack', date=day, orig=title, path=p, md=body, top=1)

# ---- Funda (md + pdf) and SemiAnalysis (pdf), filtered by publish date >= new_since
def pdf_text(p):
    return subprocess.run(['pdftotext', p, '-'], capture_output=True, text=True).stdout

def en_date(s):
    m = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(20\d\d)', s)
    return '%s-%02d-%02d' % (m.group(3), MONTHS[m.group(1)], int(m.group(2))) if m else ''

for p in sorted(glob.glob(f'{kb}/Funda/*')) + sorted(glob.glob(f'{kb}/SemiAnalysis/*')):
    src = 'FUNDA' if '/Funda/' in p else 'SA'
    base = os.path.basename(p)
    if p.endswith('.pdf'):
        txt = pdf_text(p)
        first = txt[:1500]
        date = en_date(first)
        title = re.sub(r'^\[FUNDA\]\s*', '', base[:-4]).strip()
        lines = [l for l in txt.split('\n')]
        add(src=src, date=date, orig=title, path=p, pdf=txt)
    elif p.endswith('.md'):
        t = read(p)
        m = re.match(r'(\d{8})\s+(.*)\.md$', base)
        if m:
            date = '%s-%s-%s' % (m.group(1)[:4], m.group(1)[4:6], m.group(1)[6:]); title = m.group(2)
        else:
            date = en_date(t[:400]) or ''
            mm = re.search(r'([A-Z][a-z]{2}) (\d{1,2}), (20\d\d)', t[:400])
            if not date and mm:
                mon = {k[:3]: v for k, v in MONTHS.items()}[mm.group(1)]
                date = '%s-%02d-%02d' % (mm.group(3), mon, int(mm.group(2)))
            title = base[:-3]
        _, t = front(t)   # web-clipper front matter
        t = re.sub(r'^\s*#\s+.*\n', '', t, count=1)
        add(src=src, date=date, orig=title, path=p, md=t)
recs = [r for r in recs if r['src'] not in ('FUNDA', 'SA') or (r['date'] and r['date'] >= new_since)]

# Funda substack posts also land in Substack/: keep the Substack copy
sub_all = [norm(r['orig']) for r in recs if r['src'] == 'Substack']
def funda_dup(r):
    n = norm(re.sub(r'^Deep\s*-\s*', 'Deep', r['orig']))[:12]
    return any(n and n in s for s in sub_all)
recs = [r for r in recs if not (r['src'] == 'FUNDA' and funda_dup(r))]

# ---- dedupe within batch (same title + date) and against the published list
pub = set()
idx = read(f'{repo}/notes/index.html')
for d, o in re.findall(r'<div class="kick num">(\S+) ·.*?<div class="desc">(.*?)</div>', idx, re.S):
    pub.add((d.replace('.', '-'), norm(o)))
seen, final, skipped = set(), [], 0
for r in recs:
    if r['src'] == 'AC' and not r.get('time'):
        t = ac_times.get(r.get('article', ''), '')
        if t[:10] == r['date']:
            r['time'] = t[11:16]
    k = (r['date'], norm(r['orig']))
    if k in pub:
        skipped += 1; continue
    if k in seen:
        continue
    seen.add(k); final.append(r)

# body html + excerpt for metadata
for i, r in enumerate(final):
    r['id'] = i
    if 'pdf' in r:
        r['body'] = pdftext_to_html(r.pop('pdf'))
    else:
        r['body'] = md_to_html(r.pop('md'), qq_quotes=(r['src'] == 'AC'))
    r['excerpt'] = re.sub(r'<[^>]+>', ' ', r['body'])[:1200]
json.dump(final, open(out_f, 'w'), ensure_ascii=False)
from collections import Counter
print('records', len(final), 'skipped-published', skipped)
print(Counter((r['src']) for r in final))
print(sorted(Counter(r['date'] for r in final).items()))
