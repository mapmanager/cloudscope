# 068 — CHANGELOG draft for CloudScope v0.2.0

## Goal

Promote and extend `CHANGELOG.md` Unreleased notes into a `[0.2.0]` section
ready for the v0.2.0 cut, including gaps since the last CHANGELOG pass
(~2026-07-07) and agreed scope for AcqStore Server / AcqTrace / dff0.

## Files changed

- `CHANGELOG.md` — empty `[Unreleased]`; new `## [0.2.0] - YYYY-MM-DD` section
- `docs-dev/cursor_tickets/068_changelog_0_2_0_draft_report.md` — this report

## Summary of implementation

1. Moved prior Unreleased package-section content into `[0.2.0]`.
2. Added missing post-0.1.3 / post–July-7 items agreed in chat:
   - acqstore: OME-Zarr, TIFF/reference TIFF export, find_analysis, OIR units,
     calibration, NaN interpolate, AcqTrace/ABF, dff0_diameter_analysis
   - nicewidgets: Set F₀ Plotly helpers; tree selection/scroll fixes
   - cloudscope: Set F₀ GUI, build info, save reference as TIFF, reconnect,
     reference physical axes
   - new `### acqstore_server` section (CHANGELOG only; no public MkDocs)
   - Desktop: CS icons, build-info / CI packaging notes
   - Documentation: request form, Google Analytics
3. Left release date as `YYYY-MM-DD` placeholder until tag day.
4. Left empty `[Unreleased]` section headers for ongoing work.

## User decisions (locked)

| Topic | Decision |
|---|---|
| AcqStore Server | CHANGELOG only; docs stay in `docs-dev/acqstore_server/` |
| CHANGELOG structure | New `### acqstore_server` section |
| AcqTrace / ABF / dff0 | Include in CHANGELOG; do **not** add to MkDocs |
| Release date | Fill on tag day |

## Tests added or modified

None (documentation-only).

## Exact test commands run

None.

## Test results

N/A.

## Concerns or follow-ups

- MkDocs pass: done in `069_mkdocs_0_2_0_docs_pass_report.md`.
- Desktop get-app wording: landing / `users/install` / nav updated for form-based
  distribution (no public GitHub download CTA).
- Before tag: bump `pyproject.toml` / `uv.lock` to `0.2.0`, replace
  `YYYY-MM-DD`, run `uv run python scripts/check_release.py v0.2.0`.
- Do not bump version or tag in this ticket.
