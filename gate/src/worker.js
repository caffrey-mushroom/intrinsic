// 麻薯 gate: every request must carry a valid Cloudflare Access login (email code).
// Access only proves who you are; membership is decided here, from single-use invite codes.
// Fails closed: no valid login or not a member means no page content.

import { joinPage, deniedPage, adminPage } from './pages.js';

const OLD_SITE = 'https://caffrey-mushroom.github.io/intrinsic/';
const now = () => new Date().toISOString();

export default {
  async fetch(req, env, ctx) {
    const url = new URL(req.url);
    const email = await identify(req, env, url);
    if (!email) return html(deniedPage(), 401);

    const admins = (env.ADMIN_EMAILS || '').toLowerCase().split(',').map(s => s.trim()).filter(Boolean);
    const isAdmin = admins.includes(email);

    if (req.method !== 'GET' && req.method !== 'HEAD') {
      const origin = req.headers.get('Origin');
      if (origin && origin !== url.origin) return json({ error: 'bad origin' }, 403);
    }

    let member = await env.DB.prepare('SELECT * FROM members WHERE email = ?').bind(email).first();
    if (isAdmin && !member) {
      await env.DB.prepare('INSERT INTO members (email, invite_code, joined_at) VALUES (?, ?, ?)').bind(email, 'admin', now()).run();
      member = { email, revoked: 0 };
    }

    if (url.pathname === '/_gate/logout') return Response.redirect(url.origin + '/cdn-cgi/access/logout', 302);

    if (!member || (member.revoked && !isAdmin)) {
      if (url.pathname === '/_gate/join' && req.method === 'POST') return redeem(req, env, email, member);
      return html(joinPage(email, member && member.revoked ? '你的访问权限已被撤销，如有疑问请联系管理员。' : ''), 403);
    }

    ctx.waitUntil(env.DB.prepare('UPDATE members SET last_seen = ? WHERE email = ?').bind(now(), email).run());

    if (url.pathname.startsWith('/_gate/api/')) return api(req, env, url, email, isAdmin);
    if (url.pathname === '/_gate/admin') return isAdmin ? html(adminPage()) : new Response('Not found', { status: 404 });
    if (url.pathname === '/_gate/join') return Response.redirect(url.origin + '/', 302);

    const res = await env.ASSETS.fetch(req);
    const type = res.headers.get('content-type') || '';
    const headers = new Headers(res.headers);
    headers.set('Cache-Control', 'private, no-store');
    headers.set('X-Robots-Tag', 'noindex, nofollow');
    headers.set('Referrer-Policy', 'no-referrer');
    if (!type.includes('text/html')) return new Response(res.body, { status: res.status, headers });

    if (res.status === 200) {
      ctx.waitUntil(env.DB.prepare('INSERT INTO views (email, path, at) VALUES (?, ?, ?)').bind(email, url.pathname, now()).run());
    }
    const out = new Response(res.body, { status: res.status, headers });
    return new HTMLRewriter()
      .on('a[href]', { element(el) { const h = el.getAttribute('href'); if (h && h.startsWith(OLD_SITE)) el.setAttribute('href', '/' + h.slice(OLD_SITE.length)); } })
      .on('head', { element(el) { el.append('<link rel="stylesheet" href="/_gate/comments.css">', { html: true }); } })
      .on('body', { element(el) { el.append('<script src="/_gate/comments.js" defer></script>', { html: true }); } })
      .transform(out);
  },
};

// ---------- identity ----------

async function identify(req, env, url) {
  // Local development only: .dev.vars sets DEV_EMAIL; never set in production.
  if (env.DEV_EMAIL && (url.hostname === 'localhost' || url.hostname === '127.0.0.1')) {
    return (url.searchParams.get('as') || cookie(req, 'dev_as') || env.DEV_EMAIL).toLowerCase();
  }
  const token = req.headers.get('Cf-Access-Jwt-Assertion') || cookie(req, 'CF_Authorization');
  if (!token || !env.TEAM_DOMAIN || !env.ACCESS_AUD) return null;
  try {
    const [h, p, s] = token.split('.');
    const header = JSON.parse(b64text(h));
    const payload = JSON.parse(b64text(p));
    const issuer = 'https://' + env.TEAM_DOMAIN;
    if (payload.iss !== issuer) return null;
    const aud = Array.isArray(payload.aud) ? payload.aud : [payload.aud];
    if (!aud.includes(env.ACCESS_AUD)) return null;
    if (!payload.exp || payload.exp * 1000 < Date.now()) return null;
    const jwk = (await certs(issuer)).find(k => k.kid === header.kid);
    if (!jwk) return null;
    const key = await crypto.subtle.importKey('jwk', jwk, { name: 'RSASSA-PKCS1-v1_5', hash: 'SHA-256' }, false, ['verify']);
    const ok = await crypto.subtle.verify('RSASSA-PKCS1-v1_5', key, b64bytes(s), new TextEncoder().encode(h + '.' + p));
    return ok && payload.email ? String(payload.email).toLowerCase() : null;
  } catch {
    return null;
  }
}

let certCache = { at: 0, keys: [] };
async function certs(issuer) {
  if (Date.now() - certCache.at < 3600e3 && certCache.keys.length) return certCache.keys;
  const r = await fetch(issuer + '/cdn-cgi/access/certs');
  const j = await r.json();
  certCache = { at: Date.now(), keys: j.keys || [] };
  return certCache.keys;
}

function b64bytes(s) {
  s = s.replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  return Uint8Array.from(atob(s), c => c.charCodeAt(0));
}
const b64text = s => new TextDecoder().decode(b64bytes(s));

function cookie(req, name) {
  const m = (req.headers.get('Cookie') || '').match(new RegExp('(?:^|;\\s*)' + name + '=([^;]+)'));
  return m ? decodeURIComponent(m[1]) : null;
}

// ---------- invite redemption ----------

async function redeem(req, env, email, member) {
  const form = await req.formData();
  const code = String(form.get('code') || '').trim().toUpperCase();
  if (member && member.revoked) return html(joinPage(email, '你的访问权限已被撤销，如有疑问请联系管理员。'), 403);
  if (!code) return html(joinPage(email, '请输入邀请码。'), 400);
  // Conditional update so a code can only ever be claimed once, even with two simultaneous attempts.
  const r = await env.DB.prepare('UPDATE invites SET used_by = ?, used_at = ? WHERE code = ? AND used_by IS NULL AND revoked = 0')
    .bind(email, now(), code).run();
  if (!r.meta || r.meta.changes !== 1) return html(joinPage(email, '邀请码无效、已被使用或已作废。'), 400);
  await env.DB.prepare('INSERT OR REPLACE INTO members (email, invite_code, joined_at, revoked) VALUES (?, ?, ?, 0)').bind(email, code, now()).run();
  return Response.redirect(new URL(req.url).origin + '/', 303);
}

// ---------- API ----------

async function api(req, env, url, email, isAdmin) {
  const path = url.pathname.slice('/_gate/api/'.length);
  const body = req.method === 'POST' ? await req.json().catch(() => ({})) : {};

  if (path === 'me') return json({ email, admin: isAdmin });

  if (path === 'comments' && req.method === 'GET') {
    const page = normPage(url.searchParams.get('page'));
    const { results } = await env.DB.prepare('SELECT id, parent_id, quote, prefix, suffix, body, author, created_at, resolved FROM comments WHERE page = ? AND deleted = 0 ORDER BY created_at').bind(page).all();
    return json({ comments: results });
  }
  if (path === 'comments' && req.method === 'POST') {
    const page = normPage(body.page);
    const text = String(body.body || '').trim().slice(0, 5000);
    if (!page || !text) return json({ error: 'empty' }, 400);
    const parent = body.parent_id ? String(body.parent_id) : null;
    if (!parent && !body.quote) return json({ error: 'no quote' }, 400);
    const row = {
      id: crypto.randomUUID(), page, parent_id: parent,
      quote: parent ? null : String(body.quote).slice(0, 2000),
      prefix: parent ? null : String(body.prefix || '').slice(0, 64),
      suffix: parent ? null : String(body.suffix || '').slice(0, 64),
      body: text, author: email, created_at: now(), resolved: 0,
    };
    await env.DB.prepare('INSERT INTO comments (id, page, parent_id, quote, prefix, suffix, body, author, created_at) VALUES (?,?,?,?,?,?,?,?,?)')
      .bind(row.id, row.page, row.parent_id, row.quote, row.prefix, row.suffix, row.body, row.author, row.created_at).run();
    return json({ comment: row });
  }
  const m = path.match(/^comments\/([\w-]+)\/(resolve|reopen|delete)$/);
  if (m && req.method === 'POST') {
    const [, id, action] = m;
    if (action === 'delete') {
      const r = await env.DB.prepare('UPDATE comments SET deleted = 1 WHERE (id = ? OR parent_id = ?) AND (author = ? OR ?)').bind(id, id, email, isAdmin ? 1 : 0).run();
      return json({ ok: r.meta.changes > 0 });
    }
    await env.DB.prepare('UPDATE comments SET resolved = ? WHERE id = ?').bind(action === 'resolve' ? 1 : 0, id).run();
    return json({ ok: true });
  }

  if (!isAdmin) return json({ error: 'forbidden' }, 403);

  if (path === 'admin/state') {
    const invites = (await env.DB.prepare('SELECT * FROM invites ORDER BY created_at DESC').all()).results;
    const members = (await env.DB.prepare('SELECT m.*, (SELECT COUNT(*) FROM views v WHERE v.email = m.email) AS views FROM members m ORDER BY joined_at DESC').all()).results;
    const views = (await env.DB.prepare('SELECT * FROM views ORDER BY at DESC LIMIT 200').all()).results;
    return json({ invites, members, views });
  }
  if (path === 'admin/invites' && req.method === 'POST') {
    const n = Math.min(Math.max(parseInt(body.count) || 1, 1), 20);
    const made = [];
    for (let i = 0; i < n; i++) {
      const code = newCode();
      await env.DB.prepare('INSERT INTO invites (code, note, created_at) VALUES (?, ?, ?)').bind(code, String(body.note || '').slice(0, 200), now()).run();
      made.push(code);
    }
    return json({ codes: made });
  }
  const a = path.match(/^admin\/(invite|member)\/(revoke|restore)$/);
  if (a && req.method === 'POST') {
    const val = a[2] === 'revoke' ? 1 : 0;
    if (a[1] === 'invite') await env.DB.prepare('UPDATE invites SET revoked = ? WHERE code = ?').bind(val, String(body.code)).run();
    else await env.DB.prepare('UPDATE members SET revoked = ? WHERE email = ?').bind(val, String(body.email).toLowerCase()).run();
    return json({ ok: true });
  }
  return json({ error: 'not found' }, 404);
}

// white.html and index.html share comments with the page they belong to.
function normPage(p) {
  if (!p) return '';
  p = String(p).split('?')[0].split('#')[0];
  p = p.replace(/\/(index|white)(\.html)?\/?$/, '/');
  if (!p.endsWith('/') && !/\.[a-z0-9]+$/i.test(p)) p += '/';
  return p.slice(0, 500);
}

function newCode() {
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  const b = crypto.getRandomValues(new Uint8Array(10));
  const s = Array.from(b, x => alphabet[x % alphabet.length]).join('');
  return s.slice(0, 5) + '-' + s.slice(5);
}

const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { 'content-type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' } });
const html = (s, status = 200) => new Response(s, { status, headers: { 'content-type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' } });
