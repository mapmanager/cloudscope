# 030 — Contrast polish, Plotly Hover Info, App-level x-range sync

## Summary

This ticket combines three changes that all hang off the primary-image /
analysis-plot pair:

* **Part A — Contrast polish.** Widen the `PlotlyRasterViewer` LUT API so the
  `Inverted Gray` 2-stop colorscale propagates end-to-end as a real list (no
  `'Greys'` fallback). Switch the contrast widget's `ui.select` to a
  `{value: label}` mapping so the dropdown shows `Inverted Gray` while the
  wire value stays `inverted_grays`. Tighten the contrast row's column widths
  (LUT `w-32`, range `w-56` without `flex`, min/max labels `w-10`) to keep the
  toolbar from horizontally overflowing.
* **Part B — Plotly Hover Info toggle.** Add a `show_hover_info` option
  (default `False`) and `set_hover_info_visible` setter on
  `PlotlyRasterViewer`. The raster trace's `hoverinfo` is set to `'skip'` when
  disabled, which suppresses Plotly's hover events entirely. A new
  `Hover Info` item lives in the existing Plotly raster context menu next to
  `Plotly Toolbar`.
* **Part C — App-level x-range sync.** Introduce
  `SetPrimaryXRangeIntent` / `PrimaryXRangeChanged` and an `XRangeController`
  that owns `HomePageState.primary_x_range`. Producers are the Plotly raster
  (`_on_plotly_relayout`, `_on_plotly_doubleclick`) and the ECharts widget
  (`_on_datazoom`, `_on_double_click`); both views forward changes through an
  injected callback and consume the resulting state event back into their
  widgets. Reset semantics: file transitions reset to auto, channel changes
  preserve the current range.

## Files changed

### New

* `src/cloudscope/events/x_range.py` — `SetPrimaryXRangeIntent`,
  `PrimaryXRangeChanged`.
* `src/cloudscope/controllers/x_range_controller.py` — `XRangeController` with
  inversion-swap normalization, float-tolerance dedup, and file-id-only reset
  via the existing `FileSelectionChanged`.
* `tests/cloudscope/test_x_range_controller.py`
* `tests/cloudscope/test_x_range_view_wiring.py`
* `tests/nicewidgets/test_plotly_viewer_x_range.py`
* `tests/nicewidgets/test_echart_x_range.py`
* `docs/codex_tickets/030_contrast_polish_hover_info_x_range_sync_report.md`
  (this file).

### Modified

* `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
    * Add `PlotlyColorscale` type alias.
    * Widen `set_heatmap_colorscale` to accept `PlotlyColorscale` (drop
      `str(...)` coercion). `json.dumps` already handles both string and list
      forms when restyling.
    * Add `_sync_hover_info_to_plotly_dict`, `set_hover_info_visible`, and
      `_restyle_hover_info` (uses `hoverinfo='skip'` when off).
    * Add `on_x_range_changed` constructor hook, `_last_applied_x_range`
      echo-suppressor, `_emit_x_range_from_relayout` helper, and
      `reset_x_axis_range`. `set_x_axis_range` records the applied pair;
      `_on_plotly_doubleclick` emits `(None, None)` on reset.
* `src/nicewidgets/raster_viewer/frontend/plotly_protocol.py`
    * Add `PlotlyColorscale` alias; widen `build_plotly_figure`
      `heatmap_colorscale` parameter type.
* `src/nicewidgets/raster_viewer/frontend/plotly_display_options.py`
    * Add `show_hover_info: bool = False`.
* `src/nicewidgets/raster_viewer/frontend/plotly_context_menu.py`
    * Add `Hover Info` toggle item.
* `src/nicewidgets/raster_viewer/backend/image_model.py`
    * Widen `RasterDisplayStyle.colorscale` to `str | list[list[float | str]]`;
      both forms are accepted by `plotly.colors.sample_colorscale` in the PNG
      encoder.
* `src/nicewidgets/contrast_widget/colorscales.py`
    * Add `colorscale_option_value_to_label()`.
* `src/nicewidgets/contrast_widget/contrast_widget.py`
    * `ui.select.options` is now the `{value: label}` dict (shows
      `Inverted Gray`, wire value stays `inverted_grays`).
    * LUT `w-40` → `w-32`; range `flex-1 min-w-32` → `w-56`; min/max labels
      `w-12` → `w-10`.
* `src/nicewidgets/echart_widget/widget.py`
    * Add `on_x_range_changed` constructor hook and `_last_applied_x_range`
      echo-suppressor; `set_x_axis_limits` records the applied pair.
    * `_on_datazoom` forwards normalized `(x_min, x_max)` via
      `_extract_x_datazoom_range` (handles `startValue`/`endValue`,
      `start`/`end` percent against current line data, and the `batch=[{...}]`
      wrapper).
    * `_on_double_click` emits `(None, None)` after resetting limits.
* `src/cloudscope/controllers/home_page_controller.py`
    * Add `HomePageState.primary_x_range: tuple[float | None, float | None]`
      defaulting to `(None, None)`.
* `src/cloudscope/pages/home_page.py`
    * Instantiate and bind `XRangeController`.
* `src/cloudscope/views/primary_image_view.py`
    * Wire `on_x_range_changed=self._on_viewer_x_range_changed` to the viewer;
      subscribe to `PrimaryXRangeChanged` and apply via
      `set_x_axis_range` / `reset_x_axis_range`.
    * Drop the `'Greys'` fallback that previously hid the list-form LUT.
* `src/cloudscope/views/acq_analysis_plot_view.py`
    * Wire `on_x_range_changed=self._on_chart_x_range_changed` to the chart;
      subscribe to `PrimaryXRangeChanged` and apply via
      `set_x_axis_limits` / `reset_x_axis_limits`.

### Tests modified

* `tests/nicewidgets/test_contrast_widget.py` — added
  `test_lut_select_uses_value_to_label_mapping`.
* `tests/nicewidgets/test_plotly_raster_context_menu.py` — extended defaults
  test for `show_hover_info`; added two hover-info toggle tests.
* `tests/cloudscope/test_primary_image_view.py` — added
  `test_apply_contrast_passes_inverted_grays_list_form`; relaxed `_FakeViewer`
  signature to accept any colorscale form.

## Implementation contracts

* **Colorscale union is end-to-end.** `PlotlyColorscale = str | list[list[float
  | str]]` is the surface for `set_heatmap_colorscale`,
  `build_plotly_figure`, and `RasterDisplayStyle.colorscale`. Both heatmap
  traces and `plotly.colors.sample_colorscale` (PNG encoder) accept either
  form, so `inverted_grays` renders identically on initial overview and after
  user interaction.
* **Hover info default is off.** `show_hover_info=False` writes
  `hoverinfo='skip'` on the raster trace at initial figure build (via
  `_apply_display_options_to_plotly_dict`) and via `Plotly.restyle` when
  toggled. `'skip'` (vs `'none'`) also stops Plotly from emitting hover events
  to the browser.
* **X-range producer/consumer are decoupled.** Both widgets emit *intents*; the
  controller dedups by value-equality (with `1e-9` float tolerance) and
  publishes *state*; both widgets consume state and the
  `_last_applied_x_range` echo-suppressor stops the resulting widget event
  from looping back as a new intent.
* **File transitions reset, channel transitions preserve.** `XRangeController`
  subscribes only to `FileSelectionChanged` (and dedups same-id republishes).
  `ChannelSelectionChanged` is intentionally **not** subscribed because
  channels of one `AcqImage` share the same x calibration; preserving the
  range matches the user's expectation when cycling channels to compare.
* **Velocity / diameter analysis views are not consumers.** Only the primary
  raster view and the analysis-plot view participate in x-range sync; the per-
  analysis tabular views are explicitly out of scope.

## Tests added or modified

| Suite | Count |
|-------|------:|
| `tests/cloudscope/test_x_range_controller.py` | 8 |
| `tests/cloudscope/test_x_range_view_wiring.py` | 7 |
| `tests/nicewidgets/test_plotly_viewer_x_range.py` | 5 |
| `tests/nicewidgets/test_echart_x_range.py` | 8 |
| `tests/nicewidgets/test_plotly_raster_context_menu.py` | +3 (defaults extended, two new hover-info tests) |
| `tests/nicewidgets/test_contrast_widget.py` | +1 (`value -> label` mapping) |
| `tests/cloudscope/test_primary_image_view.py` | +1 (`inverted_grays` list form) |

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_contrast_widget.py tests/cloudscope/test_primary_image_view.py -x -q
uv run pytest tests/nicewidgets/test_plotly_raster_context_menu.py -x -q
uv run pytest tests/cloudscope/test_x_range_controller.py -x -q
uv run pytest tests/nicewidgets/test_plotly_viewer_x_range.py -x -q
uv run pytest tests/nicewidgets/test_echart_x_range.py -x -q
uv run pytest tests/cloudscope/test_x_range_view_wiring.py -x -q
uv run pytest -q
```

## Test results

* Targeted suites: all green.
* Full suite: `928 passed, 3 warnings in 2.93s`. The 3 warnings are
  pre-existing (`TestEvent` dataclass collection note in
  `test_base_view.py` and two `RuntimeWarning: All-NaN slice encountered`
  emitted by an existing `test_raster_service.py` case); none originate from
  this ticket.

## Follow-up changes (post-merge polish)

Live testing of the ticket-030 changes surfaced four follow-ups. All four
were implemented in the same ticket scope and verified against the same
test command (full `uv run pytest`).

### F1 — Combined LUT + window viewer API (`set_heatmap_style`)

`PrimaryImageView._apply_contrast` previously issued two browser round
trips back-to-back (`set_heatmap_colorscale` then `set_heatmap_contrast`),
which can race in the JS layer and leave the heatmap repainted with one
trait updated but not the other.

Added `PlotlyRasterViewer.set_heatmap_style(*, colorscale, zmin, zmax)`
that updates all three keys with a single `Plotly.restyle` (heatmap path)
or a single `_refresh_full_png` (image-overview path). The individual
`set_heatmap_colorscale` / `set_heatmap_contrast` methods stay as-is for
back-compat (atomic, independent). `_apply_contrast` now calls the
combined method.

### F2 — Suppress relayout echo on `set_data` and double-click reset

When Plotly's `_uirevision` rotates (`set_data` for file/channel/analysis
load, or `_on_plotly_doubleclick` reset), Plotly fires a fresh
`plotly_relayout` carrying the new data-extent x-range. Previously that
relayout leaked through `_emit_x_range_from_relayout` and overwrote
`HomePageState.primary_x_range` with the data extent, defeating both the
double-click "auto" reset and any preserved user range across analysis
clicks.

Added a one-shot guard `PlotlyRasterViewer._suppress_next_relayout_x_emit`
(KISS: a single named boolean, not a generalized suppressor set — see
YAGNI). It is set:

* in `set_data` after the `_uirevision` rotation, and
* in `_on_plotly_doubleclick` before `apply_response`.

`_emit_x_range_from_relayout` consumes and clears the flag on its next
invocation, regardless of payload shape, so it cannot leak into later
user gestures.

### F3 — ECharts auto-padding on the x-axis

ECharts' default `type='value'` axis applies a "nice ticks" outward
rounding (e.g. `[0, 9.4]` → `[0, 10]`, `[0, 16]` → `[0, 18]`). In
`build_line_options`, the x-axis bounds now substitute the ECharts
sentinels `'dataMin'` / `'dataMax'` when the explicit range is `None`,
disabling the rounding without disabling tick generation. The y-axis is
unchanged.

### F4 — Re-apply `primary_x_range` after refresh (analysis-row click survival)

`HomePageState.primary_x_range` is preserved across `ChannelSelectionChanged`
and same-file `FileSelectionChanged` (analysis-row clicks). However the
two views previously consumed `PrimaryXRangeChanged` and forgot the value
after pushing it to the widget once. When the widget repainted (chart
`set_line_data`, viewer `set_data`), the previous user range was lost.

Both views now cache the latest payload locally and provide a
`_apply_primary_x_range_to_*` helper that is called from the refresh
paths (`AcqAnalysisPlotView._refresh_plot`,
`PrimaryImageView._refresh_raster_async`). The pattern keeps `nicewidgets`
CloudScope-agnostic — views consume state events, never read controllers
directly.

`PrimaryImageView` follows an additional contract: `(None, None)` is a
no-op for the viewer (Plotly already auto-ranged on the new `uirevision`);
only finite `(x_min, x_max)` is pushed. `AcqAnalysisPlotView` always calls
`reset_x_axis_limits` or `set_x_axis_limits` to match the cache.

### Files changed (follow-up)

* `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
    * Added `set_heatmap_style`.
    * Added `_suppress_next_relayout_x_emit` flag and consumption in
      `_emit_x_range_from_relayout`; armed in `set_data` and
      `_on_plotly_doubleclick`.
* `src/nicewidgets/echart_widget/widget.py`
    * `build_line_options` substitutes `'dataMin'`/`'dataMax'` for `None`
      x-axis bounds.
* `src/cloudscope/views/primary_image_view.py`
    * `_apply_contrast` switched to the combined `set_heatmap_style`.
    * Added `_primary_x_range` cache and `_apply_primary_x_range_to_viewer`
      helper; called at the end of `_refresh_raster_async`.
    * `_on_primary_x_range_changed` now updates the cache instead of
      directly pushing/resetting the viewer.
* `src/cloudscope/views/acq_analysis_plot_view.py`
    * Added `_primary_x_range` cache and
      `_apply_primary_x_range_to_chart` helper; called at the end of
      `_refresh_plot`.

### Tests (follow-up)

* `tests/nicewidgets/test_plotly_viewer_heatmap_style.py` — new
    * 4 tests covering combined restyle, inverted zmin/zmax swap,
      list-form colorscale, and idempotent no-op repeat.
* `tests/nicewidgets/test_plotly_viewer_x_range.py`
    * Helper now clears the one-shot guard after `set_data` so existing
      relayout-payload tests run as designed.
    * Added 3 tests for: `set_data` arming the guard, single-shot
      consumption + resume, and the guard being consumed by any next
      relayout payload (even without x-range keys).
* `tests/nicewidgets/test_echart_widget.py`
    * Renamed/extended the auto-axis test to expect `'dataMin'` /
      `'dataMax'`; added a symmetry test that an explicit
      `EChartAxisRange` still overrides the sentinels.
* `tests/cloudscope/test_primary_image_view.py`
    * `_FakeViewer` now models `set_heatmap_style`; added
      `test_apply_contrast_uses_single_combined_style_call`.
    * Inline viewer fakes in plane-load tests gained `has_data = True`
      and migrated to `set_heatmap_style`.
* `tests/cloudscope/test_x_range_view_wiring.py`
    * Updated `PrimaryImageView` consumer test for the new "auto = no-op"
      contract.
    * Added cache-from-state-event tests for both views and apply-helper
      tests for both finite and `(None, None)` cache values.

### Test command and result

```bash
uv run pytest -q
```

`942 passed, 3 warnings in 2.80s` (the same 3 pre-existing warnings).

## Concerns and follow-ups

* The `PlotlyColorscale` widening keeps the union narrow (a list of
  `[stop, color]` pairs). If callers later need named tuples or RGBA tuples,
  the alias and `RasterDisplayStyle.colorscale` field type should be widened
  together to keep the heatmap and PNG paths in sync.
* `_extract_x_datazoom_range` resolves percent-form `start` / `end` against
  the current `EChartLineData.x[0]` / `x[-1]`. If the analysis ever publishes
  non-monotonic x data, this conversion would need an explicit min/max scan;
  for now the existing analysis plot data is monotonic by construction.
* The `XRangeController` does not subscribe to `ChannelSelectionChanged`,
  which is the intended behavior per the plan. If a future analysis view
  requires its own x sync semantics, that view should publish its own intent
  rather than expanding this controller's scope.
* Pre-existing Ruff `E402` (late import) in `image_toolbar_view.py` line 40 is
  unrelated to this ticket and was deliberately left untouched.
