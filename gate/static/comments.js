// 麻薯 margin comments: select text -> comment card in the right margin, shared with the team.
// Injected by the gate worker into every page; pages themselves are not edited.
(() => {
  if (window.__mcLoaded) return; window.__mcLoaded = true;
  const API = '/_gate/api';
  const PAGE = location.pathname;
  const UI = 'mc-ui';
  const state = { me: null, comments: [], anchors: new Map(), active: null, open: false };
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const el = (tag, cls, htmlStr) => { const e = document.createElement(tag); if (cls) e.className = cls; if (htmlStr != null) e.innerHTML = htmlStr; return e; };
  const who = e => esc(String(e || '').split('@')[0]);
  const when = s => { const d = new Date(s); return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`; };
  const post = (u, b) => fetch(API + u, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(b || {}) }).then(r => r.json());
  const narrow = () => (window.visualViewport ? visualViewport.width : window.innerWidth) < 1000;

  // ---------- text index (whitespace-normalized, maps back to DOM text nodes) ----------
  function buildIndex() {
    const nodes = []; let text = ''; let lastSpace = true;
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode(n) {
        const p = n.parentElement;
        if (!p || p.closest('.' + UI + ',script,style,noscript,textarea,svg title')) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    let n;
    while ((n = walker.nextNode())) {
      const s = n.nodeValue; const map = [];
      for (let i = 0; i < s.length; i++) {
        const sp = /\s/.test(s[i]);
        if (sp && lastSpace) continue;
        map.push([text.length, i]);
        text += sp ? ' ' : s[i]; lastSpace = sp;
      }
      if (map.length) nodes.push({ node: n, start: map[0][0], map });
    }
    return { text, nodes };
  }
  const norm = s => String(s || '').replace(/\s+/g, ' ');

  function locate(idx, nStart, nEnd) {
    // normalized offsets -> DOM Range
    const find = pos => {
      for (const e of idx.nodes) {
        const last = e.map[e.map.length - 1][0];
        if (pos >= e.start && pos <= last) {
          const hit = e.map.find(m => m[0] >= pos) || e.map[e.map.length - 1];
          return { node: e.node, off: hit[1] };
        }
      }
      return null;
    };
    const a = find(nStart), b = find(nEnd - 1);
    if (!a || !b) return null;
    const r = document.createRange();
    r.setStart(a.node, a.off); r.setEnd(b.node, b.off + 1);
    return r;
  }

  function anchorOf(c, idx) {
    const q = norm(c.quote).trim();
    if (!q) return null;
    let best = -1, bestScore = -1, from = 0;
    while (true) {
      const i = idx.text.indexOf(q, from);
      if (i < 0) break;
      const pre = idx.text.slice(Math.max(0, i - 32), i), suf = idx.text.slice(i + q.length, i + q.length + 32);
      const score = overlap(pre, norm(c.prefix), true) + overlap(suf, norm(c.suffix), false);
      if (score > bestScore) { best = i; bestScore = score; }
      from = i + 1;
    }
    return best < 0 ? null : locate(idx, best, best + q.length);
  }
  function overlap(a, b, fromEnd) {
    let n = 0;
    for (let i = 1; i <= Math.min(a.length, b.length); i++) {
      if (fromEnd ? a[a.length - i] === b[b.length - i] : a[i - 1] === b[i - 1]) n++; else break;
    }
    return n;
  }

  // wrap a Range in <mark> pieces without disturbing layout
  function highlight(range, id) {
    const marks = [];
    const walker = document.createTreeWalker(range.commonAncestorContainer.nodeType === 3 ? range.commonAncestorContainer.parentNode : range.commonAncestorContainer, NodeFilter.SHOW_TEXT);
    const texts = []; let n;
    while ((n = walker.nextNode())) if (range.intersectsNode(n) && n.nodeValue.trim() !== '' && !n.parentElement.closest('.' + UI)) texts.push(n);
    for (let t of texts) {
      let s = t === range.startContainer ? range.startOffset : 0;
      let e = t === range.endContainer ? range.endOffset : t.nodeValue.length;
      if (e <= s) continue;
      if (s > 0) t = t.splitText(s);
      if (e - s < t.nodeValue.length) t.splitText(e - s);
      if (t.parentElement.closest('svg')) continue; // keep charts intact
      const m = el('mark', 'mc-hl'); m.dataset.mc = id;
      t.parentNode.insertBefore(m, t); m.appendChild(t); marks.push(m);
    }
    return marks;
  }
  function clearHighlights() {
    document.querySelectorAll('mark.mc-hl').forEach(m => { const p = m.parentNode; while (m.firstChild) p.insertBefore(m.firstChild, m); p.removeChild(m); p.normalize(); });
    state.anchors.clear();
  }

  // ---------- UI shell ----------
  const toggle = el('button', UI + ' mc-toggle'); toggle.type = 'button';
  const panel = el('div', UI + ' mc-panel');
  const addBtn = el('button', UI + ' mc-add', '评论'); addBtn.type = 'button';
  document.body.append(toggle, panel, addBtn);

  function setOpen(v) {
    state.open = v;
    document.documentElement.classList.toggle('mc-open', v && !narrow());
    document.documentElement.classList.toggle('mc-sheet', v && narrow());
    render();
    placeFixed();
  }
  toggle.onclick = () => setOpen(!state.open);

  // ---------- selection -> composer ----------
  let pending = null;
  document.addEventListener('mouseup', onSelect); document.addEventListener('touchend', () => setTimeout(onSelect, 50));
  function onSelect(e) {
    if (e && e.target && e.target.closest && e.target.closest('.' + UI)) return;
    setTimeout(() => {
      const sel = window.getSelection();
      const text = sel && sel.rangeCount ? sel.toString() : '';
      if (!text.trim() || text.length > 2000) { addBtn.style.display = 'none'; return; }
      const r = sel.getRangeAt(0);
      if (r.commonAncestorContainer.parentElement && r.commonAncestorContainer.parentElement.closest('.' + UI)) return;
      const rect = r.getBoundingClientRect();
      pending = r.cloneRange();
      addBtn.style.display = 'block';
      addBtn.style.top = (rect.bottom + window.scrollY + 6) + 'px';
      addBtn.style.left = Math.min(rect.right + window.scrollX - 20, document.documentElement.clientWidth - 70 + window.scrollX) + 'px';
    }, 0);
  }
  addBtn.addEventListener('mousedown', e => e.preventDefault());
  addBtn.onclick = () => {
    if (!pending) return;
    const idx = buildIndex();
    // compute normalized quote with context from the live index
    const quote = norm(pending.toString()).trim();
    const probe = document.createRange(); probe.setStart(document.body, 0); probe.setEnd(pending.startContainer, pending.startOffset);
    const beforeLen = norm(probe.toString()).length; // approximate position, used to pick prefix/suffix
    let i = idx.text.indexOf(quote, Math.max(0, beforeLen - 200));
    if (i < 0) i = idx.text.indexOf(quote);
    const draft = {
      id: 'draft', quote,
      prefix: i >= 0 ? idx.text.slice(Math.max(0, i - 32), i) : '',
      suffix: i >= 0 ? idx.text.slice(i + quote.length, i + quote.length + 32) : '',
      draft: true,
    };
    state.draft = draft; state.active = 'draft';
    addBtn.style.display = 'none';
    window.getSelection().removeAllRanges();
    rehighlight();
    setOpen(true);
    const ta = panel.querySelector('.mc-card[data-id="draft"] textarea'); if (ta) ta.focus();
  };

  // ---------- render ----------
  function threads() {
    const roots = state.comments.filter(c => !c.parent_id);
    const kids = id => state.comments.filter(c => c.parent_id === id);
    return roots.map(r => ({ ...r, replies: kids(r.id) }));
  }

  function rehighlight() {
    clearHighlights();
    const idx0 = buildIndex();
    const list = threads().filter(t => !t.resolved);
    const ranges = list.map(t => [t.id, anchorOf(t, idx0)]);
    for (const [id, r] of ranges) if (r) state.anchors.set(id, highlight(r, id));
    if (state.draft) {
      try { const r = anchorOf(state.draft, buildIndex()); if (r) state.anchors.set('draft', highlight(r, 'draft')); } catch {}
    }
  }

  function cardHTML(t) {
    const mine = state.me && t.author === state.me.email;
    const replies = (t.replies || []).map(r => `<div class="mc-reply"><div class="mc-meta"><b>${who(r.author)}</b> <span>${when(r.created_at)}</span></div><div class="mc-body">${esc(r.body)}</div></div>`).join('');
    if (t.draft) return `<div class="mc-quote">${esc(t.quote.slice(0, 120))}</div>
      <textarea placeholder="写评论... (Ctrl/Cmd+Enter 发送)"></textarea>
      <div class="mc-actions"><button class="mc-cancel" type="button">取消</button><button class="mc-send" type="button">发送</button></div>`;
    return `<div class="mc-meta"><b>${who(t.author)}</b> <span>${when(t.created_at)}</span>
      <span class="mc-tools">${t.resolved ? '<button class="mc-reopen" type="button">重新打开</button>' : '<button class="mc-resolve" type="button" title="标记为已解决">解决</button>'}${mine || (state.me && state.me.admin) ? '<button class="mc-del" type="button" title="删除">删除</button>' : ''}</span></div>
      <div class="mc-quote">${esc((t.quote || '').slice(0, 120))}</div>
      <div class="mc-body">${esc(t.body)}</div>${replies}
      <div class="mc-replybox"><textarea placeholder="回复..."></textarea><div class="mc-actions"><button class="mc-send" type="button">回复</button></div></div>`;
  }

  function render() {
    const list = threads();
    const open = list.filter(t => !t.resolved);
    toggle.textContent = state.open ? '收起评论' : (open.length ? `评论 (${open.length})` : '评论');
    panel.innerHTML = '';
    if (!state.open) { layout(); return; }
    const head = el('div', 'mc-head', `<b>评论</b><span>选中文字即可评论</span>`);
    panel.append(head);
    const all = state.draft ? [state.draft, ...open] : open;
    const orphans = [], placed = [];
    for (const t of all) {
      const card = el('div', 'mc-card' + (state.active === t.id ? ' mc-active' : ''), cardHTML(t));
      card.dataset.id = t.id;
      wire(card, t);
      (state.anchors.get(t.id) ? placed : orphans).push(card);
    }
    placed.forEach(c => panel.append(c));
    if (orphans.length) { panel.append(el('div', 'mc-sec', '原文已改动，找不到对应位置')); orphans.forEach(c => { c.classList.add('mc-orphan'); panel.append(c); }); }
    const resolved = list.filter(t => t.resolved);
    if (resolved.length) {
      const sec = el('details', 'mc-resolved', `<summary>已解决 (${resolved.length})</summary>`);
      resolved.forEach(t => { const c = el('div', 'mc-card', cardHTML(t)); c.dataset.id = t.id; wire(c, t); sec.append(c); });
      panel.append(sec);
    }
    if (!all.length && !resolved.length) panel.append(el('div', 'mc-empty', '还没有评论。选中页面上的文字，点"评论"。'));
    layout();
  }

  function wire(card, t) {
    card.addEventListener('click', e => {
      if (e.target.closest('button,textarea')) return;
      focus(t.id, true);
    });
    card.addEventListener('mouseenter', () => mark(t.id, true));
    card.addEventListener('mouseleave', () => mark(t.id, false));
    const ta = card.querySelector('textarea');
    const send = card.querySelector('.mc-send');
    if (ta) ta.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) send.click(); });
    if (ta) ta.addEventListener('input', () => { ta.style.height = 'auto'; ta.style.height = ta.scrollHeight + 'px'; layout(); });
    if (send) send.onclick = async () => {
      const body = ta.value.trim(); if (!body) return;
      send.disabled = true;
      const payload = t.draft ? { page: PAGE, quote: t.quote, prefix: t.prefix, suffix: t.suffix, body } : { page: PAGE, parent_id: t.id, body };
      const r = await post('/comments', payload);
      if (r.comment) { state.comments.push(r.comment); if (t.draft) { state.draft = null; state.active = r.comment.id; } }
      rehighlight(); render();
    };
    const cancel = card.querySelector('.mc-cancel');
    if (cancel) cancel.onclick = () => { state.draft = null; rehighlight(); render(); };
    const act = (cls, path, fn) => { const b = card.querySelector(cls); if (b) b.onclick = async () => { await post(`/comments/${t.id}/${path}`); fn(); rehighlight(); render(); }; };
    act('.mc-resolve', 'resolve', () => { t.resolved = 1; state.comments.find(c => c.id === t.id).resolved = 1; });
    act('.mc-reopen', 'reopen', () => { state.comments.find(c => c.id === t.id).resolved = 0; });
    act('.mc-del', 'delete', () => { state.comments = state.comments.filter(c => c.id !== t.id && c.parent_id !== t.id); });
  }

  function mark(id, on) { (state.anchors.get(id) || []).forEach(m => m.classList.toggle('mc-hl-on', on)); }
  function focus(id, scroll) {
    state.active = id;
    panel.querySelectorAll('.mc-card').forEach(c => c.classList.toggle('mc-active', c.dataset.id === id));
    document.querySelectorAll('mark.mc-hl').forEach(m => m.classList.toggle('mc-hl-on', m.dataset.mc === id));
    const m = (state.anchors.get(id) || [])[0];
    if (scroll && m) m.scrollIntoView({ behavior: 'smooth', block: 'center' });
    layout();
  }
  document.addEventListener('click', e => {
    const m = e.target.closest && e.target.closest('mark.mc-hl');
    if (!m) return;
    if (!state.open) setOpen(true);
    focus(m.dataset.mc, false);
    if (narrow()) { const c = panel.querySelector(`.mc-card[data-id="${m.dataset.mc}"]`); if (c) c.scrollIntoView({ block: 'nearest' }); }
  });

  // Cards sit level with their highlight; push down to avoid overlap, active card pulls to its line.
  function layout() {
    if (!state.open || narrow()) { panel.style.height = ''; panel.querySelectorAll('.mc-card').forEach(c => { c.style.top = ''; }); return; }
    const cards = [...panel.querySelectorAll(':scope > .mc-card:not(.mc-orphan)')];
    const want = cards.map(c => { const m = (state.anchors.get(c.dataset.id) || [])[0]; return m ? m.getBoundingClientRect().top + window.scrollY : 0; });
    const order = cards.map((c, i) => i).sort((a, b) => want[a] - want[b]);
    let y = 64;
    const top = new Array(cards.length);
    for (const i of order) { top[i] = Math.max(want[i] - 8, y); y = top[i] + cards[i].offsetHeight + 10; }
    cards.forEach((c, i) => { c.style.top = top[i] + 'px'; });
    panel.style.height = '';
    panel.style.height = Math.max(document.documentElement.scrollHeight, y + 200) + 'px';
    const rest = [...panel.querySelectorAll(':scope > .mc-sec, :scope > .mc-orphan, :scope > .mc-resolved, :scope > .mc-empty')];
    let bottom = Math.max(64, ...cards.map((c, i) => top[i] + c.offsetHeight + 10));
    rest.forEach(r => { r.style.top = bottom + 'px'; bottom += r.offsetHeight + 10; });
  }

  // ---------- watermark ----------
  function watermark(email) {
    const d = new Date(); const label = `${email}  ${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="420" height="240"><text x="20" y="140" transform="rotate(-24 210 120)" font-family="sans-serif" font-size="15" fill="rgb(128,128,128)" fill-opacity="0.11">${esc(label)}</text></svg>`;
    const w = el('div', UI + ' mc-wm');
    w.style.backgroundImage = `url("data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}")`;
    document.body.append(w);
  }

  // ---------- boot ----------
  async function boot() {
    try {
      state.me = await fetch(API + '/me').then(r => r.json());
      if (state.me && state.me.email) watermark(state.me.email);
      const r = await fetch(API + '/comments?page=' + encodeURIComponent(PAGE)).then(r => r.json());
      state.comments = r.comments || [];
    } catch { state.comments = []; }
    rehighlight();
    state.open = !narrow() && threads().some(t => !t.resolved);
    setOpen(state.open);
    if (location.hash.startsWith('#mc-')) focus(location.hash.slice(4), true);
  }
  // Pin toggle and bottom sheet to what is actually on screen (pages wider than a phone grow the layout viewport).
  function placeFixed() {
    const vv = window.visualViewport; if (!vv) return;
    const sheet = document.documentElement.classList.contains('mc-sheet');
    const sheetH = Math.round(vv.height * 0.55);
    if (sheet) Object.assign(panel.style, { left: vv.offsetLeft + 'px', width: vv.width + 'px', right: 'auto', top: (vv.offsetTop + vv.height - sheetH) + 'px', bottom: 'auto', maxHeight: sheetH + 'px' });
    else Object.assign(panel.style, { left: '', width: '', right: '', top: '', bottom: '', maxHeight: '' });
    toggle.style.right = 'auto'; toggle.style.bottom = 'auto';
    toggle.style.left = (vv.offsetLeft + vv.width - toggle.offsetWidth - 16) + 'px';
    toggle.style.top = (vv.offsetTop + vv.height - toggle.offsetHeight - 16 - (sheet ? sheetH : 0)) + 'px';
  }
  if (window.visualViewport) { visualViewport.addEventListener('resize', placeFixed); visualViewport.addEventListener('scroll', placeFixed); }
  window.addEventListener('scroll', placeFixed, { passive: true });

  // charts and fonts shift layout after load; keep cards aligned
  let raf = 0; const relayout = () => { cancelAnimationFrame(raf); raf = requestAnimationFrame(layout); };
  window.addEventListener('resize', () => { if (state.open) setOpen(true); else relayout(); });
  window.addEventListener('load', relayout);
  let ticks = 0; const iv = setInterval(() => { relayout(); if (++ticks > 10) clearInterval(iv); }, 1000);
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
