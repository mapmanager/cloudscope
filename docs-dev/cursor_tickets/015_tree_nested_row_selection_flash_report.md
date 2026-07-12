# 015 — Fix nested-row selection flash in the file list tree view

## Problem

Clicking a nested row (analysis / channel / ROI) in the file list tree view
caused a visible selection "flash": the clicked row was selected, then the
selection jumped to a *different* row (the previously selected sibling or the
parent file row), then settled — sometimes on the wrong row. Users reported
"1 but maybe 2 extra flashes" and occasional wrong final selection (e.g.
clicking sub-row 2 ending on sub-row 1).

## Diagnosis (browser, live, CDP-instrumented)

Ran the app as a local web server and loaded the diameter sample dataset via
the toolbar history menu:

```bash
CLOUDSCOPE_NATIVE=0 CLOUDSCOPE_PORT=8815 CLOUDSCOPE_SHOW=0 uv run python src/cloudscope/app.py
```

Instrumented the tree AG Grid (`getElement(637).api`) with listeners for
`selectionChanged` / `rowSelected` / `modelUpdated`, and wrapped the NiceGUI
element's `run_grid_method` / `run_row_method` to log every command Python sent.

Clicking sub-row `diameter` (with `sum_intensity` previously selected) produced
**two** full re-selection cycles from Python:

- Cycle 1: `applyTransaction` → `deselectAll` → `setSelected(sum_intensity)` — the **stale/old** selection.
- Cycle 2: `applyTransaction` → `deselectAll` → `setSelected(diameter)` — the newly clicked row.

Sequence the user saw: native click selects `diameter` → cycle 1 yanks selection
back to the old row (`sum_intensity`) → cycle 2 moves it to `diameter`. The two
cycles are a race; whichever lands last wins, which is why the final row was
sometimes wrong.

Root cause: `_replace_group_rows_from_acq_image` re-applied selection
(`_sync_table_selection`) after every subtree refresh. A lazy-load side-effect
event fires a subtree refresh **before** `FileSelectionChanged` updates
`current_selection`, so cycle 1 re-selects the stale selection. Ticket 001 added
that re-sync on the premise that "AG Grid `applyTransaction` drops client-side
selection even when the row id is unchanged."

That premise is **false**, verified in-browser: selecting a row and applying an
`update` transaction for it leaves it selected (`before == after`). AG Grid's
id-keyed `applyTransaction` (via `getRowId` = stable tree row id) preserves the
selection of surviving rows. The manual re-selection was therefore unnecessary
and was itself the flash.

## Fix

- `nicewidgets/tree_widget/tree_widget.py` — `set_selected_row_ids` is now
  idempotent: when the requested selection already equals the tracked selection,
  it updates bookkeeping and returns without issuing `deselectAll` /
  `setSelected`, eliminating redundant churn from repeated syncs.
- `cloudscope/views/file_list_tree_view.py`
  - `_replace_group_rows_from_acq_image` refreshes row DATA only and no longer
    re-applies selection (transactions preserve it).
  - `on_primary_selection_changed` now always calls `_sync_table_selection()`
    after the optional data refresh, so programmatic selection (e.g. pool-plot
    click) still selects the row; the idempotent guard makes the user-click echo
    a no-op.

## Browser verification (post-fix)

Same instrumentation, same dataset. Clicking `sum_intensity` and `diameter`:

- Command log: only `applyTransaction` (data refresh) ×2 per click.
- **Zero** `deselectAll`, **zero** `setSelected`.
- API/DOM selection equals the clicked row at every event, across both
  `modelUpdated` refreshes. No flash, no wrong final row.

## Files changed

- `src/nicewidgets/tree_widget/tree_widget.py`
- `src/cloudscope/views/file_list_tree_view.py`
- `tests/cloudscope/test_file_list_tree_view.py`
- `tests/nicewidgets/test_tree_widget_smoke.py`

## Tests

- Rewrote `test_replace_group_rows_re_syncs_selection_for_same_file` →
  `test_replace_group_rows_refreshes_data_without_touching_selection`
  (asserts the refresh replaces group data and does NOT churn selection).
- Renamed `test_replace_group_rows_does_not_re_sync_for_different_file` →
  `test_replace_group_rows_does_not_touch_selection_for_different_file`.
- Added `test_set_selected_row_ids_idempotent_skips_repeated_grid_churn`
  (repeated identical selection issues no grid commands; a different selection
  still does).

### Commands run

```bash
uv run pytest tests/cloudscope/test_file_list_tree_view.py tests/nicewidgets/test_tree_widget_smoke.py tests/cloudscope/test_base_view.py tests/cloudscope/test_controller.py -q
uv run pytest -q
```

### Results

- Focused: 93 passed.
- Full suite: 1873 passed, 1 skipped.

## Concerns / follow-ups

- If a subtree refresh ever *removes* the currently selected row (e.g. deleting
  the selected analysis), the row is filtered out of the sync target and the
  grid ends with no selection — expected behavior.
- The programmatic scroll-into-view for external selections remains partially
  effective (documented in ticket 014); it is untouched here.
