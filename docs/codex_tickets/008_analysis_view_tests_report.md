# Ticket 008 — Velocity / Diameter / Event analysis view tests

## Files changed

- `tests/cloudscope/test_velocity_analysis_view.py` — expanded from 3 to 11 tests
- `tests/cloudscope/test_diameter_analysis_view.py` — new file with 16 tests
- `tests/cloudscope/test_event_analysis_view.py` — new file with 25 tests
- `docs/codex_tickets/008_analysis_view_tests_report.md` (this report)

## Summary of implementation

The three analysis side panels each had little or no targeted tests. Adopted
the same headless testing pattern used elsewhere: construct each view with
`initially_visible=False` (no `build()`), assign small fake controls/buttons,
monkeypatch `ui.notify`, and assert on EventBus output.

### VelocityAnalysisView

- BaseView identity (`view_id`), no `_cancel_button` attribute.
- `_selection_snapshot` returns an independent copy of `current_selection`.
- `_on_roi_changed` only refreshes when the file id matches.
- `_on_analysis_completed` only rebuilds results for the matching RADON
  selection (filters out other kinds and other selections).
- `_current_detection_params` overrides defaults from registered controls.
- `_on_run_clicked` publishes RunAnalysisIntent for complete selections and
  is a no-op for incomplete ones (after `ui.notify` is patched).
- `_refresh_run_button` reads `has_valid_primary_selection()`.
- `_refresh_selection_label` handles unset and set selections.

### DiameterAnalysisView

- BaseView identity (`view_id`).
- `_field_visible_for_method` module-level helper.
- `_selection_snapshot` independence.
- `_on_analysis_completed` filters by kind+selection.
- `_on_roi_changed` filters by file id.
- `_selected_diameter_method`: default when no control, returns control value,
  default when control value is None.
- `_refresh_param_visibility` hides/shows controls based on the schema
  method filter.
- `_current_detection_params` skips hidden controls.
- `_on_run_clicked` happy path / no-op path.
- `_refresh_run_button`, `_refresh_selection_label` label cases.

### EventAnalysisView

- `_event_columns` exposes the expected fields.
- Intent emitters: `_add_event`, `_edit_event`, `_delete_selected`,
  `_cancel`, `_set_events_visible` publish the right intent.
- `_select_next` wraps at the end, picks the first id when none selected,
  advances by one mid-list, and publishes `None` when there are no rows.
- `_on_events_changed` ignores non-matching selections and updates rows /
  selected id / visibility / edit mode for matching ones.
- `_on_selection_changed` updates the selected event id.
- `_on_row_selected` publishes a SelectAcqImageEventIntent when idle and
  suppresses while in edit mode.
- `_on_analysis_completed` only acts on EVENT/RADON for the current
  selection.
- `refresh_from_state` publishes a refresh intent.
- `_can_run_event_analysis`: False without acq image, without Radon parent,
  without plot data, True with plot data.
- `_run_event_analysis` happy + incomplete branches.
- `_current_detection_params` uses defaults when no controls are present.
- `on_primary_selection_changed` resets internal state and publishes a
  refresh.

## Tests added or modified

11 + 16 + 25 = 52 tests across the three files.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_velocity_analysis_view.py tests/cloudscope/test_diameter_analysis_view.py tests/cloudscope/test_event_analysis_view.py -q
uv run pytest tests/cloudscope/test_velocity_analysis_view.py tests/cloudscope/test_diameter_analysis_view.py tests/cloudscope/test_event_analysis_view.py --cov=cloudscope.views.velocity_analysis_view --cov=cloudscope.views.diameter_analysis_view --cov=cloudscope.views.event_analysis_view --cov-report=term-missing -q
```

## Test results

- 52 passed
- `velocity_analysis_view.py`: **25% → 45%**
- `diameter_analysis_view.py`: **21% → 51%**
- `event_analysis_view.py`: **20% → 48%**
- Remaining gaps in all three files are `build()` + `_build_param_controls()` +
  `_build_results_controls()` + `_refresh_param_visibility()` (when iterating
  built controls) which all require an active NiceGUI client/slot.

## Concerns or follow-ups

- A future NiceGUI test-client smoke test could close the remaining build()
  gaps in all three analysis views.
- `EventControlsCard.set_controls_state` is exercised only indirectly via
  `_refresh_controls` (which requires the controls card built). Could be
  tested directly with fake buttons in a follow-up.
