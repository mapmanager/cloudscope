# 019 — Plot-view typed session state pilot

Status: implemented

## Goal

Pilot the reconnect state pattern from `docs-dev/cloudscope/dev-roadmap-reconnect.md`
on the two 1D plot views, before touching the app-level state contract or page
chrome. Concretely:

1. Give `PlotlyPlotDisplayOptions` real serialization (`to_dict` / `from_dict`).
2. Simplify `PlotlyPlotWidget.__init__` to take one `display_options` object
   instead of scattered `theme` / `show_*` booleans.
3. Introduce typed, serializable per-view state dataclasses
   (`AcqAnalysisPlotViewState`, `SumIntensityPlotViewState`) so the views stay
   thin: they build the state object on export and consume it on apply, and the
   dataclass owns schema versioning, key validation, and nested display-option
   serialization.
4. Capture and restore sum-intensity per-series overlay visibility.

Chrome cleanup (`HomePageChromeState`) and `HomePageSessionSnapshot`
serialization are intentionally **out of scope** and deferred to a follow-up per
the agreed implementation order.

## Files changed

- `src/nicewidgets/plotly_plot/display_options.py`
  - Added `to_dict()` (JSON-friendly, theme normalized to a plain string) and
    `from_dict()` (ignores unknown keys, defaults missing keys, normalizes
    theme).
- `src/nicewidgets/plotly_plot/widget.py`
  - `PlotlyPlotWidget.__init__` now takes `display_options: PlotlyPlotDisplayOptions | None`
    and no longer takes `theme`, `show_legend`, `show_x_axis_labels`,
    `show_y_axis_labels`. The widget owns a private copy (`dataclasses.replace`)
    and derives `self._theme` from it.
  - Added `set_series_visible_state(series_name, visible)`: sets desired
    visibility even for a series that is not loaded yet (no `KeyError`);
    restyles immediately when the series is already loaded. Used to restore
    visibility before plot data exists on reconnect.
- `src/cloudscope/views/acq_analysis_plot_view.py`
  - Added `AcqAnalysisPlotViewState` dataclass (`selection_guard`,
    `display_options`, `events_visible`, `schema_version`) with
    `to_dict`/`from_dict`.
  - `export_session_state` / `apply_session_state` now delegate to the dataclass
    (thin view). Child `PlotlyPlotWidget` is constructed with a
    `PlotlyPlotDisplayOptions`.
- `src/cloudscope/views/sum_intensity_plot_view.py`
  - Added `SumIntensityPlotViewState` dataclass (`selection_guard`,
    `display_options`, `series_visibility`, `schema_version`) with
    `to_dict`/`from_dict`.
  - `export_session_state` captures live per-series visibility via
    `_current_series_visibility()`; `apply_session_state` restores it via
    `_apply_series_visibility()` (uses `set_series_visible_state`). Child widget
    constructed with a `PlotlyPlotDisplayOptions`.
- Tests (see below).

## Design note (reconnect timing)

The widget constructor now accepts `display_options`, but per-view reconnect
blobs are still applied **post-build** via the existing
`HomePageSessionReconnectRestore` event → `apply_session_state` path, because
that event fires after the page (and child widgets) are rebuilt. This keeps the
working reconnect flow intact; the constructor change is an API/DRY cleanup, not
a change to restore delivery. Restored series visibility is written into the
widget in `apply_session_state`, and the subsequent selection-driven
`_refresh_plot` (from the default `on_session_reconnect_restore`) honors it.
`del visible` in `_on_series_visibility_changed` was left as-is (out of scope for
this pilot).

## Tests added / modified

- `tests/nicewidgets/test_plotly_plot_widget.py`
  - Updated three constructors that used dropped kwargs to pass
    `display_options=PlotlyPlotDisplayOptions(...)`.
  - Added: display-options round trip; `from_dict` ignores unknown / defaults
    missing; `set_series_visible_state` stores pending visibility for an
    unloaded series; `set_series_visible_state` restyles a loaded series.
- `tests/cloudscope/test_acq_analysis_plot_view.py`
  - Added: `AcqAnalysisPlotViewState` round trip; `from_dict` requires keys.
- `tests/cloudscope/test_sum_intensity_plot_view.py`
  - Extended `_FakePlot` with display-option setters, `set_series_visible_state`,
    and a `display_options` attribute.
  - Added: `SumIntensityPlotViewState` round trip; export captures series
    visibility; apply restores series visibility and display options.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_plot_widget.py tests/cloudscope/test_acq_analysis_plot_view.py tests/cloudscope/test_sum_intensity_plot_view.py -q
uv run pytest tests/nicewidgets tests/cloudscope -q
```

## Test results

- Focused plot/widget tests: 122 passed.
- Full nicewidgets + cloudscope suites: 1404 passed, 5 skipped (missing OIR
  fixtures, unrelated), 5 warnings (pre-existing "coroutine never awaited" in
  stale-refresh tests).

## Concerns / follow-ups

- One pre-existing Ruff long-line warning in
  `acq_analysis_plot_view.py::_empty_message` (line unchanged by this ticket).
- Follow-up (deferred, as agreed): define `HomePageRestorableState` / real
  app-state contract, add `HomePageSessionSnapshot.to_dict/from_dict`, and clean
  up stale `HomePageChromeState` fields (`analysis_plot_open`,
  `reference_image_open`, `velocity_pool_open`) plus add page chrome fields
  (`left_toolbar_open`, splitters, pool tab).
- True constructor-time restore (reading the per-view blob before build) is not
  implemented; current post-build apply is retained deliberately.
