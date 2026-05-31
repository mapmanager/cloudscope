# Ticket 026 — Tree-view UX fixes from first app.py run

## Goal

Four UX/behavior fixes uncovered while running `uv run python src/cloudscope/app.py` after ticket 025 landed:

1. Batch analysis with "add new ROI per file" did not refresh the tree.
2. Analysis rows showed blank "Channels" / "ROIs" cells even though the channel and ROI used are known.
3. After "Run analysis", the previously selected analysis row visually lost its highlight, and during the long-running busy state the tree appeared to collapse all groups.
4. The Metadata panel (and other simple left-toolbar panels) had no scroll bar when content exceeded the panel height.

## Files changed

### Modified

- `src/acqstore/acq_image/acq_image.py` — `_build_analysis_tree_rows` now populates the display-overloaded schema fields `name`, `num_channels`, and `num_rois` on each analysis tree row.
- `src/cloudscope/views/file_list_tree_view.py` — removed view-side `_shape_rows` (AcqStore owns shaping); dropped the `if not event.success: return` guard in `_on_analysis_completed`; `_replace_group_rows_from_acq_image` re-applies the cached selection when it points to the same file.
- `src/nicewidgets/tree_widget/tree_widget.py` — `set_enabled` stops propagating `enabled`/`update()` to the inner AG Grid element. The root-level `pointer-events-none opacity-60` overlay is sufficient.
- `src/cloudscope/views/metadata_widget/metadata_view.py` — root column now uses `h-full min-h-0 flex-1 overflow-y-auto pr-1` so long metadata content scrolls inside the left-toolbar panel.
- `src/cloudscope/views/app_config_view.py` — same scroll classes on the root column.
- `src/cloudscope/views/app_info_view.py` — same scroll classes on the root column.

### Tests modified

- `tests/acqstore/test_acq_image_tree_rows.py` — `test_acq_image_tree_rows_analysis_row_keys_match_contract` updated to assert the new display-overloaded fields on analysis rows.
- `tests/cloudscope/test_file_list_tree_view.py` — fake `_analysis_row` updated to mirror the new AcqStore output; added `test_analysis_completed_refreshes_even_when_success_is_false`, `test_replace_group_rows_re_syncs_selection_for_same_file`, and `test_replace_group_rows_does_not_re_sync_for_different_file`.

### Added

- `docs/codex_tickets/026_tree_view_ux_fixes_report.md` — this report.

## Implementation notes

### Issue 1 — batch analysis tree refresh

`AnalysisController._publish_batch_analysis_completed` publishes per-file
`AnalysisCompleted` events whose `success` flag is the AND of the batch's
aggregate success and the per-file outcome. The tree view's
`_on_analysis_completed` previously short-circuited on `success=False`,
which suppressed the refresh for every successful file in any batch that
also had one failed file.

The underlying `AcqImage` is the authoritative source of truth for the
tree's content; whether to display a refreshed file row + analysis
children does not depend on the batch's aggregate success. The new
handler refreshes whenever `event.selection.file_id` is set.

### Issue 2 — analysis-row display values

Analysis rows previously left all file-list schema fields as `None`,
producing blank "Channels" / "ROIs" cells. The channel and ROI used for
each analysis are already present in the tree contract fields
(`channel`, `roi_id`), so the data exists; only the display path was
missing.

Per discussion, row-shaping for the tree is consolidated into
AcqStore (one canonical `_build_analysis_tree_rows`) rather than
splitting between AcqStore and the CloudScope view. AcqStore now sets:

- `name` → `analysis.key.analysis_name` (e.g. `"radon_velocity"`,
  shown in the chevron column).
- `num_channels` → `analysis.key.channel` (display-overloaded: the
  cell shows which channel was analysed).
- `num_rois` → `analysis.key.roi_id` (display-overloaded: the cell
  shows which ROI was analysed).

The tree-row identity fields (`channel`, `roi_id`, `analysis_name`)
remain the source of truth used by the controller and event system.
The schema-field overloads are display-only.

The CloudScope tree view's `_shape_rows` post-processing helper was
removed; `_read_tree_rows_from_state` now returns
`acq_image_list.get_tree_rows()` directly.

### Issue 3 — selection lost / visual collapse during analysis

Two distinct problems with the same root cause: state being lost
incidentally during normal tree-view updates.

**Selection lost on analysis completion**

`TreeWidget.replace_group_rows` performs an AG Grid `applyTransaction`
of update/add/remove for the affected file's children. Even when an
analysis row's stable `row_id` is unchanged, AG Grid drops the
client-side selection state for rows in the transaction. The tree view
never re-applied the cached selection after the replace.

Fix: `_replace_group_rows_from_acq_image` now calls
`self._sync_table_selection()` after `replace_group_rows` when
`self.current_selection.file_id == file_id`. This re-applies the
correct row (file row or analysis child row, depending on
`analysis_name`) for free, using the existing selection-sync logic.

**Visual collapse during the busy state**

`TreeWidget.set_enabled` previously toggled
`self._grid.enabled = enabled` followed by `self._grid.update()`. The
`update()` call re-pushes the element to the NiceGUI client, which can
cause AG Grid to lose client-side state (notably tree-group
expansion).

Fix: only toggle the root container's `pointer-events-none opacity-60`
overlay. The CSS overlay blocks pointer input across the entire widget
surface (including the AG Grid inside) without any client-side
re-render. The inner grid retains expansion / scroll / selection
state.

### Issue 4 — left-toolbar panel scroll

`LeftToolbarView` builds its child views inside a column with
`h-full min-h-0 w-full flex-1 gap-3 p-3 overflow-hidden`. The parent
clips overflow but does not scroll itself; each child must opt into
scrolling on its own root.

- `MetadataView`, `AppConfigView`, `AppInfoView` had `w-full` roots
  with no `flex-1` / `min-h-0` / `overflow-y-auto`. Long content
  overflowed below the panel with no scroll bar. Fixed by giving each
  root the same set of classes:
  `h-full min-h-0 flex-1 overflow-y-auto pr-1`.
- `VelocityAnalysisView` and `DiameterAnalysisView` already use their
  own internal `flex flex-col` + inner `overflow-y-auto` params
  container. Left untouched (no double-scroll risk).
- `EventAnalysisView` uses an `h-full min-h-0` root with a
  `flex-1 min-h-0` table parent inside that absorbs leftover height.
  Adding `overflow-y-auto` at the root would compete with the table's
  flex layout, so this view is deferred — see "Concerns" below.

I considered generalising scroll behavior by wrapping every child at
the `LeftToolbarView` parent level, but that would either nest a
scroll container around the velocity/diameter views that already
manage their own scroll (double-scroll surface) or require a per-view
opt-in flag. With three views needing the fix and one CSS-class
string, KISS argues for the per-view approach used here.

## Test commands and results

Focused:

```bash
uv run pytest tests/cloudscope/test_file_list_tree_view.py tests/acqstore/test_acq_image_tree_rows.py tests/nicewidgets/test_tree_widget_smoke.py -v
```

Result: 45 passed.

Full suite:

```bash
uv run pytest
```

Result: 805 passed, 3 pre-existing warnings.

## Concerns and follow-ups

- **EventAnalysisView scroll**: leftover; the view embeds a `flex-1`
  table that absorbs available height. If the controls/params/results
  area ever grows past the panel height, content will clip rather than
  scroll. A focused fix would restructure that view's layout into a
  scrollable header + sticky table. Not in scope for this ticket.
- **`TreeWidget.replace_group_rows` forces expand**: the helper still
  calls `expand_group(group_id)` at the end of every transaction. For
  the current selection-restore flow this is harmless, but it does
  override any manual collapse the user made on a group before
  analysis completed. Behavioural change deferred.
- **Ticket 027 — app-state typing refactor**: as previously agreed,
  the next ticket types `app_state` as `HomePageState | None` across
  `BaseView` and derived views and removes `getattr` probing. Plus a
  code review of the duplicated `current_selection` / `current_acq_image`
  state on each view vs the controller's source-of-truth state.
- **No deletion of `AcqImageListTableView`**: per the user's directive,
  the legacy table view stays as a maintained alternate so a single
  wiring swap in `home_page.py` can toggle between table and tree.
