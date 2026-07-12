# 014 — Scroll-into-view for programmatic tree selection via selection source

## Problem

Two related file-list tree-view issues:

1. **Primary:** When a row is selected programmatically from another surface
   (e.g. a click in the velocity pool plot), the file-list tree correctly
   highlights the row but does not scroll it into view. Earlier attempts to add
   scrolling also fired on user clicks in the tree itself, causing bad UX
   (the table jumped/scrolled on every click). See
   `002_aggrid_scroll_into_view_failed_attempts.md`.

2. **Secondary (investigated, not fixed here):** clicking a nested
   analysis/channel/ROI row shows a brief "flashing" of selection between the
   nested row, the parent file row, and back.

The root cause of the primary issue was that `FileSelectionChanged` carried no
selection **origin**, so the tree could not tell its own click echo from an
external selection. Scroll therefore had to be all-or-nothing.

## Design change: selection source

Added an explicit selection **source** threaded from intent → controller →
state event → view. This lets the tree scroll only for external selections and
never for its own user clicks.

New constants in `cloudscope/events/selection.py`:

- `SELECTION_SOURCE_EXTERNAL` (default)
- `SELECTION_SOURCE_FILE_LIST_TREE` — tree's own click
- `SELECTION_SOURCE_FILE_LIST_TABLE` — legacy flat table click
- `SELECTION_SOURCE_VELOCITY_POOL` — pool plot/table click
- `SELECTION_SOURCE_LOAD` — file-list load (initial/default selection)
- `SELECTION_SOURCE_CHANNEL` / `SELECTION_SOURCE_ROI` / `SELECTION_SOURCE_REFRESH`
  — non-file-pick sentinels used by `BaseView`

`SelectFileIntent` and `FileSelectionChanged` gained a `source: str` field
(defaulting to `SELECTION_SOURCE_EXTERNAL`).

### Flow

- Emitters tag their `SelectFileIntent` with a source (tree/table/pool).
- `HomePageController` stores the source (`event.source`, or `LOAD` for
  `load_acq_image_list` / `load_demo_files`) and copies it onto the published
  `FileSelectionChanged`.
- `BaseView` stores `current_selection_source` from `FileSelectionChanged`, and
  uses `CHANNEL` / `ROI` / `REFRESH` sentinels for channel-only, ROI-only, and
  app-state refresh paths so those never scroll.
- `AcqImageListTreeView.on_primary_selection_changed()` applies the selection as
  before, then calls `_maybe_scroll_selection_into_view()`, which scrolls only
  when `current_selection_source` is in `_SCROLL_INTO_VIEW_SOURCES`
  (external / table / pool / load) — never `file_list_tree`, channel, ROI, or
  refresh.

### Scroll mechanism

`TreeWidget.scroll_row_id_into_view(row_id)` is a **new, standalone** public
method. It is intentionally NOT called by `set_selected_row_ids`, so the user
click round-trip never scrolls. It runs a small client script that resolves the
row node via `api.getRowNode(id)`, climbs to the top-level ancestor (always
present in displayed rows even when the group is collapsed), and calls
`api.ensureNodeVisible(node, 'middle')` (documented AG Grid API).

## Secondary issue (nested-row flashing) — ATTEMPTED AND REVERTED (FAILED)

Attempted fix: early-return in `on_primary_selection_changed()` for the tree's
own click echo (`SELECTION_SOURCE_FILE_LIST_TREE`), on the theory that AG Grid's
native click already selected the row and the controller echo only added
`applyTransaction` + `deselectAll`/`setSelected` churn.

Result per user testing on `./scripts/run app`: **DID NOT FIX IT.** A user click
still produces one or two extra row-selection flashes before settling, and for a
file with two sub-rows, clicking sub-row 2 sometimes settles on sub-row 1. The
early-return change was **reverted**.

Conclusion: the flashing is NOT solely caused by the click echo through
`on_primary_selection_changed`. The real source is somewhere else in the
selection round-trip (e.g. `TreeWidget._on_select_emitted`, `set_selected_row_ids`,
`replace_group_rows`/`applyTransaction`, `expand_group`, or the JS row-click hook)
and must be diagnosed with a live loaded dataset in a native run before any
further edit. No further speculative change was made.

## Scroll-into-view limitation (accepted)

Scroll targets the selected row's top-level (file) ancestor. When files above
the target have expanded subtrees, the computed target can still land partially
out of view in some cases (works ~80% of the time per user testing). Left as-is
at the user's direction; a fully correct version needs client-side displayed-row
index resolution verified in-browser.

## Files changed

- `src/cloudscope/events/selection.py` — source constants + `source` field on
  `SelectFileIntent` and `FileSelectionChanged`.
- `src/cloudscope/controllers/home_page_controller.py` — track and publish
  `source`.
- `src/cloudscope/views/base_view.py` — `current_selection_source` tracking with
  channel/ROI/refresh sentinels.
- `src/cloudscope/views/file_list_tree_view.py` — tag click source; add
  `_current_selection_row_id`, `_maybe_scroll_selection_into_view`,
  `_SCROLL_INTO_VIEW_SOURCES`; call scroll after selection. (The click-echo
  early-return flashing fix was attempted and REVERTED — it did not work.)
- `src/cloudscope/views/file_list_view.py` — tag legacy table click source.
- `src/cloudscope/views/velocity_pool_view.py` — tag pool click source.
- `src/nicewidgets/tree_widget/tree_widget.py` — `scroll_row_id_into_view`.

## Tests added or modified

- `tests/cloudscope/test_file_list_tree_view.py` — `FakeTree.scroll_row_id_into_view`
  recorder; scroll-on-external, scroll-targets-analysis-row, no-scroll-on-tree-click,
  no-scroll-on-channel, scroll-in-images-loaded-branch; assert click source on
  emitted intents. (The tree-click-echo no-mutation test was added then removed
  with the reverted flashing fix.)
- `tests/cloudscope/test_controller.py` — load source is `LOAD`; intent source
  propagates to `FileSelectionChanged`.
- `tests/cloudscope/test_base_view.py` — source tracked from
  `FileSelectionChanged`; channel/ROI use non-file sources.
- `tests/cloudscope/test_velocity_pool_view.py` — updated intent assertions to
  expect `SELECTION_SOURCE_VELOCITY_POOL`.
- `tests/nicewidgets/test_tree_widget_smoke.py` — scroll no-op without grid,
  scroll runs `ensureNodeVisible`, empty-id ignored, `set_selected_row_ids` does
  not scroll.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_file_list_tree_view.py tests/cloudscope/test_controller.py tests/cloudscope/test_base_view.py tests/nicewidgets/test_tree_widget_smoke.py -q
uv run pytest tests/ -q
```

## Test results

- Full suite: 1873 passed, 1 skipped.

## Concerns or follow-ups

- **Nested-row flashing is STILL BROKEN.** The click-echo early-return attempt
  was reverted after failing on a real native run. This needs live in-browser
  diagnosis with a loaded dataset (native mode, since web mode disables file
  loading) to find the actual source of the extra selection flashes before any
  further code change. Do not attempt another fix without that evidence.
- **Scroll-into-view** left partially working (~80%) per user direction; not
  correct when files above the target have expanded subtrees.
