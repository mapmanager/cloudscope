# MkDocs GUI and saved-files documentation update

## Files changed

- `docs/users/gui.md` — rewritten: sample-data getting started, desktop/web load/save tabs, history menu item list, left-toolbar map, diameter panel section, tone/wording updates
- `docs/users/saved-files.md` — **new** page describing JSON/CSV saved formats and Save Selected / Save All
- `docs/users/index.md` — sample data from history menu, saved-files link, tone pass
- `docs/users/recipes/index.md` — sample data menu names, saved-files link, visualize wording
- `docs/users/install.md` — next-steps link to saved-files page
- `docs/index.md` — site home tone pass (reduce redundant “scientific”)
- `docs/developers/index.md` — shared backend wording
- `docs/api/index.md` — workflow wording
- `docs/scientists/index.md` — image format wording
- `mkdocs.yml` — nav entry for saved-files page; site_description tone update

## Summary of implementation

- End-user GUI guide now documents the top header (CloudScope label, load/save, history menu with explicit items including **Load Velocity Sample Data** and **Load Diameter Sample Data**), desktop vs web tabs, and the expanded nine-item left toolbar with tooltips and links to detailed sections.
- Added **Saved file formats** page covering JSON contents (metadata, ROIs, analyses including velocity events), CSV filenames per analysis type, and Save Selected / Save All behavior.
- Added **Diameter analysis panel** section in `gui.md` (text + recipe link; no screenshot asset available).
- Site-wide tone pass on home and key index pages: “raw image” / “visualize” for users; trimmed redundant “scientific” where context already implies analysis software. Data Scientist pages retain “sidecar” and “scientific behavior” where appropriate.

## Tests added or modified

None (documentation-only change).

## Exact test commands run

```bash
uv run mkdocs build --strict
```

## Test results

`uv run mkdocs build --strict` — **passed** (exit 0).

## Concerns or follow-ups

- No diameter-analysis screenshot in `docs/assets/gui/`; diameter section is text-only until a capture is added.
- **Load Manuscript Velocity 2026** is documented as deployment-conditional (env `CLOUDSCOPE_PRESET_DATA_MANNING`).
- Sample data menu offers velocity and diameter datasets only (no sum-intensity/peak-detect sample item in the GUI menu).
- Architecture SVG still says “scientific backend” (not edited in this pass).
