# Weekly sources appendix

Adds "附 本期引用原文" to the end of a weekly issue: every note the issue read (tier A/B/C/S from
`all_out.json`, tier X dropped), linked to its page under `notes/`. Notes with no page (Tegus,
FactSet, VIC, or not yet published by the notes pipeline) are listed without a link, with the reason.

Note links carry `?from=<issue dir>`; `notes/back.js` (loaded by every note page) turns the note's
back link into "← 返回周报" pointing at the issue's `#weekly-sources`. Browser back works too.

Matching: notes/index.html rows give (date, source, original title, slug). A KB record matches on
date + normalized title, then on the KB file name (date-prefixed kebab of the original title), then on
the longest title prefix within +-1 day (+-3 for Substack).

Usage (run after the issue page is written into the repo, before commit):

    python3 tools/weekly-sources/sources.py <repo> <kb>/research-output/<date>-<track>-weekly/data/all_out.json \
        track/<group>/<issue>/index.html

- Idempotent: re-running replaces the block between `<!-- weekly-sources:start/end -->`.
- Placement: before the page's last `<p class="foot">`, else at the end of the content column.
- Bundled issues (GPU · CPU · Foundry, CSP + Neocloud): pass several all_out.json comma-separated; duplicates are merged.
- `--report` prints match counts and unlinked items without touching a page.
- `--html out.html` writes only the section, for builds that place it themselves.

Run it against the repo after `git pull --rebase`, so notes published earlier that night are matched.
