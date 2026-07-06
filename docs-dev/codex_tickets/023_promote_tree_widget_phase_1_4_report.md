# Ticket 023: Promote TreeWidget to nicewidgets (Phase 1-4)

## Files changed

- `src/nicewidgets/aggrid_common/__init__.py`
- `src/nicewidgets/aggrid_common/column_def.py`
- `src/nicewidgets/table_widget/column_def.py`
- `src/nicewidgets/tree_widget/__init__.py`
- `src/nicewidgets/tree_widget/config.py`
- `src/nicewidgets/tree_widget/js_hooks.py`
- `src/nicewidgets/tree_widget/tree_widget.py`
- `src/nicewidgets/tree_widget/README.md`
- `sandbox/demo_tree_app/demo_tree_app.py`
- `tests/nicewidgets/test_tree_widget_smoke.py`

## Summary of implementation

Implemented Phase 1-4 without touching `cloudscope/views/file_list_view.py`:

1. **Phase 1: shared ColumnDef extraction**
   - Added `nicewidgets.aggrid_common.column_def.ColumnDef`.
   - Kept backward compatibility by re-exporting `ColumnDef` from
     `nicewidgets.table_widget.column_def`.

2. **Phase 2: tree_widget package scaffold**
   - Added `TreeWidgetConfig` with a focused surface (selection, sizing,
     keyboard nav, grid merge options, enterprise module URL).
   - Added tree-specific JS hooks for row click and ArrowUp/ArrowDown row nav.
   - Added package README.

3. **Phase 3: TreeWidget implementation**
   - Implemented cloudscope-focused public API subset:
     - `build`, `set_enabled`
     - `set_data`, `update_row`, `replace_group_rows`
     - `get_selected_rows`, `set_selected_row_ids`, `clear_selection`
     - `expand_all_nodes`, `collapse_all_nodes`, `expand_group`
     - `get_displayed_rows`
   - Added row-id validation parity with `TableWidget`.
   - Added context menu composition with caller hook, expand/collapse actions,
     copy action, and column visibility toggles.
   - Added AG Grid tree options (`treeData`, `getDataPath`, `getRowId`,
     `groupDisplayType: custom` fallback, enterprise modules).

4. **Phase 4: demo port**
   - Removed in-file `TreeWidget` from sandbox demo.
   - Switched demo to import and use `nicewidgets.tree_widget.TreeWidget`.
   - Converted demo column definitions from raw dicts to shared `ColumnDef`.
   - Preserved existing domain/app-controller split and tree behavior.

## Tests added or modified

- Added:
  - `tests/nicewidgets/test_tree_widget_smoke.py`
- Existing table widget tests were intentionally re-run to validate no
  regression from shared `ColumnDef` extraction.

## Exact test commands run

- `uv run pytest tests/nicewidgets/test_tree_widget_smoke.py tests/nicewidgets/test_table_widget_smoke.py tests/nicewidgets/test_table_widget_context_menu.py tests/nicewidgets/test_table_widget_resize_config.py`

## Test results

- `51 passed in 0.39s`

## Concerns / follow-ups

- Per scope decision, **no changes were made** to
  `src/cloudscope/views/file_list_view.py` (still uses `TableWidget`).
- Phase 5 (future ticket): migrate cloudscope file-list view to `TreeWidget`
  and update upstream AcqStore row shaping (`hierarchy_path`, group renderer
  host column contract) in a laser-focused change.

---

## Refinements (post-review)

User-driven critique of the initial Phase 1-4 implementation surfaced two
defects and two scope checks. Both defects are fixed in this same ticket.

### Fix #1 -- Disclosure triangles missing

**Symptom**: tree rows rendered with no expand/collapse chevrons on the
`file_name` column despite `cellRenderer: 'agGroupCellRenderer'` being set.

#### First attempt (incorrect)

The first refinement pass replaced `groupDisplayType: 'custom'` with
`treeDataDisplayType: 'custom'` based on a hypothesis about an AG Grid v32+
option split. That hypothesis was **wrong** and was not verified against
v34 docs at the time. A unit-test added in the same pass only checked option
key presence (not actual chevron rendering), so it passed even though the
runtime behavior was still broken.

User confirmed end-to-end that triangles were still missing after the first
attempt.

#### Second attempt (correct, verified against AG Grid v34 docs)

Verified against the AG Grid v34 grid options reference and the
ag-grid-angular@35.x API export:

- `groupDisplayType` is type `RowGroupingDisplayType`; values
  `'singleColumn' | 'multipleColumns' | 'groupRows' | 'custom'`. **Documented
  to apply to both row grouping AND tree data.**
- `treeDataDisplayType` is typed `TreeDataDisplayType` but does **not**
  accept `'custom'` as a value. Setting `treeDataDisplayType: 'custom'` is
  silently ignored, falling AG Grid back to the default tree-data
  auto-group column. That is what produced the user's "no chevrons" view.

For `groupDisplayType: 'custom'` to wire chevrons to a caller-defined
column deterministically, AG Grid additionally requires
`showRowGroup: True` on that column (alongside
`cellRenderer: 'agGroupCellRenderer'`). This is documented in AG Grid's
group cell renderer docs and in the Plotly Dash AG Grid reference example.

**Final fix**:

1. Reverted `treeDataDisplayType: 'custom'` -> `groupDisplayType: 'custom'`
   in `_build_aggrid_options` (the no-`autoGroupColumnDef` branch).
2. Added a module-level helper `_auto_inject_show_row_group(column_defs)`
   that mutates `column_defs` in place to set `showRowGroup: True` on the
   first column whose `cellRenderer == 'agGroupCellRenderer'` (no-op when
   any column already has truthy `showRowGroup`, no-op when no such
   `cellRenderer` is set).
3. Called it from `TreeWidget.__init__` whenever `auto_group_column_def`
   is `None`. This removes a footgun: callers may forget `showRowGroup`,
   and AG Grid's heuristic detection of the chevron host column is fragile.
4. Updated test to assert `groupDisplayType: 'custom'` and absence of
   `treeDataDisplayType`. Added four focused tests for the auto-injection
   helper (positive case, idempotence, no-op without group renderer
   column, and end-to-end through `TreeWidget.__init__` including the
   `auto_group_column_def` skip path).

#### Process note

End-to-end browser verification (chevrons actually visible) is needed for
this kind of change; passing unit tests alone are insufficient when the
underlying library silently ignores unknown option values.

### Fix #2 -- "Copy Table Data" worked native=True but not native=False

**Symptom**: right-click context menu's "Copy Table Data" silently failed in
browser mode (NiceGUI `ui.run(native=False)`).

**Root cause**: browser clipboard write requires the call to remain inside the
originating user-gesture context. The original implementation did:

1. menu_item click (gesture active)
2. `await self.get_displayed_rows()` -- one Python<->browser round-trip
   (gesture consumed)
3. `copy_to_clipboard(text)` -- second JS round-trip with
   `navigator.clipboard.writeText` -- browser rejected (no gesture).

Native mode was unaffected because pyperclip writes the OS clipboard with no
gesture requirement.

**Fix**: rewrote `_copy_table_data_to_clipboard` so the browser path performs
displayed-rows fetch + TSV build + clipboard write in a single
`ui.run_javascript` round-trip. The JS uses
`api.forEachNodeAfterFilterAndSort` to read the visible rows, builds a TSV
using the widget's visible columns (passed in via JSON literals), then writes
via `navigator.clipboard.writeText` with a legacy
`document.execCommand('copy')` fallback for non-secure contexts. Native window
mode keeps using `pyperclip` against the current Python-side rows.

### Scope check #3 -- `visible_file_ids_provider` for batch analysis

CloudScope's diameter and velocity batch analyses depend on:

```text
home_page.py:117               app_state.visible_file_ids_provider = file_list_panel.get_displayed_file_ids
file_list_view.py:135-153      get_displayed_file_ids() -> await self._table.get_displayed_rows()
diameter_analysis_view.py:355  file_ids = await provider()
velocity_analysis_view.py:309  file_ids = await provider()
```

`TreeWidget.get_displayed_rows()` already mirrors `TableWidget.get_displayed_rows()`
shape (async, returns `list[dict[str, Any]]` after AG Grid filter+sort). No
new widget API required. When Phase 5 swaps the file-list view to
`TreeWidget`, `get_displayed_file_ids` will need to filter to top-level rows
only (e.g. `len(row[path_field]) == 1`); that is a `file_list_view` adapter
concern, not a widget feature gap.

### Scope check #4 -- `event_analysis_view.py` usage

The event analysis view's TableWidget consumption is a strict subset of the
file-list view's. It calls only `build`, `set_data`, `clear_selection`,
`set_selected_row_ids` and constructs with `columns`, `row_id_field`, `rows`,
`on_row_selected`, and a `TableWidgetConfig` (selection mode, sizing,
`extra_grid_options`, `show_index_column=False`). All of those are already
covered by `TreeWidget` / `TreeWidgetConfig`. **No new feature required.**

### Refinement test results

```bash
uv run pytest tests/nicewidgets/test_tree_widget_smoke.py
```

- **22 passed** (was 17 before the disclosure-triangle re-fix; +5 tests
  cover the corrected `groupDisplayType` option key and the new
  `_auto_inject_show_row_group` helper).

### Fix #5 -- AG Grid Enterprise default context menu shadowed ours

**Symptom**: right-clicking on a tree cell showed the AG Grid Enterprise
default menu (`Copy`, `Copy with Headers`, `Export`, etc.) instead of the
NiceGUI `ui.context_menu` we install. The AG Grid menu intercepts the
`contextmenu` DOM event before it reaches NiceGUI's handler.

**Fix**: always set `suppressContextMenu: True` and
`preventDefaultOnContextMenu: True` in `_build_aggrid_options`. This
disables AG Grid's Enterprise menu and also asks AG Grid to block the
browser's native menu over the grid surface, leaving the NiceGUI
`on_build_context_menu` menu as the single source of truth for right-click
actions.

### Refinement files changed

- `src/nicewidgets/tree_widget/tree_widget.py`
- `src/nicewidgets/tree_widget/README.md`
- `tests/nicewidgets/test_tree_widget_smoke.py`
- `docs/codex_tickets/023_promote_tree_widget_phase_1_4_report.md` (this file)

### Scope check #6 -- demo controller/adapter helper functions

User asked whether the five helpers in `sandbox/demo_tree_app/demo_tree_app.py`
(lines 150-264: `_analysis_id`, `_file_tree_row`, `_analysis_tree_row`,
`_subtree_rows`, `_all_tree_rows`) should be folded into `TreeWidget`, or
whether the widget needs new configuration knobs to absorb their work.

**Verdict**: keep them outside `TreeWidget`. All five are domain adapters
that embed CloudScope/AcqStore concepts the widget must not know about:

| Helper | Domain knowledge it embeds |
|---|---|
| `_analysis_id` | analysis id encoding (channel, ROI, type, file path) |
| `_file_tree_row` | depth-1 row shape; `row_type='File'`; `as_row_dict()` |
| `_analysis_tree_row` | depth-2 row shape; sentinel `None` on file-level fields; reuse of `channels`/`rois` columns as id columns at depth 2 |
| `_subtree_rows` | parent + children iteration order over `file.analyses` |
| `_all_tree_rows` | iteration over the domain collection (`files_map.values()`) |

Three speculative widget-side configurations were considered and rejected:

- A `row_builder: Callable[[T], list[dict]]` callback would force the
  widget to know about a generic domain type `T`, breaking the
  `nicewidgets` package boundary.
- A field-name map for `row_type` / depth-2 sentinel handling is
  premature abstraction with one caller.
- An "analysis id encoder" is purely cloudscope-specific.

The widget's existing API (typed `columns`, `row_id_field`, `path_field`,
`set_data`, `replace_group_rows`) is sufficient. The helpers will be
ported into CloudScope (or onto AcqStore domain types) in Phase 5; that
is the appropriate boundary.

A new "Caller responsibility: shaping rows from your domain" section was
added to `src/nicewidgets/tree_widget/README.md` documenting the adapter
pattern with the demo's helpers as the canonical example.

### Phase 5 follow-up: where these helpers should live

When CloudScope swaps `file_list_view.AcqImageListTableView` to
`TreeWidget`, equivalents of these five helpers are needed for the real
`AcqImage` / `AcqImageList` types. Recommended placement:

- `AcqImage.get_tree_rows(row_id_field='row_id', path_field='hierarchy_path') -> list[dict[str, Any]]`
  -- mirrors the existing `get_schema_row()` pattern; returns parent +
  analysis rows for one image.
- `AcqImageList.get_tree_rows(...)` -- flattens across the collection.

This keeps row shaping in `acqstore` (single source of truth, no widget
dependency), gives CloudScope a one-line call site, and keeps the widget
agnostic. That is a separate ticket on `acqstore`; out of scope here.

### Known limitation / follow-up

- `TableWidget` has the same browser-mode clipboard bug (uses the same
  shared `nicewidgets.utils.clipboard.copy_to_clipboard` after an awaited
  displayed-rows query). Out of scope for this ticket; recommend a separate
  ticket to apply the same single-roundtrip pattern to `TableWidget`.
