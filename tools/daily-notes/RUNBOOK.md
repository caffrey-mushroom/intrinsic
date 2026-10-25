# Daily notes runbook

Two issues a day, Asia/Shanghai, published to `track/daily-notes/<date>-<am|pm>/`:

| Edition | Fires | Window (by KB file mtime = ingest time) |
|---|---|---|
| 早间版 `am` | 05:05 | previous day 20:00 → 05:00 |
| 晚间版 `pm` | 20:05 | 05:00 → 20:00 same day |

Reference issue: `track/daily-notes/2026-10-24-pm/` (layout, tone, section order). Reuse its HTML as the template.

## Steps

1. **List the window.** On the device (Knowledge Base folder), `find Acecamp GuidePoint ThirdBridge MeritForum Substack Funda SemiAnalysis <top-level YYYY-MM-DD> -type f -newermt <start> ! -newermt <end>`, drop `*.partN.md`, Nutstore conflict copies (`name N.md` when `name.md` exists), FactSet, `(audio)` own calls. Also check `acecamp 2/<date>/` for articleIds not yet in `Acecamp/`.
2. **Make sure every note has a site page first.** The Notes routine runs 05:55 / 17:55, so notes ingested after its last run have no page yet. For any file in the window without a page under `notes/` (match on date + `原标题`), run the Notes pipeline for just those files (`tools/notes-pipeline/README.md`: stage, `collect.py`, write meta, `render.py`). `collect.py` dedupes on date + original title, so the next Notes run will not duplicate them.
3. **Score and read.** Keyword-score each file by layer (demand/model, cloud/neocloud, GPU/ASIC, memory, power, SPE, CPU). Read the high scorers in full or their summaries; read nothing from `research-output/`.
4. **Write the issue** (Chinese, plain language, numbers in sentences, ticker-first; rota-design web track): 主线 (2–3 serif sentences) · 先读这 N 篇 · 分层速览 · 反方信号 · 数字速查 (vs the weekly thesis baselines in KB `research-output/<track>-thesis|baseline/`) · 窗口与篇目. Every note title and source tag links to `https://caffrey-mushroom.github.io/intrinsic/notes/<slug>/`. If the window has no new files, do not publish an issue: just tell Caffrey in one line that no new notes came in (Caffrey, 2026-10-25). If it has files but nothing AI-related, publish a short issue that says so.
5. **Publish:** `python3 tools/daily-notes/publish.py . <issue.html> <date> <am|pm> "<window>" "<one-line desc>" <n_in_window> <n_relevant>`, then commit and push to `main` (`git pull --rebase` first; the Notes routine pushes to the same branch).
6. **Email the issue** to Caffrey's work address anran.chen@marswalk.com (Caffrey, 2026-10-25), from the connected Gmail account (anran.caffrey@gmail.com): `python3 tools/daily-notes/email.py . <date>-<am|pm> /tmp/mail.html` prints the subject and writes the HTML body (主线 + 先读这 N 篇 with absolute links + link to the full issue; Times New Roman / STKaiti inline styles). Send with `mcp__Gmail__send_message`, `htmlBody` = that file, `body` = a plain-text 主线. No email when the window had no new files.
7. **Tell Caffrey** in the Daily notes thread: one or two lines with the site link, the one note to read first, and whether the email went out.

Known data issue: GP file `2026-10-24-coreweave-and-gpu-financing-...md` holds an ESMO melanoma transcript; its Notes page has the wrong body.
