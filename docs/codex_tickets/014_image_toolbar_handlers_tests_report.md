# Ticket 014 — ImageToolbarWidget handler and setter tests

## Files changed

- `tests/nicewidgets/test_image_toolbar_widget_handlers.py` — new file with
  33 tests
- `docs/codex_tickets/014_image_toolbar_handlers_tests_report.md`
  (this report)

## Summary of implementation

`ImageToolbarWidget` previously had 5 smoke tests covering only the
`set_file_ext` / `set_roi_options_and_selection_ext` / `_on_roi_change`
paths. This ticket adds headless tests for the remaining setter helpers,
value parsers, and per-button click handlers.

Behaviors covered:

- `_format_file_label` (value vs. dash) and `_channel_as_str` (None vs. int).
- `_parse_channel_str`: None pass-through, decimal parse, and ValueError on
  garbage.
- `_parse_roi_select_value`: None, int, decimal str, whole-number float;
  ValueErrors for bool, fractional float, and unsupported types.
- `set_enabled_ext` toggles `_enabled`.
- `set_channel_options_ext` / `set_roi_options_ext`: happy path preserves
  selection; raises when the new options no longer contain the current
  selection.
- `_on_channel_change` emits `ImageToolbarSelectChannelIntent` and respects
  the disabled state.
- ROI-action click handlers (`_on_add_click`, `_on_delete_click`,
  `_on_edit_click`, `_on_full_width_click`, `_on_full_height_click`,
  `_on_ok_click`, `_on_cancel_click`) emit the correct intent types, no-op
  when disabled, no-op when no ROI is selected, and `_on_ok_click` /
  `_on_cancel_click` return mode to IDLE.
- `_emit` is silent when `on_intent is None`.

## Tests added or modified

33 new tests in `tests/nicewidgets/test_image_toolbar_widget_handlers.py`.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_image_toolbar_widget_handlers.py -q
uv run pytest tests/nicewidgets/test_image_toolbar_widget.py \
    tests/nicewidgets/test_image_toolbar_widget_handlers.py \
    tests/nicewidgets/test_image_toolbar_validation.py \
    --cov=nicewidgets.image_toolbar_widget --cov-report=term-missing -q
```

## Test results

- 33 / 33 new tests passing
- 59 / 59 tests passing across the toolbar module
- Coverage:
  - `image_toolbar_widget.py`: 64% → **100%**
  - `image_toolbar_widget` package: 75% → **99%** (only one line in
    `validation.py`, line 77, remains uncovered and is out of scope here)

## Concerns or follow-ups

- None. The toolbar widget is now fully covered. The single remaining
  uncovered line is in `validation.py`, untouched by this ticket.
