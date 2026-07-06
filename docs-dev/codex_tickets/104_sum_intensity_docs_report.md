# 104 — Sum intensity MkDocs documentation

## Files changed

- `mkdocs.yml`
- `docs/index.md`
- `docs/users/index.md`
- `docs/users/gui.md`
- `docs/users/recipes/index.md`
- `docs/users/recipes/sum-intensity-analysis.md` (new)
- `docs/scientists/index.md`
- `docs/scientists/sum-intensity-analysis.md` (new)
- `docs/scientists/notebooks.md`
- `docs/scientists/reproducibility.md`
- `docs/api/index.md`
- `docs/api/analysis-core.md`
- `docs/api/sum-intensity-analysis.md` (new)
- `docs/developers/index.md`
- `docs/assets/cloudscope-architecture.svg`

## Summary of implementation

Added sum intensity analysis to the MkDocs site as a third primary analysis alongside
velocity and diameter:

- End-user recipe with GUI screenshot (`assets/gui/sum-intensity-analysis-view.png`)
- Data Scientist page (pipeline, presets, results; parameter table deferred)
- API page via mkdocstrings for `SumIntensityAnalysis`
- Nav entries in `mkdocs.yml` for recipe, scientist, and API sections
- Hub/index updates (home, end user, recipes, scientists, API, reproducibility, developers)
- GUI guide section for the sum intensity panel
- Architecture diagram label updated

Deferred per ticket steering:

- `docs/notebooks/sum-intensity-analysis.ipynb` edits
- `docs/schemas/sum_intensity_detection_parameters.md` schema snippet (scientist page links to API instead)

## Tests added or modified

None (documentation-only change).

## Exact test commands run

```bash
uv sync --group docs
uv run mkdocs build --strict
```

## Test results

`uv run mkdocs build --strict` — passed (exit 0).

## Concerns or follow-ups

- Add `docs/schemas/sum_intensity_detection_parameters.md` when a schema export workflow exists (match velocity/diameter `--8<--` pattern on scientist page).
- Refresh `sum-intensity-analysis.ipynb` terminology and sample data path.
- Capture additional GUI screenshots if the sum intensity panel layout changes.
