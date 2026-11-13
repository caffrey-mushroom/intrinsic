# 麻薯 gate

Serves the whole repo as a team-only site on Cloudflare:

- Cloudflare Access asks for an email one-time code (proves who you are).
- The worker (`src/worker.js`) decides membership: first visit needs a single-use invite code, which then binds to that email. Admins (repo variable `MASHU_ADMIN_EMAILS`) manage codes and members at `/_gate/admin`.
- Every HTML page gets `/_gate/comments.js` injected: select text, comment in the right margin, replies, resolve. Stored in D1. `index.html` and `white.html` share one comment thread. A faint viewer-email watermark is added.
- Pages themselves are never edited; old `caffrey-mushroom.github.io/intrinsic/` links are rewritten on the fly.

Deploy: `.github/workflows/mashu-deploy.yml` on every push to main (skips until the `CLOUDFLARE_API_TOKEN` secret exists). `setup.mjs` creates the D1 database, email-code login and Access app if missing.

Local: `npm install && printf 'DEV_EMAIL=me@example.com\nADMIN_EMAILS=me@example.com\n' > .dev.vars && npm run dev`, then `?as=other@x.com` to act as someone else.
