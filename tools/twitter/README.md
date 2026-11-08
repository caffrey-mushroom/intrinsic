# twitter

The home page ends with one row named `twitter`. The index lists every Beijing date that has been published. Morning (`am`, 早报) and evening (`pm`, 晚报) are different rows. A later revision of the same date and edition replaces that one page. An older revision is ignored. Adding the next day does not remove the previous day.

Mail delivery is not part of this tool.

## Handoff for the next edition

Put two files where the publisher can read them. Do not commit them.

`source.html` — the digest HTML body only. No message headers, recipient list, or raw mail file.

`meta.json`

```json
{
  "date": "2026-11-09",
  "edition": "am",
  "revision": "2026-11-09T01:05:00Z",
  "window": "2026-11-08 21:30:00 至 2026-11-09 09:30:00 北京时间"
}
```

`date` is the Beijing date on the edition. `edition` is `am` or `pm`. `revision` is the edition's own publish time in ISO-8601. A larger timestamp wins for that date and edition. Use the time the revised edition was sent, not a post time from inside the digest.

```bash
python3 tools/twitter/publish.py . source.html \
  --date 2026-11-09 --edition am --revision 2026-11-09T01:05:00Z \
  --window "2026-11-08 21:30:00 至 2026-11-09 09:30:00 北京时间"
```

The command rewrites only `twitter/<date>-<am|pm>/index.html` for that key, then rebuilds `twitter/index.html`, `twitter/editions.json`, and the home row. Other edition directories are left in place.

Printed status:

- `add` — first time this date and edition is published
- `replace` — this revision is newer than the one already stored
- `unchanged` — the same revision and the same content are already stored
- `skip` — the incoming revision is older; the stored page stays

Commit `index.html` and `twitter/`, then push to `main`. GitHub Pages serves the repository root. Nothing in this repo sends mail or runs on a schedule.

Example: publishing 2026-11-09 leaves `twitter/2026-11-08-pm/` on the 2026-11-08 evening revision. A late copy of an earlier 2026-11-08 evening file does not replace it.
