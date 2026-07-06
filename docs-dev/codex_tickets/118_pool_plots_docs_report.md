# Pool plots documentation (first pass)

## Files changed

- `docs/users/pool-plots.md` — **new** dedicated overview page
- `docs/index.md` — pool plots mention and link
- `docs/users/gui.md` — legend + Pool plots section
- `docs/users/index.md` — link in workflow and Where to go next
- `docs/users/recipes/index.md` — See also link
- `docs/users/recipes/velocity-analysis.md` — Next steps link
- `docs/users/recipes/sum-intensity-analysis.md` — See also link
- `mkdocs.yml` — nav entry `Pool plots: users/pool-plots.md`

## Summary

First-pass end-user documentation for the Home page **Pool Plots** panel (velocity and Peaks
tabs). Documents live folder-wide sync, left-control screenshots, swarm plot example, Copy full
table / Copy stats clipboard export, and an info admonition that detailed control docs are coming
soon.

Assets used: `pool-plots/pool-plot-left-toolbar-top.png`, `pool-plot-left-toolbar-middle.png`,
`pool-plot-sample-plot-1.png`. Bottom toolbar screenshot (`pool-plot-left-toolbar-bottom.png`)
not yet added by user.

## Tests added or modified

None.

## Exact test commands run

```bash
uv run mkdocs build --strict
```

## Test results

`uv run mkdocs build --strict` — **passed** (exit 0).

## Concerns or follow-ups

- Add `pool-plot-left-toolbar-bottom.png` when available.
- Expand page with per-control documentation (plot presets, layout, pre-filters, plot types).
- Standalone `/pool` window and desktop **Open Pool** could get a short subsection later.
