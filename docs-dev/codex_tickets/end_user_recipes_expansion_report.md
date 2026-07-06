# End User recipes expansion

## Files changed

- `mkdocs.yml` — nested Recipes nav
- `docs/users/recipes/index.md` — recipe hub (new)
- `docs/users/recipes/velocity-analysis.md` — new
- `docs/users/recipes/diameter-analysis.md` — new
- `docs/users/recipes/analyses-from-velocity/index.md` — new
- `docs/users/recipes/analyses-from-velocity/velocity-event-analysis.md` — new
- `docs/users/recipes/analyses-from-velocity/heart-rate-analysis.md` — new
- `docs/users/recipes.md` — removed (content split into hub + dedicated pages)
- `docs/users/index.md` — updated recipes link
- `docs/users/gui.md` — link to velocity recipe
- `docs/users/install.md` — updated recipes link
- `docs/scientists/notebooks.md` — cross-link to heart rate recipe
- `docs/developers/mkdocs-style.md` — recipe hub / nested nav patterns

## Summary of implementation

Expanded End User Recipes into a nested nav section: hub page, dedicated velocity and diameter
GUI recipes, and an **Analyses from velocity** subsection with velocity event analysis (GUI, embedded
in Velocity panel) and heart rate analysis (notebook only, with info block noting no GUI yet).

## Tests added or modified

None.

## Exact test commands run

```bash
uv run mkdocs build --strict
```

## Test results

`uv run mkdocs build --strict` — **passed**.

## Concerns or follow-ups

- Heart rate notebook still mentions GUI exploration; end-user recipe correctly states no GUI. Notebook text fix deferred.
- No screenshot for diameter panel or velocity Events section yet.
