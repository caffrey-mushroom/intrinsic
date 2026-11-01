// Idempotent Cloudflare setup, run by the deploy workflow before `wrangler deploy`.
// Ensures: D1 database, email one-time-code login, an Access application in front of the worker.
// Writes wrangler.deploy.json with the real ids. Needs CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, MASHU_ADMIN_EMAILS.
import { readFileSync, writeFileSync } from 'node:fs';

const { CLOUDFLARE_API_TOKEN: TOKEN, CLOUDFLARE_ACCOUNT_ID: ACCT, MASHU_ADMIN_EMAILS: ADMINS } = process.env;
if (!TOKEN || !ACCT) throw new Error('CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID must be set as repository secrets');
if (!ADMINS) throw new Error('MASHU_ADMIN_EMAILS must be set as a repository variable');
const WORKER = 'mashu';

async function cf(method, path, body) {
  const r = await fetch(`https://api.cloudflare.com/client/v4/accounts/${ACCT}${path}`, {
    method, headers: { Authorization: `Bearer ${TOKEN}`, 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const j = await r.json().catch(() => ({}));
  if (!j.success) throw new Error(`${method} ${path} failed: ${JSON.stringify(j.errors || j)}`);
  return j.result;
}

// 1. D1
let db = (await cf('GET', '/d1/database?name=mashu')).find(d => d.name === 'mashu');
if (!db) db = await cf('POST', '/d1/database', { name: 'mashu' });
const dbId = db.uuid;

// 2. Hostname: <worker>.<account subdomain>.workers.dev
const { subdomain } = await cf('GET', '/workers/subdomain');
const host = `${WORKER}.${subdomain}.workers.dev`;

// 3. Zero Trust team domain (created once in the dashboard when Zero Trust is first opened)
let org;
try { org = await cf('GET', '/access/organizations'); } catch (e) {
  throw new Error('Zero Trust is not set up yet: open dash.cloudflare.com -> Zero Trust once, pick a team name and the Free plan. ' + e.message);
}
const team = org.auth_domain;

// 4. Email one-time code login
let otp = (await cf('GET', '/access/identity_providers')).find(p => p.type === 'onetimepin');
if (!otp) otp = await cf('POST', '/access/identity_providers', { name: 'Email code', type: 'onetimepin', config: {} });

// 5. Access application. Policy lets any verified email through; the worker then checks invite membership.
const appBody = {
  name: '麻薯', domain: host, type: 'self_hosted', session_duration: '720h',
  allowed_idps: [otp.id], auto_redirect_to_identity: true, app_launcher_visible: false,
  policies: [{ name: 'verified email', decision: 'allow', include: [{ everyone: {} }], precedence: 1 }],
};
let app = (await cf('GET', '/access/apps')).find(a => a.domain === host);
app = app ? await cf('PUT', `/access/apps/${app.id}`, appBody) : await cf('POST', '/access/apps', appBody);

// 6. Deploy config
const cfg = JSON.parse(readFileSync('wrangler.jsonc', 'utf8').replace(/^\s*\/\/.*$/gm, ''));
cfg.d1_databases[0].database_id = dbId;
cfg.vars = { TEAM_DOMAIN: team, ACCESS_AUD: app.aud, ADMIN_EMAILS: ADMINS.toLowerCase() };
writeFileSync('wrangler.deploy.json', JSON.stringify(cfg, null, 2));
console.log(`site: https://${host}  team: ${team}  d1: ${dbId}`);
