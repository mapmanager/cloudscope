# 035 — Edit F0 plot x-range emit + Manual H-line drag

## Summary of implementation

1. **X-range emit from F0 plot** — `_f0_plot` uses the same
   `on_x_range_changed=self._on_plot_x_range_changed` as the primary plot
   (no new architecture).

2. **Manual F0 H-line drag** — Plotly line shapes have two endpoints. Vertex
   drags often update only `y0` or only `y1`. The widget previously took
   `y0` only, so dragging the other end looked like a “first point” move and
   could snap back. Now:
   - Position after edit prefers the changed endpoint(s) from the relayout
     payload, then normalizes to a full paper-width horizontal line.
   - Scoped CSS disables pointer events on Plotly shape vertex circles so the
     line body is dragged as a unit (Plotly community guidance for
     `config.edits.shapePosition`).

## Files changed

- `src/cloudscope/views/sum_intensity_plot_view.py`
- `src/nicewidgets/plotly_plot/widget.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`
- `docs-dev/cursor_tickets/035_edit_f0_xrange_and_hline_drag_report.md`

## Tests added or modified

- Single-endpoint `y1` drag moves the whole H-line
- Dual-endpoint skew uses mean then normalizes paper span

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py \
  tests/cloudscope/test_sum_intensity_plot_view.py -q
```

## Test results

```text
102 passed, 1 warning in 1.31s
```

## Concerns or follow-ups

- Live native-app verify that Manual F0 body-drag stays horizontal during gesture
  (CSS + normalize). Unit tests cover post-relayout normalization only.
