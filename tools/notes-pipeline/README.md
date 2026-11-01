# Notes pipeline

Publishes Knowledge Base notes to `notes/` (see the Notes handover doc for the field rules).

Sources and codes: AC (AceCamp, incl. the `acecamp 2/` mirror), TB (Third Bridge), GP (GuidePoint),
9K (MeritForum + top-level `YYMMDD - Merit ...` audio transcripts), Substack (incl. top-level copies
not yet in `Substack/`), FUNDA (`Funda/` md + pdf, slug prefix `funda`, meta `Funda · date`),
SA (`SemiAnalysis/` pdf, slug prefix `sa`, meta `SemiAnalysis · date`).
PDF-sourced notes (FUNDA/SA) embed the original as `doc.pdf` in an iframe (render.py copies it from the record `path`); md-sourced FUNDA notes stay as text.
Call = own expert calls (top-level `(audio)` files, any date; meta `Expert Call · date`).
Not published: FactSet, Tegus, VIC, 医药周报, research-output.

1. Stage the window's source files from the Knowledge Base into `<kb>` (same relative layout).
2. `python3 collect.py <kb> <repo> <since> <new_src_since> <ac_times.json> records.json`
   lists and dedupes (Nutstore conflict copies, mirror vs `Acecamp/`, top-level copies, already-published
   date + original title) and converts bodies to HTML. `ac_times.json` maps AceCamp articleId to
   "YYYY-MM-DD HH:MM" from the mirror (optional).
3. Write `meta.json`: `[{id, name, sector, tags, summary}]` per record (handover sec. 4; tags from the fixed vocabulary).
   `summary` (Caffrey, 2026-11-01): a list of 5-10 Chinese sentences, read from the full note (PDFs too), giving its core view,
   key facts and the most useful numbers. render.py shows it as a 核心摘要 box above the body and warns when it is missing.
   New notes only; existing pages were not backfilled.
4. `python3 render.py <repo> records.json meta.json` writes pages, re-sorts `notes/index.html`, updates the home count.
