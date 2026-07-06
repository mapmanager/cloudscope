# Ticket 001: Plotly wheel zoom flicker fix

## Files changed

- `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
- `src/cloudscope/views/primary_image_view.py`
- `tests/nicewidgets/test_plotly_viewer_state.py`
- `tests/cloudscope/test_x_range_view_wiring.py`

## Summary of implementation

Replaced v8–v10 relayout classification machinery with a **viewport observer** architecture:

1. **Thin `_on_plotly_relayout`**: ROI shapes immediate; bracket-key axis relayouts schedule debounced viewport settle only; normalized-only relayouts ignored.
2. **Debounced viewport settle** (~120ms): reads live `plotDiv.layout` from the browser, emits `on_x_range_changed`, refreshes raster content.
3. **Content-only apply**: same trace type → `Plotly.restyle`; PNG↔heatmap → `Plotly.react(..., plotDiv.layout, ...)`; no `_plot.update()` on wheel path.
4. **`set_x_axis_range`**: x-axis-only `Plotly.relayout`; no-op when x already matches display cache; does not reset y after wheel zoom.
5. **Skip-if-adequate**: skips raster apply when mode, level, and clip bounds already cover the visible viewport.
6. **CloudScope primary image view**: breaks viewer → event bus → `set_x_axis_range` self-echo with `_viewer_originated_x_range`.

Removed: `_ignore_next_programmatic_relayout`, pending/active relayout tracking, normalized follow-up heuristics, diagnostic `plotly_restyle` / `plotly_autosize` handlers, verbose `pprint` logging.

## Tests added or modified

- `tests/nicewidgets/test_plotly_viewer_state.py` — viewport settle, live viewport read, x-only `set_x_axis_range`, `Plotly.react` cross-type apply
- `tests/cloudscope/test_x_range_view_wiring.py` — viewer-originated x-range does not round-trip to viewer

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_viewer_state.py tests/nicewidgets/test_plotly_viewer_x_range.py tests/cloudscope/test_x_range_view_wiring.py src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py -q
```

## Test results

80 passed (nicewidgets plotly viewer tests) + 13 passed (cloudscope x-range wiring), run separately due to NiceGUI test isolation.

```bash
uv run pytest tests/nicewidgets/test_plotly_viewer_state.py tests/nicewidgets/test_plotly_viewer_x_range.py src/nicewidgets/raster_viewer/tests/frontend/test_plotly_viewer.py -q
uv run pytest tests/cloudscope/test_x_range_view_wiring.py -q
```

## Concerns or follow-ups

- Manual UX validation in CloudScope (wheel zoom on primary image + 1D chart sync) still required.
- If PNG↔heatmap `Plotly.react` still flashes in browser, follow-up ticket for dual-trace architecture (Option 2).
- Reference image view has no x-range loop; benefits from raster-only fixes automatically.

## Revert anchor

```bash
git reset --hard e34e7e16592985c83a6fa74379b517b68d7e4f3e
```
