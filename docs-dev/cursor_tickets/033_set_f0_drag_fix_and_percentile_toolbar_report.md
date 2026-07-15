# 033 — Set F0 drag fix + percentile / Compute auto F0 toolbar

## Summary of implementation

### Drag fix (Manual F0)

- Stop putting Plotly shape `name` / `showlegend` on measurement lines unless `show_legend=True` (Set F0 Manual uses `show_legend=False`).
- After a Manual H-line drag, normalize the shape so it stays a full paper-width horizontal line (`y0=y1`, `x0=0`, `x1=1`).
- **Auto F0** is no longer a layout measurement shape (avoids `shapePosition` fighting `editable=False`). It is a non-interactive **line trace** (`Auto F0`, dotted cyan) that can appear in the legend when the plot legend is on.

### Toolbar

- Percentile `ui.number` (seeded from analysis `baseline_percentile`)
- **Compute auto F0** → `get_percentile_f0_baseline(percentile=...)` → update Auto label + Auto trace only (Manual line unchanged)
- Accept still commits **manual only**

## Files changed

- `src/nicewidgets/plotly_plot/models.py` — optional `line_color` / `line_dash` on `PlotlyTraceData`
- `src/nicewidgets/plotly_plot/widget.py` — trace line style; omit shape legend keys; normalize H-line after drag
- `src/cloudscope/views/sum_intensity_plot_toolbar.py` — percentile + Compute auto F0
- `src/cloudscope/views/sum_intensity_plot_view.py` — Auto as trace; Manual as shape without legend
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `tests/cloudscope/test_sum_intensity_plot_view.py`
- `docs-dev/cursor_tickets/033_set_f0_drag_fix_and_percentile_toolbar_report.md`

## Tests added or modified

- Shape without legend omits `name`/`showlegend`
- Horizontal drag normalizes skewed endpoints
- Set F0 enter/exit with Auto trace + Manual shape
- Compute auto F0 updates Auto only

## Exact test commands run

```bash
uv run pytest \
  tests/nicewidgets/test_plotly_plot_widget.py \
  tests/cloudscope/test_sum_intensity_plot_view.py
```

## Test results

```text
99 passed, 1 warning in 1.40s
```

## Concerns or follow-ups

- Manual F0 is intentionally **not** in the Plotly legend (toolbar labels name it). Auto F0 remains a legend-capable trace.
- Browser verify Manual drag moves the whole H-line after this change.
- Future: Accept percentile vs Accept manual as separate commit actions.
