# 001 File list tree initial selection report

## Files changed

- `src/nicewidgets/tree_widget/tree_widget.py`
- `tests/nicewidgets/test_tree_widget_smoke.py`
- `docs-dev/cursor_tickets/001_file_list_tree_initial_selection_report.md`

## Problem

On a true cold start (app launches, `app_config.last_path` auto-loads a
file/channel/ROI while the file-list tree panel is collapsed/hidden), revealing
the panel afterward showed **no** selected row. The correct file was selected
everywhere else (status bar, channel/ROI controls); only the tree row was not
visually highlighted.

## Root cause (verified in-browser via CDP)

The failure is an AG Grid rendering quirk, not a timing/subscription problem:

- On cold start the tree panel is built while `acq_image_list` is empty
  (`initialize_once()` publishes an **async** `LoadPathIntent`; the server log
  shows `build(complete)` with `file_count=0`, then `Load completed (18/18)`).
  So the `ui.aggrid` element was created with **empty `rowData`**.
- An AG Grid instance that is **born with empty `rowData` and later filled**
  accepts programmatic selection *state* but never repaints the row:
  `api.getSelectedNodes()` returns the node and `node.isSelected() === true`,
  yet the row keeps `aria-selected="false"` with no `ag-row-selected` class.
  `redrawRows()` / `refreshCells()` / the new `api.setNodesSelected(...)` API do
  **not** fix it. A real user click *does* paint it.
- A grid **born with rows** (warm reconnect, where state already had data at
  build time) paints programmatic selection correctly. This was the decisive
  A/B observation.
- The tree's first rows on cold start actually arrive via
  `AcqImageListTreeView._replace_group_rows_from_acq_image()` →
  `TreeWidget.replace_group_rows()` (an AG Grid `applyTransaction`) during
  `BaseView.on_show()`'s `_refresh_primary_selection_from_state()`, i.e. before
  `refresh_from_state()`'s `set_data()`. Either way the grid was born empty and
  then filled, so it landed in the broken-paint state.

### Why the earlier (reverted) attempt failed

The first attempt retried `setSelected` on `gridReady`/`rowDataUpdated`. That
faithfully re-applied selection **state** that was already set, but the bug is a
**repaint** problem on a born-empty grid, so the visual never updated. Those
changes were reverted before implementing this fix.

## Summary of implementation

Never create a born-empty grid: build the `ui.aggrid` element **lazily**, only
once rows exist, so it is always born with rows and programmatic selection
paints correctly (matching the working warm-start path).

In `src/nicewidgets/tree_widget/tree_widget.py`:

- `build()` no longer creates the grid unconditionally; it creates the root and
  context menu and calls `_ensure_grid_built()`.
- New `_ensure_grid_built()` creates the grid (born with current rows) only when
  a root exists, the grid is not already built, and `self._rows` is non-empty.
- `set_data()` builds the grid lazily on the first non-empty data instead of
  pushing into a not-yet-built grid; otherwise it uses `grid.update()` as before
  (preserving tree expansion state for subsequent updates).
- `replace_group_rows()` and `update_row()` now build the grid lazily when it
  does not exist yet instead of early-returning.

No CloudScope view/lifecycle changes were needed; the existing
`on_show → set_data + _sync_table_selection` flow paints correctly once the grid
is born with rows. No `ui.timer()` used. Both file-list trees inherit the fix
via `AcqImageListTreeView` → `TreeWidget`.

## Tests added or modified

Added to `tests/nicewidgets/test_tree_widget_smoke.py`:

- `test_set_data_builds_lazy_grid_when_first_rows_arrive`
- `test_set_data_uses_update_when_grid_already_exists`
- `test_ensure_grid_built_no_op_without_root_or_rows`
- `test_replace_group_rows_builds_lazy_grid_when_absent`

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_tree_widget_smoke.py tests/cloudscope/test_file_list_tree_view.py -q
uv run pytest tests/nicewidgets tests/cloudscope -q
```

## Test results

```
61 passed in 1.31s
1351 passed, 3 warnings in 5.14s
```

## Browser verification (true single-page cold start)

```bash
CLOUDSCOPE_NATIVE=0 CLOUDSCOPE_PORT=8776 CLOUDSCOPE_SHOW=0 uv run python src/cloudscope/app.py
```

Navigate once, wait for `Load completed` on the same first-paint client, then
reveal the File list panel:

- Before fix: `ag-row-selected` count = 0 (API had the node selected, DOM did
  not paint it).
- After fix: `ag-row-selected` count = 1, `aria-selected="true"`, on the visible
  row `220110n_0003.tif` (12-file folder, groups collapsed). Status bar matches
  (`File: 220110n_0003.tif  Channel: 0  ROI: 1`).
- Regression: clicking a different file (`220110n_0009.tif`) moves the visual
  selection as expected.

## Concerns or follow-ups

- `TableWidget` uses a similar create-then-fill pattern; if a flat table shows
  the same born-empty programmatic-selection paint bug, apply the same lazy
  build there.
- Not reproduced/verified specifically under packaged native (pywebview) build;
  the fix is environment-agnostic (born-with-rows grid), and the web cold-start
  repro matches the reported native symptom.
