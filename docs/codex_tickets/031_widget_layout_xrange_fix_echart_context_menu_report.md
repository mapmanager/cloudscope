# 031 — Widget layout, x-range first-gesture fix, ECharts context menu

## Summary

This ticket combines three independent code changes that came out of the
review of ticket 030's follow-ups. The fourth item from the original request
(plot border / margin source-of-truth) is documentation only and called out
inline below — no code change is bundled here.

* **Part A — Widget layout (composition over inheritance).** Drop
  `class ContrastWidget(ui.row)` and `class ImageToolbarWidget(ui.row)`. Both
  widgets now create their child controls directly in the caller's active
  NiceGUI slot. `ImageToolbarView` wraps both widgets in a single shared
  `ui.row` so the contrast controls sit on the same horizontal line as the
  channel/ROI selects. The `w-56` fixed width on the contrast range slider is
  removed so the slider grows to fill the row.
* **Part B — Plotly x-range first-gesture fix.** Remove the
  `_suppress_next_relayout_x_emit` one-shot guard introduced in ticket 030
  follow-up F2. It could swallow the user's first pan/zoom gesture after
  `set_data` whenever the post-`uirevision` relayout Plotly fired carried no
  `xaxis.range` keys (the early-return in `_on_plotly_relayout` skipped the
  guard-consumption call site). Replaced with value-based dedup: both
  `set_data` and `_on_plotly_doubleclick` now pre-populate
  `_last_applied_x_range` with the freshly auto-ranged data extent, so the
  follow-up echo relayout is suppressed by value while genuine user gestures
  always reach `on_x_range_changed`.
* **Part C — EChart right-click context menu + default click+drag x-zoom.**
  Mirror the Plotly raster viewer pattern: add
  `EChartDisplayOptions` (toggle dataclass), `EChartWidgetContextMenu`
  (menu builder), and ECharts clipboard helpers. The menu currently exposes
  "Show Toolbar" and "Copy To Clipboard"; `✓` prefix denotes enabled.
  Move `copy_png_bytes_to_native_clipboard` from `plotly_clipboard.py` to
  `nicewidgets/utils/clipboard.py` so both Plotly and ECharts share one
  implementation. The widget now activates the ECharts `dataZoomSelect`
  cursor at construction time so click+drag inside the plot area zooms the
  x-axis by default. `cancel_select_x_range` restores the zoom cursor so the
  default mode resumes after one-shot brush selection.

## Files changed

### New

* `src/nicewidgets/echart_widget/display_options.py` — `EChartDisplayOptions`.
* `src/nicewidgets/echart_widget/clipboard.py` —
  `get_echart_png_bytes(echart_element)`,
  `copy_echart_png_to_browser_clipboard(echart_element)`.
* `src/nicewidgets/echart_widget/context_menu.py` —
  `EChartWidgetContextMenu` (build, `_toggle_label`).
* `tests/nicewidgets/test_echart_context_menu.py` — 9 cases covering
  display-option defaults, toolbox feature shape, `_apply_display_options_to_options`
  propagation, menu label `✓` prefix, full menu build order, toolbar toggle
  invocation, x-zoom cursor payload, and cancel-restore behavior.
* `docs/codex_tickets/031_widget_layout_xrange_fix_echart_context_menu_report.md`
  (this file).

### Modified — Part A (widget layout)

* `src/nicewidgets/contrast_widget/contrast_widget.py`
    * `class ContrastWidget(ui.row)` → `class ContrastWidget`.
    * Drop `super().__init__()`, `self.classes(...)`, and the `with self:`
      block. Controls are created in the caller's active slot.
    * Drop `.classes('w-56')` from `_range`; keep `.props('debounce=200')`,
      `w-32` on the LUT select, and `w-10` on the min/max labels.
    * Updated module docstring to reflect the composition pattern.
* `src/nicewidgets/image_toolbar_widget/image_toolbar_widget.py`
    * `class ImageToolbarWidget(ui.row)` → `class ImageToolbarWidget`.
    * Drop `super().__init__()`, `self.classes(...)`, and the inner
      `with ui.row().classes('gap-1 items-center'):` wrapper. The widget no
      longer owns any layout container.
* `src/cloudscope/views/image_toolbar_view.py`
    * Outer `ui.row` classes updated to
      `'w-full items-center flex-wrap gap-2 p-1'` so the merged child
      controls flow on one line and wrap together when narrow.

### Modified — Part B (Plotly x-range)

* `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py`
    * Remove `self._suppress_next_relayout_x_emit` attribute (constructor and
      both call sites in `set_data` / `_on_plotly_doubleclick`).
    * In `set_data`, after the `uirevision` rotation and bounds recompute,
      pre-populate `self._last_applied_x_range` with the new auto-ranged data
      extent via `PlotlyCoordTransform.row_col_to_plot_x_range`. This causes
      the follow-up echo relayout (carrying that extent) to dedup by value.
    * In `_on_plotly_doubleclick`, after `apply_response`, perform the same
      pre-population. The explicit `on_x_range_changed(None, None)` emission
      to the controller is unchanged.
    * `_emit_x_range_from_relayout` now relies exclusively on the existing
      `_is_x_range_echo` float-tolerance dedup; the boolean short-circuit was
      removed.
* `tests/nicewidgets/test_plotly_viewer_x_range.py`
    * Helper `_viewer_with_data` no longer toggles a guard attribute (the
      attribute is gone).
    * Removed: `test_set_data_arms_one_shot_suppressor`,
      `test_suppressor_swallows_exactly_one_relayout_then_resumes`,
      `test_suppressor_consumes_one_shot_even_without_xrange_payload`.
    * Added: `test_set_data_pins_last_applied_to_data_extent`,
      `test_post_set_data_data_extent_relayout_is_suppressed_by_value`,
      `test_first_user_relayout_after_set_data_fires` (the regression test
      for the original bug), and
      `test_non_xrange_relayout_does_not_affect_dedup_baseline`.

### Modified — Part C (ECharts context menu + zoom)

* `src/nicewidgets/echart_widget/widget.py`
    * Import `EChartDisplayOptions`, `EChartWidgetContextMenu`,
      `get_echart_png_bytes`, `copy_echart_png_to_browser_clipboard`, and
      `copy_png_bytes_to_native_clipboard`.
    * Constructor: new `display_options` kwarg; stores
      `self._display_options`. Initial `_empty_options()` dict is passed
      through `_apply_display_options_to_options` so the initial toolbox
      visibility matches the requested state.
    * Constructor wires `ui.context_menu()`, `EChartWidgetContextMenu`, and a
      `contextmenu` event handler on `self.container`, then calls
      `_activate_x_zoom_cursor()` to arm `takeGlobalCursor`/`dataZoomSelect`.
    * Public API: `display_options` (read-only property),
      `set_toolbar_visible(visible)`, `async copy_plot_to_clipboard()`.
    * Private helpers: `_on_context_menu_event`,
      `_activate_x_zoom_cursor`, `_apply_display_options_to_options`.
    * `cancel_select_x_range` now calls `_activate_x_zoom_cursor` so the
      default click+drag zoom resumes after brush mode ends.
    * `_empty_options` now includes a `toolbox` block with `"show": False`
      and the `dataZoom` / `restore` / `brush` features so the
      `dataZoomSelect` action can attach before line data is loaded.
* `src/nicewidgets/utils/clipboard.py`
    * Added `copy_png_bytes_to_native_clipboard(png_bytes)`.
* `src/nicewidgets/raster_viewer/frontend/plotly_clipboard.py`
    * Removed the local `copy_png_bytes_to_native_clipboard` body and
      re-exports the helper from `nicewidgets.utils.clipboard`. Trimmed
      unused `logging` / `BytesIO` imports.

## Implementation contracts

* **Layout ownership.** ContrastWidget and ImageToolbarWidget no longer own
  any layout container. Callers compose them inside their own `ui.row` /
  `ui.column` and pick the wrapping classes. `ImageToolbarView` provides the
  single shared row for both widgets in CloudScope.
* **X-range echo dedup by value.** Plotly fires a relayout whenever the
  axis range changes, including programmatic changes via `Plotly.relayout`
  and the implicit auto-range that occurs when `uirevision` rotates.
  `_last_applied_x_range` is the single dedup baseline; both `set_data` and
  `_on_plotly_doubleclick` set it to the freshly auto-ranged data extent
  before any browser-side relayout can race the Python-side emit. The
  existing `set_x_axis_range` already pinned this field.
* **EChart default cursor.** The widget activates ECharts'
  `dataZoomSelect` cursor in `__init__`. Click+drag inside the chart area
  zooms the x-axis (`dataZoom.yAxisIndex='none'` in `build_line_options`
  / `_empty_options`). Brush-based one-shot x-range selection still works:
  `begin_select_x_range` switches the cursor to `brush`; `cancel_select_x_range`
  restores `dataZoomSelect`.
* **EChart toolbox visibility.** `display_options.show_toolbar` controls
  only the visible icon row. The `toolbox.feature.dataZoom` entry is always
  present (because the `dataZoomSelect` cursor needs it) but icons stay
  hidden by default.
* **Clipboard surface.** Native window mode writes PNG bytes via the shared
  `copy_png_bytes_to_native_clipboard` (requires `pyperclipimg` + `pillow`).
  Browser mode writes a `Blob` through `navigator.clipboard.write` with a
  per-widget JS helper (`copy_plotly_png_to_browser_clipboard` /
  `copy_echart_png_to_browser_clipboard`).

## Plot border / margin source-of-truth (no code change in this ticket)

For future reference, the margin/grid values that produce the visible
border around the plots live here:

* Plotly raster (data path):
  `src/nicewidgets/raster_viewer/frontend/plotly_protocol.py` line 78 —
  `'margin': {'l': 40, 'r': 20, 't': 20, 'b': 40}`.
* Plotly raster (empty/initial path):
  `src/nicewidgets/raster_viewer/frontend/plotly_viewer.py` line 1222 —
  same dict (must be kept in sync with the data path).
* ECharts (line plot path):
  `src/nicewidgets/echart_widget/widget.py` `build_line_options` —
  `'grid': {'left': 55, 'right': 20, 'top': 24, 'bottom': 45}`.
* ECharts (empty path):
  same file `_empty_options` — same dict (kept in sync).

Reducing these values shrinks the gutter between the plot frame and the
host element. Setting them to `0` removes the gutter entirely; combine with
`show_axis_labels=False` (Plotly) or hidden axis names (ECharts) to avoid
clipped labels.

## Tests added or modified

| Suite | Change |
|-------|-------:|
| `tests/nicewidgets/test_plotly_viewer_x_range.py` | -3 suppressor tests, +4 value-dedup tests |
| `tests/nicewidgets/test_echart_context_menu.py` | new, 9 tests |
| existing contrast/image-toolbar/echart-x-range tests | unchanged; all still pass |

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plotly_viewer_x_range.py -x -q
uv run pytest tests/cloudscope/test_x_range_view_wiring.py tests/cloudscope/test_x_range_controller.py tests/cloudscope/test_primary_image_view.py -x -q
uv run pytest tests/nicewidgets/test_contrast_widget.py tests/nicewidgets/test_image_toolbar_widget.py tests/nicewidgets/test_image_toolbar_widget_handlers.py tests/nicewidgets/test_image_toolbar_validation.py tests/cloudscope/test_image_toolbar_view.py -x -q
uv run pytest tests/nicewidgets/test_echart_widget.py tests/nicewidgets/test_echart_x_range.py tests/nicewidgets/test_echart_context_menu.py -x -q
uv run pytest -q
```

## Test results

* Targeted suites: all green.
* Full suite: `952 passed, 3 warnings in 2.83s`. The 3 warnings are
  pre-existing (`TestEvent` dataclass collection note in
  `test_base_view.py` and two `RuntimeWarning: All-NaN slice encountered`
  emitted by `test_raster_service.py`); none originate from this ticket.

## Follow-up changes (post-merge polish)

Live testing surfaced two issues. Both were fixed in the same ticket scope
and verified against the same `uv run pytest` command.

### FU1 — ECharts clipboard ``chart_not_ready`` regression

The initial ECharts clipboard helpers reached into the DOM with
`window.echarts.getInstanceByDom(host.$el)`. NiceGUI's `$el` is the Vue root
element, not the chart-mount div, so the lookup returned `null` and the
helpers raised `RuntimeError: ECharts export failed: {'stage': 'chart_not_ready'}`.

Source of truth: `ui.echart.run_chart_method(name, *args)` is the NiceGUI-
documented bridge to the underlying ECharts instance — the same mechanism
the widget already uses for `dispatchAction`. ECharts exposes
`getDataURL({type, pixelRatio, backgroundColor})` as the canonical PNG
export entry point. Reference: https://echarts.apache.org/en/api.html#echartsInstance.getDataURL.

Rewrite of `src/nicewidgets/echart_widget/clipboard.py`:

* `_get_data_url(echart_element)` awaits
  `run_chart_method('getDataURL', _GET_DATA_URL_OPTIONS, timeout=10.0)`.
* `get_echart_png_bytes` consumes the data URL and returns decoded bytes.
* `copy_echart_png_to_browser_clipboard` consumes the data URL in Python,
  then runs one JS snippet that does `navigator.clipboard.write` against
  the inlined data URL. No JS-side chart instance lookup is required.

New regression-guard tests in `tests/nicewidgets/test_echart_clipboard.py`
(8 cases) verify the call surface, the documented option shape, base64
decoding, browser-side JS contract, timeout wrapping, and that
`getInstanceByDom` / `window.echarts` no longer appear inside any helper
body.

### FU2 — Hover Info toggle in the ECharts context menu

Mirrors the Plotly `Hover Info` toggle introduced in ticket 030.

Source of truth: ECharts' `tooltip.show` option
(https://echarts.apache.org/en/option.html#tooltip.show) controls the
tooltip floating layer. The `trigger='axis'` axis-pointer configuration is
preserved across toggles.

Changes:

* `EChartDisplayOptions` gains `show_hover_info: bool` (default flipped to
  `False` in FU4 below — see updated docstring in
  `src/nicewidgets/echart_widget/display_options.py`).
* `EChartWidget.set_hover_info_visible(visible)` updates the display
  option and calls `apply()`.
* `_apply_display_options_to_options` propagates `tooltip.show` from the
  display option (and creates the dict if missing, so the legacy
  `_empty_options` shape continues to work).
* `EChartWidgetContextMenu.build` inserts a `Hover Info` toggle item right
  after `Show Toolbar` (and before the separator before `Copy To
  Clipboard`).

New / updated tests in `tests/nicewidgets/test_echart_context_menu.py`:

* `test_display_options_default_hides_hover_info` (renamed from
  `..._shows_hover_info` in FU4) — default is `False`.
* `test_apply_display_options_show_hover_info_propagates` — option flip
  maps to `tooltip.show` while preserving `trigger='axis'`.
* `test_apply_display_options_creates_missing_toolbox_and_tooltip` —
  defensive creation of both blocks.
* Menu build test renamed to
  `test_context_menu_builds_toggles_separator_and_clipboard_entries` —
  now expects 4 items (toolbar, hover, separator, copy).
* `test_context_menu_hover_item_flips_show_hover_info` — clicking the
  hover item calls `set_hover_info_visible` with the inverse.

### FU3 — `nicewidgets` → `cloudscope` import boundary

Switched `src/nicewidgets/echart_widget/widget.py` from
`from cloudscope.utils.logging import get_logger` to
`from nicewidgets.utils.logging import get_logger`. Same `get_logger(name)`
API. `rg "from cloudscope" src/nicewidgets/` now returns no matches.

### FU4 — Hover info default flipped to off

Per the latest follow-up request, the default value of
`EChartDisplayOptions.show_hover_info` is now `False` so charts ship with
the floating tooltip hidden. The setter / context-menu toggle / apply
pipeline introduced in FU2 is unchanged — only the default is flipped.

* `src/nicewidgets/echart_widget/display_options.py` — default is `False`;
  docstring updated to match the (existing) `show_toolbar=False` phrasing.
* `tests/nicewidgets/test_echart_context_menu.py` — the
  `test_display_options_default_shows_hover_info` test from FU2 is
  renamed to `test_display_options_default_hides_hover_info` and asserts
  `False`. The other FU2 tests (which explicitly pass
  `show_hover_info=True`/`False`) are unaffected.

### FU5 — Round x-axis tick labels to trim explicit-bound float precision

Source of the problem: ECharts' default value-axis tick formatter prints
the raw value. ECharts picks "nice" interior tick stops, but when `xAxis.min`
/ `xAxis.max` are set to explicit floats (which happens any time the
controller broadcasts a zoom range and `EChartWidget.set_x_range` consumes
it), the first and last labels render at full float precision
(`7.08379656153604`, `8.181001796798633`). Interior ticks stay clean
because they are derived from ECharts' own rounding.

Documented fix (ECharts API): set
[`xAxis.axisLabel.formatter`](https://echarts.apache.org/en/option.html#xAxis.axisLabel.formatter)
to a JavaScript function that rounds the numeric value. There is no
"precision" option on value axes, so a function formatter is the
ECharts-idiomatic solution.

How JS callbacks reach ECharts via NiceGUI: `convertDynamicProperties` in
`nicegui/static/utils/dynamic_properties.js` walks the option tree and, for
any key starting with `":"`, evaluates the string value as a JS expression
and rewrites the entry under the un-prefixed key. So shipping the option
key as `":formatter"` with the value `"(value) => +value.toFixed(3)"` is
how we hand ECharts a real function from a JSON-only Python options dict.

Choice of rounding: `+value.toFixed(3)` rounds to three decimals and then
re-numerifies, which drops trailing zeros (`+"7.400" === 7.4`). The
displayed strings are produced by ECharts' default number-to-string path,
so interior ticks (`7.2`, `7.4`, `8`) remain unchanged while edge labels
collapse (`7.08379656153604` → `7.084`, `8.181001796798633` → `8.181`).
Three decimals is a safe default for the typical time/velocity x-axes
this widget renders; if a future caller needs different precision it can
become a constructor / display-option parameter (out of scope here).

Changes:

* `src/nicewidgets/echart_widget/widget.py`
    * New module-level constant `_X_AXIS_LABEL_FORMATTER_JS =
      "(value) => +value.toFixed(3)"`, with a comment explaining why it
      lives at module scope and why the `:` key prefix matters.
    * `build_line_options` adds
      `"axisLabel": {":formatter": _X_AXIS_LABEL_FORMATTER_JS}` to the
      `xAxis` block.
    * `_empty_options` adds the same `axisLabel` block to the `xAxis` so
      the formatter is in place from construction time (before
      `set_line_data` is ever called).
* `tests/nicewidgets/test_echart_widget.py`
    * `test_build_line_options_includes_xaxis_label_formatter` — asserts
      the `":formatter"` key (and not a literal `formatter` key) carries
      the JS string.
    * `test_empty_options_includes_xaxis_label_formatter` — same check
      against `_empty_options`.
    * `test_xaxis_label_formatter_rounds_long_floats_to_three_decimals` —
      verifies the JS semantics with Python-equivalent rounding for the
      exact float values from the bug report (8.181001796798633 → 8.181,
      7.08379656153604 → 7.084) and that clean values are unchanged.

### Test command (final) and result

```bash
uv run pytest -q
```

`966 passed, 3 warnings in 2.77s` (the same 3 pre-existing warnings).

## Concerns and follow-ups

* The widget composition change means tests that previously relied on
  `isinstance(widget, ui.row)` would break. The current test suite has no
  such assertion, but downstream callers (if any) that introspected the
  widget type will need to update. Visible behavior is otherwise unchanged.
* The Plotly fix overturns ticket 030 follow-up F2. The new value-based
  dedup path is simpler (one source of truth: `_last_applied_x_range`) and
  closes a regression that F2 introduced — but if a future change rotates
  `_uirevision` without updating `_last_applied_x_range`, the follow-up
  relayout would leak through as a real user gesture. New rotations must
  pre-populate the dedup baseline; this is documented in the constructor
  comment.
* `nicewidgets/echart_widget/widget.py` previously imported
  `cloudscope.utils.logging.get_logger` — see follow-up FU3 above for the
  resolution.
* The ECharts clipboard browser flow now consumes the data URL in Python
  via `run_chart_method('getDataURL', ...)` and only uses raw JS to write
  to `navigator.clipboard`. The DOM-instance lookup that previously caused
  `chart_not_ready` is gone (regression-guarded by
  `tests/nicewidgets/test_echart_clipboard.py`).
