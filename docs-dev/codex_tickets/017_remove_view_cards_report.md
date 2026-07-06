# Ticket 017 — Remove redundant `ui.card` wrappers from three views

## Summary

`PrimaryImageView`, `AcqAnalysisPlotView`, and `ReferenceImageView` each
wrapped their content in a `ui.card`. In `home_page.py` all three are already
nested inside a parent `ui.column().classes(_fill_column_classes())`, where
`_fill_column_classes()` returns
``w-full h-full min-h-0 gap-3 p-3 overflow-hidden flex flex-col``. The inner
card was therefore redundant chrome: the parent already provides sizing,
padding, and flex layout.

This ticket swaps each `ui.card()` for `ui.column()` while preserving the
exact Tailwind class string. No content reordering, no children touched, no
controller/event/lifecycle logic touched.

User-confirmed scope:

- Card chrome (background, shadow, border-radius) is intentionally removed.
- `ReferenceImageView` is treated identically to the other two — no special
  padding, no gap fallback. The replacement is `ui.column().classes('w-full')`
  matching the prior card's class string 1:1.
- Element replacement is `ui.column()` (matches the parent container idiom
  already used in `home_page.py`).

## Files changed

- `src/cloudscope/views/primary_image_view.py`
  - Line that opened `ui.card().classes("w-full h-full min-h-0 flex flex-col
    overflow-hidden flex-1") as self.root` now uses `ui.column()` with the
    identical class string.
- `src/cloudscope/views/acq_analysis_plot_view.py`
  - Both `build` branches (parent provided and parent not provided) swapped
    `ui.card()` to `ui.column()` keeping the same class string.
- `src/cloudscope/views/reference_image_view.py`
  - `ui.card().classes('w-full') as self.root` → `ui.column().classes('w-full')
    as self.root`. No spacing/padding mitigation; renders flush.
- `docs/codex_tickets/017_remove_view_cards_report.md` (this report).

## Implementation notes

- `BaseView` lifecycle uses only generic element APIs on `self.root`
  (`visible`, `enabled`, `classes(add/remove=…)`, `update()`). Both `ui.card`
  and `ui.column` are NiceGUI elements, so `after_build`, `_apply_visible`,
  `set_enabled`, and `handle_app_busy_changed` are unaffected.
- The view-body `with` block remains unchanged. All child widgets
  (`PlotlyRasterViewer`, `EChartWidget`, labels) are still created inside the
  replacement context manager.
- No test asserts `isinstance(root, ui.card)` or any card-specific attribute,
  so headless tests carry over directly. `test_base_view.py` only reads
  `view.root.visible`, which is satisfied by `ui.column`.
- The pre-existing Ruff warning at `acq_analysis_plot_view.py:356` (line
  length on the `_empty_message` string) is unrelated to this ticket and is
  not addressed here.

## Tests added or modified

None. Behavior, public APIs, signal flow, and event subscriptions are
unchanged. Existing tests provide coverage for the view lifecycle and
selection-driven refresh paths.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_primary_image_view.py \
              tests/cloudscope/test_primary_image_view_handlers.py \
              tests/cloudscope/test_primary_image_diameter_overlay.py \
              tests/cloudscope/test_primary_image_view_roi_overlay.py \
              tests/cloudscope/test_reference_image_view.py \
              tests/cloudscope/test_acq_analysis_plot_view.py -q
uv run pytest -q
```

## Test results

Targeted run (the six test files that exercise the three views):

```
55 passed in 0.67s
```

Full suite:

```
739 passed, 3 warnings in 2.69s
```

The three warnings (`PytestCollectionWarning` for `TestEvent` and two
`RuntimeWarning: All-NaN slice` from `raster_service.py`) are pre-existing
and unrelated to this ticket.

## Concerns or follow-ups

- Visual chrome change is intentional but visible: the three views no longer
  render Quasar card backgrounds, shadows, or border-radius. If any specific
  panel later wants a flat-card look, that can be reintroduced with explicit
  Tailwind utilities (e.g. `rounded-md bg-white shadow-sm`) on the same
  `ui.column` without re-introducing `ui.card`.
- The pre-existing line-length warning in `acq_analysis_plot_view.py:356`
  remains. Worth a small follow-up ticket if line-length conformance is a
  goal.
