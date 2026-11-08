#!/usr/bin/env python3
"""Publish one X Digest edition onto the Mushroom twitter tab.

One public page per Beijing date + edition (am 早报 / pm 晚报).
A newer revision of the same key replaces that page. An older revision
does not. Other dates stay. There is no v1/v2 pair of cards.

  python3 tools/twitter/publish.py <repo> <source.html> \
      --date 2026-11-08 --edition pm --revision 2026-11-08T14:19:37Z

source.html is the digest body only: no mail headers, recipients, or raw message.
"""
import argparse, hashlib, html, json, re, sys
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
LABEL = {"am": "早报", "pm": "晚报"}
PRIVATE_RE = re.compile(
    r"(?i)([\w.+-]+@[\w.-]+\.(?:com|net|org|cn)|mailto:|marswalk)"
)

EDITION_CSS = r"""
:root{
  --bg:#FAF9F5; --hover:#F3F1EA; --soft:#EFEDE6; --rule:#E6E3D9;
  --text:#141413; --muted:#5F5E59; --faint:#8A887F;
  --slate-100:#E3E7ED; --slate-300:#ABB7C8; --slate-500:#7189A7; --slate-600:#5E728D; --navy:#022B46;
  --serif:Newsreader, "Noto Serif SC", "Songti SC", STSong, Georgia, serif;
  --sans:Inter, "PingFang SC", "Noto Sans SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif;
  --fs-display:40px; --fs-title:20px; --fs-body:15px; --fs-note:12.5px;
  --s1:8px; --s2:16px; --s3:24px; --s4:32px; --s6:48px; --s8:64px;
  --hair:1px solid var(--rule); --radius:8px;
}
@media (prefers-color-scheme: dark){ :root:not([data-theme="light"]){
  --bg:#1F1E1D; --hover:#282725; --soft:#2E2D2A; --rule:#3A3935; --text:#F0EEE6; --muted:#B3B0A6; --faint:#85827A;
  --slate-100:#2F3540; --navy:#C8D0DA; color-scheme:dark } }
:root[data-theme="dark"]{
  --bg:#1F1E1D; --hover:#282725; --soft:#2E2D2A; --rule:#3A3935; --text:#F0EEE6; --muted:#B3B0A6; --faint:#85827A;
  --slate-100:#2F3540; --navy:#C8D0DA; color-scheme:dark }
*,*::before,*::after{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);font-size:var(--fs-body);line-height:1.7;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
a{color:var(--slate-600);text-decoration:none} a:hover{text-decoration:underline;text-underline-offset:3px}
:focus-visible{outline:2px solid var(--slate-500);outline-offset:3px;border-radius:4px}
.mbar{position:sticky;top:0;z-index:20;background:color-mix(in srgb, var(--bg) 94%, transparent);backdrop-filter:blur(8px);border-bottom:var(--hair)}
.mbar-in{max-width:1180px;margin:0 auto;padding:0 max(16px, env(safe-area-inset-left, 0px));height:56px;display:flex;align-items:center;gap:16px}
.mark{font-family:var(--serif);font-weight:500;font-size:19px;color:var(--text)}.mark:hover{text-decoration:none}
.back{display:flex;align-items:center;gap:16px;color:var(--muted);white-space:nowrap}.back::after{content:"";width:1px;height:16px;background:var(--rule)}
.back:hover{color:var(--text);text-decoration:none}
.crumb{color:var(--muted);display:flex;align-items:center;gap:16px;white-space:nowrap}.crumb::before{content:"";width:1px;height:16px;background:var(--rule)}
.mbar .sp{flex:1}
.wrap{max-width:1180px;margin:0 auto;display:grid;grid-template-columns:220px minmax(0,1fr);gap:56px;padding:var(--s6) max(16px, env(safe-area-inset-right, 0px)) var(--s8) max(16px, env(safe-area-inset-left, 0px))}
nav.toc{position:sticky;top:96px;align-self:start;font-size:13.5px;max-height:calc(100vh - 120px);overflow:auto}
nav.toc .tl{font-size:var(--fs-note);color:var(--faint);margin-bottom:var(--s1)}
nav.toc a{display:block;color:var(--muted);padding:3px 0 3px 12px;border-left:1px solid transparent;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
nav.toc a.on{color:var(--text);border-left-color:var(--text)}
nav.toc a:hover{text-decoration:none;color:var(--text)}
main{min-width:0;max-width:880px}
h1{font-family:var(--serif);font-weight:500;font-size:var(--fs-display);line-height:1.15;letter-spacing:-.012em;margin:0}
h2{font-family:var(--serif);font-weight:500;font-size:var(--fs-title);line-height:1.35;margin:var(--s6) 0 0;padding-top:var(--s3);border-top:var(--hair)}
h3,h4{font-family:var(--sans);font-weight:600;font-size:var(--fs-body);line-height:1.5;margin:var(--s3) 0 var(--s1)}
.meta{font-size:var(--fs-note);color:var(--muted);margin:var(--s1) 0 0}
.lede{color:var(--muted);margin:var(--s2) 0 0;max-width:72ch}
article.post{padding:var(--s3) 0;border-top:var(--hair)}
article.post h4{margin-top:0}
p{margin:0 0 .9em;max-width:74ch}
article.post img,main img{display:block;max-width:100%;height:auto;margin:var(--s2) 0;border-radius:var(--radius)}
@media (max-width:1100px){.wrap{grid-template-columns:minmax(0,1fr)} nav.toc{display:none} main{max-width:880px}}
@media (max-width:760px){:root{--fs-display:32px}.wrap{padding:var(--s4) var(--s2) var(--s6)} h3,h4{font-weight:600}}
"""

INDEX_CSS = r"""
:root{
  --bg:#FAF9F5; --hover:#F3F1EA; --soft:#EFEDE6; --rule:#E6E3D9;
  --text:#141413; --muted:#5F5E59; --faint:#8A887F;
  --slate-500:#7189A7;
  --serif:Newsreader, "Noto Serif SC", "Songti SC", STSong, Georgia, serif;
  --sans:Inter, "PingFang SC", "Noto Sans SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif;
  --fs-display:40px; --fs-title:20px; --fs-body:15px; --fs-note:12.5px;
  --s1:8px; --s2:16px; --s3:24px; --s4:32px; --s6:48px; --s8:64px;
  --radius:8px; --hair:1px solid var(--rule);
}
*,*::before,*::after{box-sizing:border-box}
html{background:var(--bg)}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);font-size:var(--fs-body);line-height:1.7;-webkit-font-smoothing:antialiased}
a{color:inherit;text-decoration:none}
:focus-visible{outline:2px solid var(--slate-500);outline-offset:3px;border-radius:4px}
.mbar{position:sticky;top:0;z-index:20;background:rgba(250,249,245,.94);backdrop-filter:blur(8px);border-bottom:var(--hair)}
.mbar-in{max-width:1120px;margin:0 auto;padding:0 var(--s3);height:56px;display:flex;align-items:center;gap:var(--s2)}
.mark{font-family:var(--serif);font-weight:500;font-size:19px}
.back{display:flex;align-items:center;gap:var(--s2);color:var(--muted);white-space:nowrap}
.back::after{content:"";width:1px;height:16px;background:var(--rule)}
.back:hover{color:var(--text)}
.crumb{color:var(--muted);display:flex;align-items:center;gap:var(--s2);white-space:nowrap}
.crumb::before{content:"";width:1px;height:16px;background:var(--rule)}
.mbar .sp{flex:1}
.page{max-width:960px;margin:0 auto;padding:var(--s6) var(--s3) var(--s8)}
h1{font-family:var(--serif);font-weight:500;font-size:var(--fs-display);line-height:1.15;letter-spacing:-.012em;margin:0}
.psub{color:var(--muted);margin:var(--s1) 0 0;max-width:72ch}
.sec{margin-top:var(--s6);padding-top:var(--s3);border-top:var(--hair)}
.sec h2{font-family:var(--serif);font-weight:500;font-size:var(--fs-title);margin:0}
.list{margin-top:var(--s1)}
.row{position:relative;display:grid;grid-template-columns:minmax(0,1fr) auto;gap:var(--s4);align-items:end;padding:var(--s3) 0;border-bottom:var(--hair)}
.row:last-child{border-bottom:0}
a.row::before{content:"";position:absolute;inset:6px calc(-1 * var(--s2));border-radius:var(--radius);background:var(--hover);opacity:0;transition:opacity .15s ease;z-index:-1}
a.row:hover::before{opacity:1}
.kick{font-size:var(--fs-note);color:var(--muted)}
.name{font-family:var(--serif);font-weight:500;font-size:var(--fs-title);line-height:1.35}
.desc{color:var(--muted);margin-top:4px;max-width:64ch}
.meta{font-size:var(--fs-note);color:var(--muted);margin-top:var(--s1)}
@media (max-width:760px){
  :root{--fs-display:32px}
  .mbar-in{padding:0 var(--s2)}
  .page{padding:var(--s4) var(--s2) var(--s6)}
  .row{grid-template-columns:1fr;gap:4px}
}
"""

FONTS = "https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Newsreader:opsz,wght@6..72,400;6..72,500&family=Noto+Serif+SC:wght@500&family=Noto+Sans+SC:wght@400;500;600&display=swap"


def parse_revision(value):
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=SHANGHAI)
    return dt.astimezone(SHANGHAI)


def revision_sort_key(value):
    return parse_revision(value).timestamp()


def display_revision(value):
    return parse_revision(value).strftime("%Y.%m.%d %H:%M") + " 北京时间"


def esc(value):
    return html.escape(value or "", quote=True)


def safe_url(url, https_only=False):
    if not url:
        return ""
    url = url.strip()
    lower = url.lower()
    if lower.startswith("javascript:") or lower.startswith("data:") or lower.startswith("vbscript:"):
        return ""
    if https_only:
        return url if lower.startswith("https://") else ""
    if lower.startswith("https://") or lower.startswith("http://"):
        return url
    return ""


class Sanitize(HTMLParser):
    """Turn the email HTML into the tags the reading page allows."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0
        self.drop_text = 0
        self.stack = []
        self.posts = 0
        self.images = 0
        self._post_ids = set()

    def handle_starttag(self, tag, attrs):
        self._start(tag, attrs, void=False)

    def handle_startendtag(self, tag, attrs):
        self._start(tag, attrs, void=True)

    def _start(self, tag, attrs, void):
        tag = tag.lower()
        if tag in ("script", "style", "title"):
            if not void:
                self.skip += 1
            return
        if tag in ("meta", "link"):
            return
        if tag == "head":
            if not void:
                self.skip += 1
            return
        if self.skip:
            return
        attr = {k.lower(): v for k, v in attrs}
        if tag == "div":
            pid = attr.get("id") or ""
            if re.fullmatch(r"post-\d+", pid) and pid not in self._post_ids:
                self._post_ids.add(pid)
                self.posts += 1
                self.out.append(f'<article class="post" id="{pid}">')
                self.stack.append("article")
            else:
                self.stack.append(None)
            return
        if tag in ("span", "font"):
            self.stack.append(None)
            return
        if tag == "h1":
            self.drop_text += 1
            self.stack.append("h1")
            return
        if tag in ("h2", "h3", "h4", "p"):
            self.out.append(f"<{tag}>")
            self.stack.append(tag)
            return
        if tag == "br":
            self.out.append("<br>")
            return
        if tag == "a":
            href = safe_url(attr.get("href") or "")
            if not href:
                self.stack.append(None)
                return
            self.out.append(
                f'<a href="{esc(href)}" target="_blank" rel="noopener noreferrer">'
            )
            self.stack.append("a")
            return
        if tag == "img":
            src = safe_url(attr.get("src") or "", https_only=True)
            if src:
                self.images += 1
                alt = esc(attr.get("alt") or "")
                self.out.append(
                    f'<img src="{esc(src)}" alt="{alt}" loading="lazy">'
                )
            return
        if not void:
            self.stack.append(None)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ("script", "style", "title", "head"):
            if self.skip:
                self.skip -= 1
            return
        if self.skip:
            return
        if tag == "h1":
            if self.drop_text:
                self.drop_text -= 1
            if self.stack and self.stack[-1] == "h1":
                self.stack.pop()
            return
        if tag in ("div", "span", "font", "h2", "h3", "h4", "p", "a"):
            if not self.stack:
                return
            opened = self.stack.pop()
            if opened == "article":
                self.out.append("</article>")
            elif opened in ("h2", "h3", "h4", "p", "a"):
                self.out.append(f"</{opened}>")

    def handle_data(self, data):
        if self.skip or self.drop_text or not data:
            return
        self.out.append(esc(data))

    def result(self):
        while self.stack:
            opened = self.stack.pop()
            if opened == "article":
                self.out.append("</article>")
            elif opened in ("h2", "h3", "h4", "p", "a"):
                self.out.append(f"</{opened}>")
        body = "".join(self.out)
        body = re.sub(r"(?:<br>\s*){3,}", "<br><br>", body)
        body = re.sub(r"<p>\s*</p>", "", body)
        return body, self.posts, self.images


def sanitize(source):
    parser = Sanitize()
    parser.feed(source)
    parser.close()
    body, posts, images = parser.result()
    if PRIVATE_RE.search(body):
        raise SystemExit("refusing to publish: sanitized HTML still has a private address")
    return body, posts, images


def heading_list(body):
    found = []
    for i, match in enumerate(re.finditer(r"<h2>(.*?)</h2>", body, re.S), start=1):
        text = re.sub(r"<[^>]+>", "", match.group(1))
        text = re.sub(r"\s+", " ", text).strip()
        found.append((f"s{i}", text))
    numbered = body
    for sid, _ in found:
        numbered = numbered.replace("<h2>", f'<h2 id="{sid}">', 1)
    return numbered, found


def edition_page(meta, body):
    body, headings = heading_list(body)
    toc = "\n".join(
        f'  <a href="#{sid}">{esc(text)}</a>' for sid, text in headings
    )
    parts = []
    if meta.get("window"):
        parts.append("覆盖窗口：" + meta["window"])
    parts.append("更新时间：" + meta["updated_display"])
    if meta.get("posts"):
        parts.append(f'{meta["posts"]} 条')
    label = LABEL[meta["edition"]]
    date_dots = meta["date"].replace("-", ".")
    title = f'{date_dots} {label}'
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>{esc(title)} · twitter · Mushroom</title>
<link rel="stylesheet" href="{FONTS}">
<style>{EDITION_CSS}</style>
</head><body>
<header class="mbar"><div class="mbar-in">
  <a class="back" href="../" aria-label="返回 twitter">←&#8201;返回</a>
  <a class="mark" href="../../" aria-label="Mushroom 首页"><span>Mushroom</span></a>
  <span class="crumb">twitter</span>
  <span class="sp"></span>
</div></header>
<div class="wrap">
<nav class="toc" aria-label="目录"><div class="tl">目录</div>
{toc}
</nav>
<main>
<h1>{esc(title)}</h1>
<p class="meta">{esc(" · ".join(parts))}</p>
{body}
</main>
</div>
<script>
(function(){{
  var links=[].slice.call(document.querySelectorAll('nav.toc a'));
  var secs=links.map(function(a){{return document.querySelector(a.getAttribute('href'))}});
  function on(){{
    var y=window.scrollY+120, idx=0;
    secs.forEach(function(s,i){{ if(s && s.offsetTop<=y) idx=i; }});
    links.forEach(function(a,i){{ a.classList.toggle('on', i===idx); }});
  }}
  window.addEventListener('scroll', on, {{passive:true}}); on();
}})();
</script>
</body></html>
"""


def sort_editions(editions):
    def key(item):
        return (item["date"], 1 if item["edition"] == "pm" else 0)
    return sorted(editions, key=key, reverse=True)


def index_page(editions):
    rows = []
    for item in editions:
        label = LABEL[item["edition"]]
        date_dots = item["date"].replace("-", ".")
        window = item.get("window") or ""
        kick = f"{date_dots} · {label}"
        if window:
            kick += f" · {window}"
        meta = f'更新 {item["updated_display"]}'
        if item.get("posts"):
            meta += f' · {item["posts"]} 条'
        if item.get("images"):
            meta += f' · {item["images"]} 张图'
        rows.append(
            f'      <a class="row" href="./{item["slug"]}/">\n'
            f'        <div>\n'
            f'          <div class="kick">{esc(kick)}</div>\n'
            f'          <div class="name">X Digest · {esc(label)}</div>\n'
            f'          <div class="meta">{esc(meta)}</div>\n'
            f'        </div>\n'
            f'      </a>'
        )
    body = "\n".join(rows) if rows else '      <p class="psub">还没有一期</p>'
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<title>twitter · Mushroom</title>
<link rel="stylesheet" href="{FONTS}">
<style>{INDEX_CSS}</style>
</head><body>
<header class="mbar"><div class="mbar-in">
  <a class="back" href="../" aria-label="返回首页">←&#8201;返回</a>
  <a class="mark" href="../" aria-label="Mushroom 首页"><span>Mushroom</span></a>
  <span class="crumb">twitter</span>
  <span class="sp"></span>
</div></header>
<main class="page">
  <h1>twitter</h1>
  <p class="psub">X Digest。同一天的早报和晚报各留一期；同一期若有修订，只留较新的那一版。新的日期加在上面，以前的日期还在。</p>
  <section class="sec">
    <h2>全部期数</h2>
    <div class="list">
{body}
    </div>
  </section>
</main>
</body></html>
"""


def home_section(latest, count):
    if latest is None:
        desc = "还没有一期"
        side = "0 期"
    else:
        label = LABEL[latest["edition"]]
        desc = f'最新：{latest["date"].replace("-", ".")} {label}'
        side = f"{count} 期"
    return (
        '  <section class="sec" id="twitter">\n'
        '    <div class="list">\n'
        '      <a class="row" href="./twitter/">\n'
        f'        <div><div class="name">twitter</div><div class="desc">{esc(desc)}</div></div>\n'
        f'        <div class="side">{esc(side)}</div>\n'
        '      </a>\n'
        '    </div>\n'
        '  </section>\n'
    )


def update_home(repo, editions):
    path = repo / "index.html"
    text = path.read_text(encoding="utf-8")
    ordered = sort_editions(editions)
    block = home_section(ordered[0] if ordered else None, len(ordered))
    pattern = re.compile(r'\n  <section class="sec" id="twitter">.*?</section>\n', re.S)
    if pattern.search(text):
        text = pattern.sub("\n" + block, text, count=1)
    else:
        text = text.replace("</main>", block + "</main>", 1)
    path.write_text(text, encoding="utf-8")


def load_editions(repo):
    path = repo / "twitter" / "editions.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def write_catalog(repo, editions):
    ordered = sort_editions(editions)
    root = repo / "twitter"
    root.mkdir(parents=True, exist_ok=True)
    (root / "editions.json").write_text(
        json.dumps(ordered, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    (root / "index.html").write_text(index_page(ordered), encoding="utf-8")
    update_home(repo, ordered)
    return ordered


def publish(repo, source_html, date, edition, revision, window=""):
    repo = Path(repo)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise SystemExit("date must be YYYY-MM-DD")
    if edition not in LABEL:
        raise SystemExit("edition must be am or pm")
    revision_sort_key(revision)
    body, posts, images = sanitize(source_html)
    if not window:
        plain = re.sub(r"<[^>]+>", " ", body)
        found = re.search(
            r"固定窗口：\s*(20\d\d-\d\d-\d\d \d\d:\d\d:\d\d\s*至\s*20\d\d-\d\d-\d\d \d\d:\d\d:\d\d(?:\s*北京时间)?)",
            plain,
        )
        window = re.sub(r"\s+", " ", found.group(1)).strip() if found else ""
    slug = f"{date}-{edition}"
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    record = {
        "slug": slug,
        "date": date,
        "edition": edition,
        "revision": revision,
        "updated_display": display_revision(revision),
        "window": window,
        "posts": posts,
        "images": images,
        "content_sha256": digest,
    }
    editions = load_editions(repo)
    current = next((item for item in editions if item["slug"] == slug), None)
    if current and revision_sort_key(revision) < revision_sort_key(current["revision"]):
        return {"status": "skip", "reason": "older revision", "kept": current["revision"], "slug": slug}
    if current and current.get("content_sha256") == digest and current.get("revision") == revision:
        return {"status": "unchanged", "slug": slug, "posts": posts, "images": images}
    page = edition_page(record, body)
    if PRIVATE_RE.search(page):
        raise SystemExit("refusing to publish: page still has a private address")
    out = repo / "twitter" / slug
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    editions = [item for item in editions if item["slug"] != slug]
    editions.append(record)
    write_catalog(repo, editions)
    status = "replace" if current else "add"
    return {"status": status, "slug": slug, "posts": posts, "images": images, "revision": revision}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Publish one twitter digest edition")
    parser.add_argument("repo")
    parser.add_argument("source")
    parser.add_argument("--date", required=True)
    parser.add_argument("--edition", required=True, choices=["am", "pm"])
    parser.add_argument("--revision", required=True, help="ISO-8601 timestamp; newer wins for the same date+edition")
    parser.add_argument("--window", default="")
    args = parser.parse_args(argv)
    source = Path(args.source).read_text(encoding="utf-8")
    result = publish(
        Path(args.repo), source, args.date, args.edition, args.revision, args.window
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
