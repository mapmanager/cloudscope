# 069 — MkDocs docs pass for CloudScope v0.2.0

## Goal

Final public MkDocs updates for user-facing items in the `[0.2.0]` CHANGELOG,
excluding AcqStore Server, AcqTrace/ABF, and `dff0_diameter_analysis`.

## Files changed

- `docs/users/recipes/sum-intensity-analysis.md` — Edit F0 (baseline) recipe section
- `docs/scientists/sum-intensity-analysis.md` — Edit F0 GUI → detection params note
- `docs/users/gui.md` — Save As Tif..., Save Reference As Tif, App Info build metadata
- `docs/users/saved-files.md` — Export TIFF section
- `docs/users/supported-file-formats.md` — physical units / OME-Zarr load note
- `docs-dev/cursor_tickets/069_mkdocs_0_2_0_docs_pass_report.md` — this report

## Summary of implementation

Implemented agreed items #1–#5 only:

1. Peak-detection recipe: **Edit F0** context menu, Manual / Auto Set buttons, Close.
2. Scientist sum-intensity page: ties Edit F0 to `baseline_method` / params.
3. GUI guide: file-list **Save As Tif...**, Reference Image export + metadata, App Info
   build metadata wording.
4. Saved files: **Export TIFF** table (distinct from JSON/CSV sidecars).
5. Supported formats: OIR/CZI auto physical units; OME-Zarr load note; link to Image Header
   and reference TIFF export.

Skipped per plan: API prose (#6), tree/reconnect internals, packaging, analytics, batch,
t/z slider pages. No `mkdocs.yml` nav changes. README.md untouched.

## Tests added or modified

None (documentation-only).

## Exact test commands run

None.

## Test results

N/A.

## Concerns or follow-ups

- Before tag: bump `pyproject.toml` / `uv.lock` to `0.2.0`, replace CHANGELOG
  `YYYY-MM-DD`, run `uv run python scripts/check_release.py v0.2.0`.
- Optional later: batch-analysis GUI page; t/z slider blurb on Main image viewer.
- Optional: local `uv run mkdocs build` smoke check before docs deploy.
- Follow-up desktop CTA wording (landing + install + nav + users index) done in-session
  after 069; see chat / `docs/index.md` + `docs/users/install.md`.
- README shortened + desktop CTA points at docs install page (explicit README pass).
- `request-desktop-app.md` title shortened; back-link to install page.
