# Ticket 003 — Expand EventAnalysisController tests

## Files changed

- `tests/cloudscope/test_event_analysis_controller.py` — expanded from 1 test to 33
- `docs/codex_tickets/003_event_analysis_controller_tests_report.md` (this report)

## Summary of implementation

`EventAnalysisController` previously had only one test covering the
"requires Radon velocity dependency" guard. The whole intent-handler surface
(`_on_begin_add`, `_on_begin_edit`, `_on_cancel_edit`, `_on_x_range_selected`,
`_on_delete_selected`, `_on_select_event`, `_on_set_visible`,
`_on_refresh_requested`, `_on_primary_selection_changed`) and the helpers
(`_required_selection_values`, `_copy_selection`, `_same_selection`, and the
module-level `_event_row`) were uncovered.

Added a `_make()` helper that wires the controller to an `EventBus`, captures
every published event type, and seeds a `FakeAnalysisSet` with optional
`FakeRadon` plot data and an optional real `EventAnalysis` instance. The fake
analysis set exposes `get` / `get_or_create` so the controller's actual
`get_or_create_event_analysis` and `_get_existing_event_analysis` paths run
end-to-end.

New tests cover:

- `_can_begin_edit_mode`: missing AcqImageList, missing Radon analysis,
  incomplete selection, in-progress edit-mode guard.
- `_on_begin_add`: enters ADD mode, publishes AppBusy + BeginPlotXRangeSelection
  + AcqImageEventsChanged.
- `_on_begin_edit`: warns when no event selected, warns when no event analysis,
  clears stale event id and republishes selection-change + events-changed when
  the event id no longer exists, enters EDIT mode otherwise.
- `_on_cancel_edit`: noop when idle, clears mode and publishes
  CancelPlotXRangeSelection + AcqImageEventsChanged while editing.
- `_on_x_range_selected`: ignored outside edit mode, ignored for stale
  selections, ADD path creates and selects the new event id, EDIT path
  updates coordinates, error path publishes ERROR + cancels edit.
- `_on_delete_selected`: warns when nothing selected, blocked while editing,
  removes the event and clears the selection, silently returns when no event
  analysis exists, publishes ERROR on delete failure.
- `_on_select_event`: sets/clears id and publishes selection change; suppressed
  during edit mode.
- `_on_set_visible`: toggles flag and republishes events changed.
- `_on_refresh_requested`: emits rows for selection / empty rows when no
  analysis.
- `_on_primary_selection_changed`: clears selection state, publishes rows,
  cancels any active edit mode.
- Helpers: `_required_selection_values`, `_copy_selection`, `_same_selection`,
  `_event_row`.

## Tests added or modified

33 tests in `tests/cloudscope/test_event_analysis_controller.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_event_analysis_controller.py -q
uv run pytest tests/cloudscope/test_event_analysis_controller.py --cov=cloudscope.controllers.event_analysis_controller --cov-report=term-missing -q
```

## Test results

- 33 passed
- `event_analysis_controller.py` coverage: **28% → 95%** (221 statements, 12 missed)
- Remaining missed lines (82, 99, 156, 312, 318, 333, 336, 339, 353-354, 357,
  360) are early-return / defensive raise branches in `_get_required_*` and
  `_get_existing_event_analysis` reached only when the test fixtures have a
  stale state (e.g. acq_image_list disappears between `_can_begin_edit_mode`
  and `_on_x_range_selected`). Could be covered with white-box mid-flow
  fixture mutations in a follow-up.

## Concerns or follow-ups

- The `_on_x_range_selected` EDIT-mode error path is covered by using
  `selected_event_id = None` and manually pushing the controller into EDIT
  mode; the same scenario could be reached via the public flow only via a
  race condition.
- `_event_row` returns event-stat values as opaque objects from
  `EventStats.to_json_dict()`; the test only asserts presence of keys.
