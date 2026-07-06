# Ticket 025 — Swap file-list view to TreeWidget via parallel `AcqImageListTreeView`

## Goal

Replace the `TableWidget`-based file-list view in CloudScope with a
`TreeWidget`-based view, using a parallel `AcqImageListTreeView` so the
swap is a single-line wiring change and the legacy table view remains
untouched (and trivially reversible).

## Strategy

- Build a new view `cloudscope.views.file_list_tree_view.AcqImageListTreeView`
  next to the existing `AcqImageListTableView`.
- Swap a single import + class name in `cloudscope.pages.home_page.HomePage.build`.
- Extend selection plumbing additively (all new fields default to
  `None`) so non-tree call sites are unaffected:
  - `SelectFileIntent` gains optional `channel`, `roi_id`,
    `analysis_name`.
  - `FileSelectionChanged` gains optional `analysis_name`.
  - `PrimarySelection` gains optional `analysis_name`.
- Centralize chevron-column configuration in `schema_adapters` via a
  new keyword-only kwarg `tree_group_display_field` (defaults to `None`,
  so the schema adapter behaves exactly as before for non-tree callers).
- Drive tree rows from the AcqStore tree-row API added in Ticket 024
  (`AcqImage.get_tree_rows()`, `AcqImageList.get_tree_rows()`) and from
  `acqstore.acq_image.tree_rows` constants.

The legacy `AcqImageListTableView` and its tests are intentionally
kept. A future ticket (027) can delete them once the tree view has
soaked.

## Files changed

### Added
- `src/cloudscope/views/file_list_tree_view.py` —
  `AcqImageListTreeView`, the new parallel view.
- `tests/cloudscope/test_file_list_tree_view.py` — focused unit tests
  for the new view (13 tests).
- `docs/codex_tickets/025_swap_file_list_view_to_treewidget_report.md`
  — this report.

### Modified
- `src/cloudscope/events/selection.py` — extended `SelectFileIntent`
  with optional `channel`, `roi_id`, `analysis_name`; extended
  `FileSelectionChanged` with optional `analysis_name`. Both additive,
  defaults `None`.
- `src/cloudscope/state.py` — extended `PrimarySelection` with
  optional `analysis_name` (default `None`). Detailed docstring covers
  the analysis-row contract and the channel/ROI-change clearing
  policy.
- `src/cloudscope/controllers/home_page_controller.py` —
  `_on_select_file` now honors event-supplied `channel`, `roi_id`,
  `analysis_name`; `_on_select_channel` and `select_roi` clear
  `analysis_name`. `_publish_file_selection_changed` propagates
  `analysis_name`.
- `src/cloudscope/views/base_view.py` — `_on_file_selection_changed`
  and `_refresh_primary_selection_from_state` propagate
  `analysis_name` into cached `current_selection`. Channel- and
  ROI-selection-changed handlers clear `current_selection.analysis_name`.
- `src/cloudscope/schema_adapters.py` — `schema_to_column_defs`
  accepts optional keyword-only `tree_group_display_field`. When set,
  the matching column gets
  `cellRenderer: 'agGroupCellRenderer'` and
  `cellRendererParams: {'suppressCount': True}` injected into
  `ColumnDef.extra`. Raises `KeyError` when the field name is unknown.
- `src/cloudscope/pages/home_page.py` — one-line import swap and
  one-line class swap from `AcqImageListTableView` to
  `AcqImageListTreeView`. No other wiring changes.
- `tests/cloudscope/test_controller.py` — three new tests covering
  the analysis-row selection propagation path and channel/ROI
  clearing of `analysis_name`.

## Design notes

### Why a parallel view rather than mutating the existing one?

- Keeps the diff additive and reversible (revert one import + one
  class name to fall back to the table view).
- Lets the new view consume the AcqStore tree-row API directly
  without breaking other callers that rely on `get_schema_rows()`.
- Lets the legacy table-view tests keep passing unchanged.

### Why does the tree view ignore `FileListChanged.rows` and `MetadataChanged.file_list_row`?

Those payloads are flat schema rows shaped for the legacy table view.
The tree view rebuilds rows from `app_state.acq_image_list` and from
the targeted `AcqImage` to keep AcqStore as the single source of truth
for hierarchy and identity. Other consumers of these events (legacy
table view, metadata view, batch dialogs) are unaffected.

### Where is the chevron-column field name defined?

`AcqImageListTreeView._TREE_CHEVRON_COLUMN_FIELD = "name"` lives in
the view module because the chevron column is a display decision
specific to this view. AcqStore intentionally does not encode display
intent; the tree-row contract in `acqstore.acq_image.tree_rows` only
declares row identity, hierarchy, and analysis identity fields.

### How are analysis rows labeled?

AcqStore returns analysis rows with all file-list-schema fields set to
`None`. `AcqImageListTreeView._shape_rows` post-processes analysis
rows by copying `analysis_name` into the chevron column field
(`name`), so the tree displays e.g. `"radon_velocity"` next to the
disclosure chevron for an analysis child row.

### What does `get_displayed_file_ids` return for the tree view?

Only file rows (`tree_row_type == "file"`) in current AG Grid visible
order, after user filtering and sorting. Analysis child rows are
intentionally excluded, because CloudScope batch analysis consumes
files, not analyses.

### Selection sync

`_sync_table_selection` picks the analysis tree row id (via
`build_analysis_tree_row_id`) when `current_selection.analysis_name`
is set; otherwise it selects the file row by `file_id`. This makes
analysis-row clicks visibly persistent until the user picks something
else, channel/ROI change events explicitly clear `analysis_name`, or
the file changes.

### Channel / ROI selection changes clear `analysis_name`

When the user changes channel or ROI through any path other than the
tree view (e.g. ImageToolbar, ROI overlay), the controller and
BaseView both clear `analysis_name` because the previously-selected
analysis row identity is no longer valid. The next state event makes
the tree view fall back to selecting the file row.

## Tests

### Added focused tree-view tests (`tests/cloudscope/test_file_list_tree_view.py`, 13 tests)

- `test_refresh_from_state_reads_tree_rows_from_app_state`
- `test_file_list_changed_rebuilds_from_app_state_not_event_rows`
- `test_metadata_changed_replaces_one_subtree_from_app_state`
- `test_analysis_completed_replaces_subtree_from_app_state`
- `test_roi_changed_replaces_subtree_from_app_state`
- `test_acq_image_events_changed_replaces_subtree_from_app_state`
- `test_on_row_selected_publishes_simple_intent_for_file_row`
- `test_on_row_selected_publishes_full_intent_for_analysis_row`
- `test_sync_table_selection_selects_file_row_when_no_analysis_name`
- `test_sync_table_selection_selects_analysis_row_when_analysis_name_set`
- `test_sync_table_selection_clears_when_no_file_id`
- `test_get_displayed_file_ids_filters_to_file_rows_only`
- `test_forwards_enabled_state_to_tree`

### Added controller selection tests (`tests/cloudscope/test_controller.py`)

- `test_select_file_with_analysis_fields_propagates_through_state`
- `test_select_channel_clears_analysis_name`
- `test_select_roi_clears_analysis_name`

### Test commands and results

Focused:

```bash
uv run pytest tests/cloudscope/test_file_list_tree_view.py tests/cloudscope/test_controller.py -v
```

Result: 19 passed.

Full suite:

```bash
uv run pytest
```

Result: 802 passed, 3 warnings.

## Concerns and follow-ups

- **Ticket 026 (deferred)** — Type `app_state` as `HomePageState | None`
  directly across `BaseView` and derived views; remove `getattr`-based
  probing in `velocity_analysis_view`, `diameter_analysis_view`, etc.
  Also review and de-duplicate `current_selection` / `current_acq_image`
  storage in `BaseView` and derived views (the views maintain their
  own copies of selection state in addition to the controller's
  source-of-truth `HomePageState.selection`).
- **Ticket 027 (deferred)** — Delete `AcqImageListTableView` and
  `tests/cloudscope/test_file_list_view*.py` once the tree view is
  validated against `app.py`.
- **Polish** — `Analysis Type` column or icon next to the chevron name,
  default-expand-first-N rows, analysis-row hover hint that maps the
  channel/ROI columns even though they are blank for the file row's
  perspective. Not in scope for this ticket.
