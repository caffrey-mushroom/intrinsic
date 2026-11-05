"""Build map/data.json for The Map from the model folder.

Usage: python3 tools/the-map/build_map.py <model_dir> [--out map/data.json]

<model_dir> holds Map_Model_*.xlsx (newest wins) plus any other model whose
workbook has an `Export` tab (id | year | metric | value). Export rows from
other files override the Map Model's own Output for the same id/year/metric;
files are applied in name order, so a company model beats the base table.
"""
import argparse, glob, json, os, re, subprocess, sys, datetime
from collections import defaultdict
import openpyxl

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LAYERS = [('ent','Enterprise','用 token 的企业和应用'),('lab','Labs','把算力变成 token'),('cloud','Cloud','CapEx 和机房'),
          ('power','Power','电和机房设备'),('chip','卡 / 存储 / 光','算力硬件'),('fab','Foundry','晶圆制造'),('cap','SemiCap','设备'),
          ('odm','Servers','服务器'),('pkg','Packaging','封测 / PCB'),('grid','Grid','电力零部件'),('sub','Subsystems','设备零部件'),('mat','Materials','材料')]
YEARS = [2025, 2026, 2027, 2028]

def values(path):
    """Open with cached values; recalculate through LibreOffice if the file has never been calculated."""
    wb = openpyxl.load_workbook(path, data_only=True)
    if 'Output' in wb.sheetnames and wb['Output']['J9'].value is None:
        recalc = next((p for p in glob.glob('/mnt/skills/public/xlsx/scripts/recalc.py') + glob.glob('/root/.claude/skills/**/xlsx/scripts/recalc.py', recursive=True)), None)
        if not recalc: sys.exit(f'{path} has no cached values; open and save it in Excel first')
        subprocess.run([sys.executable, recalc, path, '120'], check=True, capture_output=True)
        wb = openpyxl.load_workbook(path, data_only=True)
    return wb

def rows(ws, start, ncol):
    for r in ws.iter_rows(min_row=start, max_col=ncol, values_only=True):
        if any(v is not None for v in r): yield r

def shares(ws):
    """Sell / Buy tab -> {wallet: {id: [bn usd per year]}}."""
    out = defaultdict(dict)
    for r in rows(ws, 9, 19):
        w, i = r[1], r[7]
        if w and i: out[w][i] = [float(x or 0) for x in r[15:19]]
    return out

def match_site(nodes):
    """Attach research / notes pages on the site that mention each node."""
    try:
        h = open(os.path.join(ROOT, 'research/index.html')).read()
    except OSError:
        return
    res = []
    for href, body in re.findall(r'<a class="row[^"]*" href="\./([^"]+)">(.*?)</a>', h, re.S):
        name = re.search(r'class="name">(.*?)</div>', body, re.S); kick = re.search(r'class="kick[^"]*">(.*?)</div>', body, re.S)
        tags = re.search(r'class="tags">(.*?)</div>', body, re.S)
        res.append((href, re.sub('<.*?>', '', name.group(1)) if name else '', kick.group(1)[:10] if kick else '',
                    set(re.findall(r'[a-z0-9]+', ((tags.group(1) if tags else '') + ' ' + href).lower()))))
    nd = os.path.join(ROOT, 'notes')
    notes = sorted([d for d in os.listdir(nd) if re.match(r'\d{4}-', d) and os.path.isdir(os.path.join(nd, d))], reverse=True)
    ambiguous = {'now','team','net','be','ge','dt','tel','lam','fn','applied','tokyo','hybrid','together','cat','sec','arm','meta','lite','cursor','delta','ase','emc','su','vat','tok','lin','ter','advanced','ultra','hon','ai'}
    for n in nodes:
        kw = {k.lower() for k in n.pop('kw')}
        n['res'] = [[h_, nm, k] for h_, nm, k, toks in res if kw & toks][:12]
        n['nres'] = sum(1 for *_, toks in res if kw & toks)
        nk = kw - ambiguous
        ns = [d for d in notes if nk & set(d.lower().replace('podcast-intel', 'podcast').split('-'))]
        n['nnotes'] = len(ns)
        n['notes'] = [[d, re.sub(r'^\d{4}-\d{2}-\d{2}-', '', d).replace('-', ' '), d[:10].replace('-', '.')] for d in ns[:8]]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('model_dir'); ap.add_argument('--out', default=os.path.join(ROOT, 'map/data.json'))
    a = ap.parse_args()
    files = sorted(glob.glob(os.path.join(a.model_dir, '*.xlsx')))
    base = sorted([f for f in files if os.path.basename(f).startswith('Map_Model')])
    if not base: sys.exit('no Map_Model_*.xlsx in ' + a.model_dir)
    base = base[-1]
    wb = values(base)

    nodes = []
    for r in rows(wb['Nodes'], 7, 8):
        _, i, sec, g, layer, priv, mc, role = r
        if not i: continue
        kw = [str(i)] + [w for w in re.findall(r'[A-Za-z][A-Za-z0-9]+', str(role or '')) if len(w) > 3]
        nodes.append(dict(id=str(i), sec=sec, g=g, layer=layer, priv=bool(priv), mc=float(mc or 0), role=role or '', kw=kw))
    ids = {n['id'] for n in nodes}
    links = [dict(s=r[1], t=r[2], l=r[3] or '') for r in rows(wb['Links'], 7, 4) if r[1] and r[2]]

    metric = defaultdict(lambda: defaultdict(dict))   # id -> metric -> year -> value
    sources = {}
    for f in [base] + [f for f in files if f != base and not os.path.basename(f).startswith('Map_Model')]:
        w = wb if f == base else openpyxl.load_workbook(f, data_only=True, read_only=True)
        if 'Export' not in w.sheetnames: continue
        for r in w['Export'].iter_rows(min_row=2, max_col=4, values_only=True):
            i, y, m, v = r
            if i in ids and isinstance(y, (int, float)) and isinstance(v, (int, float)):
                metric[i][m][int(y)] = round(float(v), 2)
        sources[os.path.basename(f)] = 'Export'

    sell, buy = shares(wb['Sell']), shares(wb['Buy'])
    flow = defaultdict(lambda: [0.0] * 4)              # (buyer, seller) -> bn usd per year, summed over wallets
    for w, s in sell.items():
        tot = [sum(v[k] for v in s.values()) for k in range(4)]
        for b, bv in buy.get(w, {}).items():
            for t, sv in s.items():
                if b == t: continue
                f = flow[(b, t)]
                for k in range(4):
                    if tot[k]: f[k] += bv[k] * sv[k] / tot[k]
    for l in links:
        f = flow.get((l['s'], l['t']))
        if f and max(f) > 0.05: l['f'] = [round(x, 2) for x in f]
    pairs = {(l['s'], l['t']) for l in links}
    for n in nodes:
        m = metric.get(n['id'], {})
        n['rev'] = [m.get('AI Revenue', {}).get(y, 0) for y in YEARS]
        n['spend'] = [m.get('AI Spend', {}).get(y, 0) for y in YEARS]
        ins = sorted([(b, f) for (b, t), f in flow.items() if t == n['id'] and (b, t) in pairs], key=lambda x: -x[1][2])[:6]
        outs = sorted([(t, f) for (b, t), f in flow.items() if b == n['id'] and (b, t) in pairs], key=lambda x: -x[1][2])[:6]
        n['fin'] = [[b, [round(x, 1) for x in f]] for b, f in ins if max(f) > 0.05]
        n['fout'] = [[t, [round(x, 1) for x in f]] for t, f in outs if max(f) > 0.05]
    match_site(nodes)

    issues = []
    for r in rows(wb['Check'], 9, 13):
        if r[2] and any(isinstance(x, (int, float)) and x and abs(x - 1) > 0.001 for x in r[9:13]): issues.append(r[2])
    unknown = sorted(({l['s'] for l in links} | {l['t'] for l in links}) - ids)
    if unknown: issues.append('unknown ids in Links: ' + ', '.join(unknown))

    groups = sorted({(n['g'], n['layer']) for n in nodes})
    data = dict(years=YEARS, built=datetime.date.today().isoformat(), model=os.path.basename(base), sources=sorted(sources), issues=issues,
                layers=[dict(id=a_, name=b_, sub=c_) for a_, b_, c_ in LAYERS], groups=[dict(id=g, layer=l) for g, l in groups],
                nodes=nodes, links=links)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(data, open(a.out, 'w'), ensure_ascii=False, separators=(',', ':'))
    print(f'{a.out}: {len(nodes)} nodes, {len(links)} links, {sum(1 for l in links if "f" in l)} with flows; issues: {issues or "none"}')

if __name__ == '__main__':
    main()
