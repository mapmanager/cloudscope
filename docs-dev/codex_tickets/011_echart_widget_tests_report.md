# Ticket 011 — EChartWidget option-building tests

## Files changed

- `tests/nicewidgets/test_echart_widget.py` — extended from 3 to 11 tests
- `docs/codex_tickets/011_echart_widget_tests_report.md` (this report)

## Summary of implementation

`EChartWidget` cannot be instantiated headlessly because `__init__` calls
`ui.echart(...)` which requires an active NiceGUI slot. The tests therefore
focus on the static helpers and the data-model conversion logic:

- `build_line_options` with and without `EChartAxisRange` bounds.
- `EChartWidget._empty_options()` shape (value axes, empty series, animation
  off).
- `EChartWidget._extract_x_brush_range()` empty / single-value / sorted /
  normal cases.
- `EChartEventOverlay.from_object` with int / string / `StrEnum` event types
  and the default `event_type='user'` branch.

## Tests added or modified

8 new tests in `tests/nicewidgets/test_echart_widget.py`.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_echart_widget.py -q
uv run pytest tests/nicewidgets/test_echart_widget.py tests/nicewidgets/test_echart_event_overlay.py --cov=nicewidgets.echart_widget --cov-report=term-missing -q
```

## Test results

- 11 passed (combined: 14 passed)
- `echart_widget/widget.py` coverage: **30% → 42%** (104 statements, 60 missed)
- `echart_widget` package overall: **65%** (rounded; was lower before)
- `echart_widget/models.py`: **100%**
- Remaining missed lines in `widget.py` are inside `__init__`,
  `apply()`, `clear()`, `set_x_axis_limits`, `reset_x_axis_limits`,
  `begin_select_x_range`, `cancel_select_x_range`, and the event handlers
  (`_on_*`) — all of which exercise `self.container` (the live NiceGUI
  `ui.echart` element) and cannot run without a NiceGUI slot.

## Concerns or follow-ups

- A `nicegui.testing` smoke test could instantiate `EChartWidget` inside a
  `ui.row()` and call `clear()`, `set_line_data()`, and the event handlers
  to push coverage well above 80%. Out of scope for this ticket.
