# MkDocs GUI hub, recipes, and inline icons

## Files changed

- `docs/index.md` — analysis bullet wording, *in vivo*, desktop and browser GUIs
- `docs/users/index.md` — *in vivo*, history menu inline icon, sample data
- `docs/users/gui.md` — hub reorg: home PNG + legend, performance paragraph, hamburger PNG, toolbar/context-menu bullets, analysis links only, narrower widths
- `docs/users/gui-experiment-metadata.md` — **new**
- `docs/users/gui-image-header.md` — **new**
- `docs/users/gui-app-config.md` — **new**
- `docs/users/recipes/index.md` — analysis-only hub (removed General workflows)
- `docs/users/recipes/velocity-analysis.md` — workflow, results section, narrower screenshot
- `docs/users/recipes/diameter-analysis.md` — workflow, results section
- `docs/users/recipes/sum-intensity-analysis.md` — Peak Detect naming, results section, narrower screenshot
- `docs/users/recipes/analyses-from-velocity/velocity-event-analysis.md` — results section, JSON wording
- `docs/users/recipes/analyses-from-velocity/heart-rate-analysis.md` — saved-files link
- `docs/assets/gui/clouscope-home-page.png` → `docs/assets/gui/cloudscope-home-page.png` (rename)
- `docs/developers/mkdocs-style.md` — inline Material icon pattern documented
- `mkdocs.yml` — nav entries for three GUI detail pages

## Summary of implementation

- **Inline icons:** `:material-menu:{ .middle }` per `pymdownx.emoji` + Material SVG generator in `mkdocs.yml`; documented in mkdocs-style.md with home page as prior art.
- **GUI hub** (`gui.md`): overview screenshot with legend, consolidated sample-data section, history menu with left-aligned PNG, detailed toolbar/context-menu docs, analysis panel table linking to recipes.
- **New pages:** experiment metadata, image header, app config (text-only until user PNGs).
- **Recipes hub:** analysis tables only; saved-file detail on dedicated pages.
- **Recipe pages:** full workflows and “Results and reproducibility” sections; GUI screenshots on recipe pages not on gui hub.

## Tests added or modified

None (documentation-only).

## Exact test commands run

```bash
uv run mkdocs build --strict
```

## Test results

`uv run mkdocs build --strict` — **passed** (exit 0).

## Concerns or follow-ups

- ~~User to provide PNG assets for experiment metadata, image header, and app config pages.~~ Added in follow-up (experimental-metadata-view, image-header-view, options-view, diameter-analysis-view).
- ~~Diameter recipe still has no panel screenshot.~~ Added `diameter-analysis-view.png`.
- Architecture SVG still says “scientific backend” (unchanged).

## Follow-up (screenshots)

Added GUI panel screenshots and expanded copy:

- `docs/users/gui-experiment-metadata.md` — `experimental-metadata-view.png`; immediate apply, preset dropdowns
- `docs/users/gui-image-header.md` — `image-header-view.png`; read-only vs editable calibration
- `docs/users/gui-app-config.md` — `options-view.png`; percentile display-only note
- `docs/users/recipes/diameter-analysis.md` — `diameter-analysis-view.png`
