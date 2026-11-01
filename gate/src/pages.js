// Small server-rendered pages: join (invite code), denied, admin.

const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const base = (title, body) => `<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>${title}</title><style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1f2933;--mute:#66727f;--line:#d9dee4;--acc:#3e5c76;--bad:#a23b3b}
@media (prefers-color-scheme:dark){:root{--bg:#14181d;--card:#1c2229;--ink:#e3e8ee;--mute:#95a1ad;--line:#2f3842;--acc:#8fb0cc;--bad:#e08a8a}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",sans-serif}
.wrap{max-width:440px;margin:12vh auto;padding:0 16px}.wide{max-width:1080px;margin:32px auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:24px}
h1{font-size:20px;margin:0 0 6px}h2{font-size:16px;margin:28px 0 10px}p{margin:6px 0;color:var(--mute)}
input,button{font:inherit}input{width:100%;padding:10px 12px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);letter-spacing:.06em}
button{padding:9px 16px;border:0;border-radius:8px;background:var(--acc);color:#fff;cursor:pointer}
@media (prefers-color-scheme:dark){button{color:#14181d}}
button.ghost{background:transparent;color:var(--acc);border:1px solid var(--line);padding:4px 10px;font-size:13px}
.err{color:var(--bad);margin:10px 0 0}.row{display:flex;gap:8px;margin-top:14px}
table{width:100%;border-collapse:collapse;font-size:13px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mute);font-weight:500}code{font-size:13px}.off{opacity:.45}.scroll{overflow-x:auto}
</style></head><body>${body}</body></html>`;

export const joinPage = (email, error) => base('加入麻薯', `<div class="wrap"><div class="card">
<h1>加入麻薯</h1><p>你已用 <b>${esc(email)}</b> 登录。第一次访问需要输入邀请码，每个码只能用一次，用后绑定到这个邮箱。</p>
<form method="post" action="/_gate/join"><div class="row"><input name="code" placeholder="邀请码，例如 ABCDE-FGH23" autocomplete="off" autofocus required></div>
${error ? `<p class="err">${esc(error)}</p>` : ''}
<div class="row"><button type="submit">加入</button></div></form>
<p style="margin-top:18px;font-size:13px">邮箱不对? <a href="/_gate/logout">换个邮箱登录</a></p></div></div>`);

export const deniedPage = () => base('需要登录', `<div class="wrap"><div class="card">
<h1>需要登录</h1><p>请从麻薯的正式地址打开，用邮箱验证码登录后访问。</p></div></div>`);

export const adminPage = () => base('麻薯管理', `<div class="wrap wide">
<h1>麻薯管理</h1><p>邀请码只能用一次，用后绑定到兑换人的邮箱。撤销成员后对方立刻无法打开任何页面。</p>
<h2>生成邀请码</h2><div class="card"><div class="row" style="margin:0">
<input id="note" placeholder="备注，例如 给张三" style="flex:3;letter-spacing:0"><input id="count" type="number" min="1" max="20" value="1" style="flex:0 0 80px" title="数量">
<button id="gen">生成</button></div><p id="made" style="margin-top:10px"></p></div>
<h2>邀请码</h2><div class="card scroll"><table id="inv"></table></div>
<h2>成员</h2><div class="card scroll"><table id="mem"></table></div>
<h2>最近访问 (200 条)</h2><div class="card scroll"><table id="views"></table></div></div>
<script>
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const t=s=>s?new Date(s).toLocaleString('zh-CN',{hour12:false}):'';
const post=(u,b)=>fetch(u,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(b)}).then(r=>r.json());
async function load(){const s=await fetch('/_gate/api/admin/state').then(r=>r.json());
inv.innerHTML='<tr><th>邀请码</th><th>备注</th><th>状态</th><th>兑换邮箱</th><th>兑换时间</th><th></th></tr>'+s.invites.map(i=>{
const st=i.revoked?'已作废':i.used_by?'已使用':'未使用';
return '<tr class="'+(i.revoked?'off':'')+'"><td><code>'+esc(i.code)+'</code></td><td>'+esc(i.note)+'</td><td>'+st+'</td><td>'+esc(i.used_by)+'</td><td>'+t(i.used_at)+'</td><td>'+
(i.used_by?'':'<button class="ghost" data-k="invite" data-v="'+esc(i.code)+'" data-a="'+(i.revoked?'restore':'revoke')+'">'+(i.revoked?'恢复':'作废')+'</button>')+'</td></tr>'}).join('');
mem.innerHTML='<tr><th>邮箱</th><th>邀请码</th><th>加入时间</th><th>最近访问</th><th>浏览次数</th><th></th></tr>'+s.members.map(m=>
'<tr class="'+(m.revoked?'off':'')+'"><td>'+esc(m.email)+'</td><td><code>'+esc(m.invite_code)+'</code></td><td>'+t(m.joined_at)+'</td><td>'+t(m.last_seen)+'</td><td>'+m.views+'</td><td>'+
(m.invite_code==='admin'?'管理员':'<button class="ghost" data-k="member" data-v="'+esc(m.email)+'" data-a="'+(m.revoked?'restore':'revoke')+'">'+(m.revoked?'恢复':'撤销')+'</button>')+'</td></tr>').join('');
views.innerHTML='<tr><th>时间</th><th>邮箱</th><th>页面</th></tr>'+s.views.map(v=>'<tr><td>'+t(v.at)+'</td><td>'+esc(v.email)+'</td><td>'+esc(v.path)+'</td></tr>').join('');}
document.addEventListener('click',async e=>{const b=e.target.closest('button[data-k]');if(!b)return;
await post('/_gate/api/admin/'+b.dataset.k+'/'+b.dataset.a,b.dataset.k==='invite'?{code:b.dataset.v}:{email:b.dataset.v});load();});
gen.onclick=async()=>{const r=await post('/_gate/api/admin/invites',{note:note.value,count:count.value});
made.innerHTML='新码: '+r.codes.map(c=>'<code>'+c+'</code>').join(' , ');note.value='';load();};
load();
</script>`);
