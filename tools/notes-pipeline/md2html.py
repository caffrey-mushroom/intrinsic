"""Markdown / PDF-text -> Notes body HTML (handover sec. 6). Stdlib only."""
import re, html

CJK = re.compile(r'[　-鿿＀-￯]')
CSS_LINE = re.compile(r'^\s*(@media|@font-face|\.[\w-]+[^{}]*\{|[\w.#:\-\s,>()*\[\]="]+\{[^}]*\}|\}|</?style)', re.I)
FURNITURE = [
    re.compile(r'^\s*confidential\s*$', re.I),
    re.compile(r'^\s*(page\s*)?\d+\s*(of\s*\d+)?\s*$', re.I),
    re.compile(r'^\s*\d{1,2}:\d{2}(:\d{2})?\s*$'),
    re.compile(r'^\s*-\s*\d+\s*-\s*$'),
]

def join_lines(lines):
    out = ''
    for l in lines:
        l = l.strip()
        if not l:
            continue
        if not out:
            out = l
        elif CJK.search(out[-1]) or CJK.search(l[0]) or out.endswith(('/', '-', '=', '?', '&', '_')) and re.search(r'https?://\S*$', out):
            out += l
        else:
            out += ' ' + l
    return out

def fix_urls(s):
    s = re.sub(r'\s+"[^"]*"\s*\)', ')', s)   # drop link/image titles
    # rejoin URLs broken across lines inside ](...)
    return re.sub(r'\]\(([^)]*)\)', lambda m: '](' + re.sub(r'\s+', '', m.group(1)) + ')', s)

def img_tag(url):
    url = url.strip()
    if url.startswith('http://mw-meeting.oss'):
        url = 'https://' + url[7:]
    return '<img src="%s" alt="" loading="lazy">' % html.escape(url, quote=True)

def inline(s):
    s = fix_urls(s)
    imgs = []
    def keep_img(m):
        imgs.append(img_tag(m.group(1)))
        return '\x00%d\x00' % (len(imgs) - 1)
    s = re.sub(r'\[!\[[^\]]*\]\(([^)\s]+)[^)]*\)\]\([^)]*\)', keep_img, s)
    s = re.sub(r'!\[[^\]]*\]\(([^)\s]+)[^)]*\)', keep_img, s)
    s = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', s)          # links -> text
    s = re.sub(r'\]\(https?://[^)\s]*\)', '', s)              # tail of a link opened in an earlier paragraph
    s = re.sub(r'^\[(?=\S)', '', s)
    s = re.sub(r'<(https?://[^>]+)>', r'\1', s)
    s = re.sub(r'<br\s*/?>', ' ', s, flags=re.I)
    s = re.sub(r'</?(span|div|font|u|sup|sub|a)[^>]*>', '', s, flags=re.I)
    s = html.escape(s, quote=False)
    s = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'__(.+?)__', r'<b>\1</b>', s)
    s = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<i>\1</i>', s)
    s = s.replace('**', '')
    s = re.sub(r'<b>\s*</b>', '', s)
    s = re.sub('\x00(\\d+)\x00', lambda m: imgs[int(m.group(1))], s)
    return s.strip()

def strip_bold(s):
    return re.sub(r'^\*\*(.*)\*\*$', r'\1', s.strip()).replace('**', '').strip()

def is_table_row(l):
    return l.strip().startswith('|') and l.strip().count('|') >= 2

def table_html(rows):
    cells = [[c.strip() for c in r.strip().strip('|').split('|')] for r in rows]
    sep = [i for i, r in enumerate(cells) if all(re.fullmatch(r':?-{2,}:?', c) or c == '' for c in r) and any(c for c in r)]
    head = None
    if sep and sep[0] == 1:
        head = cells[0]
        body = [r for i, r in enumerate(cells) if i > 1]
    else:
        body = [r for i, r in enumerate(cells) if i not in sep]
    h = ['<div class="tbl"><table class="t wrap">']
    if head:
        h.append('<thead><tr>' + ''.join('<th>%s</th>' % inline(c) for c in head) + '</tr></thead>')
    h.append('<tbody>' + ''.join('<tr>' + ''.join('<td>%s</td>' % inline(c) for c in r) + '</tr>' for r in body) + '</tbody>')
    h.append('</table></div>')
    return ''.join(h)

LIST_RE = re.compile(r'^(\s*)([-*+•]|\d+[.)])\s+(.*)$')

def collapse_links(md):
    # keep multi-line [text](url "title") constructs on one line so wrapped text is not read as list/heading
    md = re.sub(r'\]\([^()]*?\)', lambda m: m.group(0).replace('\n', ' ') if '\n' in m.group(0) else m.group(0), md)
    md = re.sub(r'\[([^\[\]]*?)\]\(', lambda m: '[' + m.group(1).replace('\n', ' ') + '](', md)
    md = re.sub(r'\[!\[([^\[\]]*?)\]', lambda m: '[![' + m.group(1).replace('\n', ' ') + ']', md)
    md = re.sub(r'^\[(#{1,6} )', r'\1', md, flags=re.M)
    return md

def md_to_html(md, qq_quotes=False, numbered_lists=True):
    md = collapse_links(md.replace('\r\n', '\n').replace('\r', '\n'))
    lines = md.split('\n')
    out, para, i = [], [], 0
    def flush():
        if para:
            t = inline(join_lines(para))
            if t:
                if re.fullmatch(r'(<img [^>]+>\s*)+', t):
                    out.append('<p>%s</p>' % t)
                else:
                    out.append('<p>%s</p>' % t)
            para.clear()
    while i < len(lines):
        l = lines[i]
        s = l.strip()
        if not s:
            flush(); i += 1; continue
        if CSS_LINE.match(s) or any(f.match(s) for f in FURNITURE) or re.fullmatch(r'[-*_]{3,}', s):
            flush(); i += 1; continue
        m = re.match(r'^(#{1,6})\s+(.*)$', s)
        if m:
            flush()
            txt = inline(strip_bold(m.group(2)))
            if txt:
                tag = 'h2' if len(m.group(1)) <= 2 else 'h3'
                out.append('<%s>%s</%s>' % (tag, txt, tag))
            i += 1; continue
        if is_table_row(s):
            flush()
            rows = []
            while i < len(lines) and is_table_row(lines[i]):
                rows.append(lines[i]); i += 1
            out.append(table_html(rows)); continue
        if s.startswith('>'):
            flush()
            q = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                q.append(lines[i].strip().lstrip('>').strip()); i += 1
            # split on blank quote lines
            chunk = []
            for x in q + ['']:
                if x:
                    chunk.append(x)
                elif chunk:
                    t = inline(join_lines(chunk))
                    if qq_quotes:
                        t = re.sub(r'^<b>(.*)</b>$', r'\1', t)
                        out.append('<p class="qq">%s</p>' % t)
                    else:
                        out.append('<p>%s</p>' % t)
                    chunk = []
            continue
        m = LIST_RE.match(l)
        if m and m.group(2)[0].isdigit() and not numbered_lists:
            m = None
        if m:
            flush()
            ordered = m.group(2)[0].isdigit()
            items = []
            while i < len(lines):
                mm = LIST_RE.match(lines[i])
                if mm and (mm.group(2)[0].isdigit()) == ordered:
                    items.append([mm.group(3)]); i += 1
                elif lines[i].strip() and items and not LIST_RE.match(lines[i]) and lines[i].startswith((' ', '\t')):
                    items[-1].append(lines[i]); i += 1
                else:
                    break
            tag = 'ol' if ordered else 'ul'
            lis = ''.join('<li>%s</li>' % inline(join_lines(it)) for it in items if inline(join_lines(it)))
            if lis:
                out.append('<%s>%s</%s>' % (tag, lis, tag))
            continue
        para.append(l); i += 1
    flush()
    h = '\n'.join(out)
    # list items separated by blank lines come out as separate lists: merge them
    return re.sub(r'</(ul|ol)>\n<\1>', '', h)

def pdftext_to_html(txt):
    """pdftotext output -> paragraphs. Drops repeated header/footer lines and page furniture."""
    pages = txt.split('\f')
    from collections import Counter
    cnt = Counter()
    for p in pages:
        for l in set(x.strip() for x in p.split('\n') if x.strip()):
            cnt[l] += 1
    rep = {l for l, c in cnt.items() if c >= 3 and len(pages) >= 4 and len(l) < 80}
    md = []
    for p in pages:
        for l in p.split('\n'):
            s = l.strip()
            if s in rep or re.fullmatch(r'\d+\s*/\s*\d+', s):
                continue
            s = re.sub(r'\s+\d+\s*/\s*\d+$', '', s)
            md.append(s)
        md.append('')
    # pdf lines: blank line = paragraph break; bullets "•" become list items
    text = '\n'.join(md)
    text = re.sub(r'^[•●▪■◆]\s*', '- ', text, flags=re.M)
    return md_to_html(text, numbered_lists=False)
