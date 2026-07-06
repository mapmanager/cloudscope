# 044 — ECharts axis/grid context-menu toggles + click+drag zoom fix

## Summary

Three additions to the reusable `nicewidgets` ECharts widget:

1. **Three new right-click context-menu toggles**, each a pure ECharts option
   flip applied through the existing `_apply_display_options_to_options`
   pipeline:
   * **Axis Labels** (default `True`) — single toggle for both axes that
     shows/hides the axis name, tick labels, tick marks, and axis line.
   * **Horizontal Lines** (default `False`) — `yAxis.splitLine.show`.
   * **Vertical Lines** (default `False`) — `xAxis.splitLine.show`.
2. **Fix: default click+drag x-axis zoom now actually works.** The
   `dataZoomSelect` cursor was armed once in `__init__` (before the chart was
   mounted) and then wiped by every `apply()` (a full `setOption` resets the
   global cursor). It is now re-armed at the end of every `apply()` (skipped
   while a one-shot brush selection is active), so it stays live once data is
   drawn.
3. **Shift+drag → y-axis zoom.** A page-level `ui.keyboard` listener flips the
   toolbox `dataZoom` feature between x-only and y-only on Shift press/release
   and re-arms the cursor. (Shift, not Ctrl, because on macOS Ctrl+click is the
   system secondary-click and would open the context menu.)

No changes outside `nicewidgets`; no GUI-view or backend edits.

## Files changed

* `src/nicewidgets/echart_widget/display_options.py`
  * Added `show_axis_labels: bool = True`, `show_horizontal_lines: bool = False`,
    `show_vertical_lines: bool = False` (with docstrings).
* `src/nicewidgets/echart_widget/widget.py`
  * `apply()` re-arms the x-zoom cursor after the redraw when not selecting
    (the runtime fix), with an explanatory docstring.
  * `_apply_display_options_to_options()` now stamps axis-label visibility on
    both axes (`axisLabel`/`axisTick`/`axisLine` `show`, blanks `name` when off,
    preserving the `:formatter`) and split-line visibility
    (`xAxis.splitLine` = vertical, `yAxis.splitLine` = horizontal).
  * New setters: `set_axis_labels_visible`, `set_horizontal_lines_visible`,
    `set_vertical_lines_visible` (flip flag → `apply()`).
  * New `_set_zoom_axis(y_axis=...)` (merges the toolbox `dataZoom` feature with
    both axis indices set explicitly, then re-arms) and `_on_zoom_modifier_key`
    (Shift down → y, Shift up → x).
  * `__init__` registers `ui.keyboard(on_key=self._on_zoom_modifier_key)`.
* `src/nicewidgets/echart_widget/context_menu.py`
  * Added the three toggle `menu_item`s after "Hover Info", before the
    separator.
* `tests/nicewidgets/test_echart_context_menu.py`
  * Updated `test_context_menu_builds_toggles_separator_and_clipboard_entries`
    for the new 7-item layout/order.
  * Added tests: new defaults; axis-label + split-line propagation (on/off);
    `apply()` re-arm and its brush-selection skip; `_set_zoom_axis` x/y feature
    + re-arm; Shift keydown/keyup axis switching; non-Shift no-op; new menu-item
    setter wiring.

## Implementation notes

* Axis sub-options use `setdefault` so the stamping works on both the
  `build_line_options` and `_empty_options` dicts and preserves the existing
  x-axis tick `:formatter`.
* `_set_zoom_axis` sets **both** `xAxisIndex` and `yAxisIndex` explicitly so a
  merged `setOption` never leaves both as `'none'` (which would zoom nothing).
* Multiple charts on one page would all react to Shift; this is harmless since
  only the chart being dragged produces a rubber band. Kept simple per KISS.

## Tests run

```bash
uv run pytest tests/nicewidgets/test_echart_context_menu.py tests/nicewidgets/test_echart_widget.py -q
uv run pytest tests/nicewidgets/ -q
```

## Test results

* Targeted echart suites: `37 passed`.
* Full nicewidgets suite: `302 passed, 2 warnings` (the 2 warnings are the
  pre-existing All-NaN slice warnings in `test_raster_service.py`).

## Addendum — Shift y-zoom parked, toolbar default flipped on

Live testing showed the Shift+drag y-zoom corrupted the chart (a confusing
second axis appeared on shift+drag), so that feature was reverted:

* `src/nicewidgets/echart_widget/widget.py`
  * The `ui.keyboard(on_key=self._on_zoom_modifier_key)` install line in
    `__init__` is now **commented out** with a note explaining why. The
    `_on_zoom_modifier_key` and `_set_zoom_axis` helpers (and their tests) are
    intentionally kept so the feature can be revisited later.
* `src/nicewidgets/echart_widget/display_options.py`
  * `EChartDisplayOptions.show_toolbar` default flipped `False` → `True` so the
    ECharts toolbox (zoom/restore/brush icons) is visible by default. Docstring
    updated.
* `tests/nicewidgets/test_echart_context_menu.py`
  * `test_display_options_default_hides_toolbar` renamed to
    `test_display_options_default_shows_toolbar` and now asserts `True`.

Kept unchanged: the `apply()`-time x-zoom re-arm fix and the Axis Labels /
Horizontal Lines / Vertical Lines toggles.

Re-ran `uv run pytest tests/nicewidgets/ -q` → `302 passed, 2 warnings`.

## Concerns / follow-ups

* The Shift y-zoom relies on a page-level `ui.keyboard`; in a hypothetical
  multi-chart page every chart switches axis on Shift. Acceptable for the
  current single-analysis-chart usage.
* If an `apply()` happens to fire while Shift is held mid-session, the redraw
  resets the feature to x-only until Shift is released/re-pressed. This is an
  unlikely edge case and was left as-is for simplicity.
