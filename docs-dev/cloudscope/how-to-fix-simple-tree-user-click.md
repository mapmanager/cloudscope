# How to fix simple tree user-click (developer roadmap)

Scope: **all uncommitted changes** relative to the clean commit
`2e356b6` ("before another attempt at fixing file list tree view selection").
This covers two batches of work that were never committed:

1. **Selection-source + scroll-into-view** machinery (ticket 014).
2. **Nested-row click "flash" fix** (ticket 015, the part that finally worked).

This document is a post-hoc roadmap of what was done and why, so the changes can
be reviewed as a unit before committing.

---

## 1. The problem being solved

The file-list tree view (`AcqImageListTreeView`, an AG Grid tree over
`nicewidgets` `TreeWidget`) had two related selection defects:

### 1a. No scroll-into-view for programmatic selection (ticket 014)

When a row was selected from *outside* the tree (e.g. clicking a point in a
pool plot), the correct tree row became selected but was often **off-screen**.
The grid did not scroll to reveal it, so the user saw no visible feedback in the
tree. This needed to work for programmatic selection **without** affecting user
clicks inside the tree (an earlier attempt scrolled on every click, which was
bad UX).

### 1b. Nested-row selection "flash" on user click (ticket 015)

Clicking a nested row (analysis / channel / ROI) caused a visible selection
**flash**: the clicked row highlighted, then selection jumped to a *different*
row (the previously selected sibling or the parent file row), then settled —
sometimes on the wrong row. The user reported "1 but maybe 2 extra flashes" and
that clicking sub-row 2 sometimes ended on sub-row 1.

---

## 2. Status of the code before the plan (analysis)

### 2a. Events carried no origin

`SelectFileIntent` and `FileSelectionChanged` (`events/selection.py`) had no
field describing *where* a selection came from. Every consuming view therefore
treated a selection identically, whether it was:

- the user clicking a row in *this* tree,
- the user clicking in another surface (pool plot, legacy flat table),
- an initial/default selection from loading a file list,
- a channel/ROI-only change, or
- a view refreshing from cached app state on show.

With no origin, the tree could not implement "scroll into view for external
selections but not for my own clicks" — the two are indistinguishable at the
consumer. This is exactly the design-change prerequisite identified in the prior
session ("scroll-into-view can't be done correctly until `FileSelectionChanged`
carries a real selection origin").

### 2b. Subtree refresh re-applied selection (root of the flash)

`AcqImageListTreeView._replace_group_rows_from_acq_image()` did:

```python
self._tree.replace_group_rows(file_id, ...)
if self.current_selection.file_id == file_id:
    self._sync_table_selection()   # deselectAll + setSelected
```

The re-selection was added (ticket 001) on the premise that **AG Grid
`applyTransaction` drops client-side selection even when the row id is
unchanged**, so selection had to be manually re-applied after every subtree
refresh.

`on_primary_selection_changed()` also branched:

```python
if acq_image is not None and acq_image.images_loaded:
    self._replace_group_rows_from_acq_image(file_id)   # this re-synced selection
    return
self._sync_table_selection()
```

`TreeWidget.set_selected_row_ids()` unconditionally issued `deselectAll()` and
`setSelected()` every time it was called, even when the requested selection was
already the current selection.

### 2c. Why that produced the flash (confirmed live via CDP)

Running the app as a local web server, loading the diameter sample dataset, and
instrumenting the tree AG Grid (`getElement(<id>).api`) plus wrapping the NiceGUI
element's `run_grid_method` / `run_row_method` revealed that clicking one nested
row produced **two** full re-selection cycles from Python:

- Cycle 1: `applyTransaction` → `deselectAll` → `setSelected(<OLD/stale row>)`
- Cycle 2: `applyTransaction` → `deselectAll` → `setSelected(<clicked row>)`

Sequence the user saw: native click selects the clicked row → cycle 1 yanks
selection to the previously selected row (a lazy-load side-effect refresh runs
`_sync_table_selection()` against `current_selection` *before*
`FileSelectionChanged` updates it) → cycle 2 moves it to the clicked row. The
two cycles are a race; whichever lands last wins, which is why the final row was
sometimes wrong.

**Key fact established in-browser (this contradicts the ticket 001 premise):**
an `update`-only `applyTransaction` **preserves** selection. Selecting a row and
applying an `update` transaction for that same row (identity via `getRowId` =
stable tree row id) left it selected (`before == after`). So the manual
re-selection was not only unnecessary — it *was* the flash.

---

## 3. How the plan fixes it

### 3a. Thread a selection origin end-to-end (enables 1a, disambiguates 1b)

Add `SELECTION_SOURCE_*` string constants and a `source` field on both
`SelectFileIntent` and `FileSelectionChanged` (default
`SELECTION_SOURCE_EXTERNAL`). Producers stamp their origin; the controller
carries it into the published state event; `BaseView` records
`current_selection_source` so any view can branch on it.

- Tree click → `SELECTION_SOURCE_FILE_LIST_TREE`
- Legacy flat table click → `SELECTION_SOURCE_FILE_LIST_TABLE`
- Pool click → `SELECTION_SOURCE_VELOCITY_POOL`
- Load/default → `SELECTION_SOURCE_LOAD`
- Channel-only / ROI-only / refresh-from-state → `CHANNEL` / `ROI` / `REFRESH`
  sentinels

### 3b. Scroll into view only for external sources (1a)

Add `TreeWidget.scroll_row_id_into_view(row_id)` that scrolls to the row's
top-level ancestor (the file group row, always present even when collapsed) via
AG Grid `ensureNodeVisible(node, 'middle')`. It is **not** called from
`set_selected_row_ids`, so it can never fire as a side effect of selection.

The tree calls it from a new `_maybe_scroll_selection_into_view()` gated on
`current_selection_source in _SCROLL_INTO_VIEW_SOURCES` (external, table, pool,
load — deliberately excluding tree-click and channel/ROI/refresh). Result: a
user click inside the tree never auto-scrolls; an external selection does.

### 3c. Stop re-selecting on subtree refresh + make sync idempotent (1b)

- `_replace_group_rows_from_acq_image()` refreshes **row data only** and no
  longer calls `_sync_table_selection()`. Selection persistence is delegated to
  AG Grid's id-keyed transactions (verified to preserve selection).
- `on_primary_selection_changed()` always calls `_sync_table_selection()` after
  the optional data refresh, so programmatic selection (which has no native
  click to rely on) still selects the row.
- `TreeWidget.set_selected_row_ids()` gains an **idempotent guard**: if the
  requested selection already equals the tracked selection, it updates
  bookkeeping and returns without issuing `deselectAll` / `setSelected`. This
  makes the user-click echo a no-op and eliminates redundant churn.

Combined effect on a nested-row click: the stale-selection cycle 1 no longer
re-selects anything (the refresh is data-only, transaction preserves the
native-click selection); cycle 2's sync is idempotent (target already selected)
so it issues no grid commands. Selection stays on the clicked row throughout.

---

## 4. End result — the changes made

### Source

- `src/cloudscope/events/selection.py`
  - Added `SELECTION_SOURCE_*` constants.
  - Added `source: str = SELECTION_SOURCE_EXTERNAL` to `SelectFileIntent` and
    `FileSelectionChanged`.
- `src/cloudscope/controllers/home_page_controller.py`
  - Tracks `self._selection_source`; set to `LOAD` in `load_acq_image_list` /
    `load_demo_files`, and to `event.source` in the select-file handler; stamped
    onto the published `FileSelectionChanged`.
- `src/cloudscope/views/base_view.py`
  - Added `current_selection_source`; set from `event.source` on file-selection
    change, and to `CHANNEL` / `ROI` / `REFRESH` on the respective paths.
- `src/cloudscope/views/file_list_view.py`
  - Legacy flat table click stamps `SELECTION_SOURCE_FILE_LIST_TABLE`.
- `src/cloudscope/views/velocity_pool_view.py`
  - Pool click stamps `SELECTION_SOURCE_VELOCITY_POOL`.
- `src/cloudscope/views/file_list_tree_view.py`
  - Tree clicks stamp `SELECTION_SOURCE_FILE_LIST_TREE`.
  - Added `_SCROLL_INTO_VIEW_SOURCES`, `_current_selection_row_id()`,
    `_maybe_scroll_selection_into_view()`.
  - `on_primary_selection_changed()` now: optional data refresh → always
    `_sync_table_selection()` → `_maybe_scroll_selection_into_view()`.
  - `_replace_group_rows_from_acq_image()` refreshes data only (no re-select).
- `src/nicewidgets/tree_widget/tree_widget.py`
  - Added idempotent guard in `set_selected_row_ids()`.
  - Added `scroll_row_id_into_view()` (not called by `set_selected_row_ids`).

### Tests

- `tests/cloudscope/test_file_list_tree_view.py` — rewrote the
  `_replace_group_rows` selection tests to the new "refresh data, do not touch
  selection" contract; added source/scroll coverage.
- `tests/nicewidgets/test_tree_widget_smoke.py` — added
  `test_set_selected_row_ids_idempotent_skips_repeated_grid_churn` and a
  no-scroll-on-select assertion.
- `tests/cloudscope/test_base_view.py`, `test_controller.py`,
  `test_velocity_pool_view.py` — source propagation coverage.

### Rule doc

- `.cursor/rules/aggrid-source-of-truth.mdc` — added a blunt section demanding
  live browser verification for AG Grid changes and forbidding "unit tests pass"
  as evidence of a fix.

### Verification

- Full suite: **1873 passed, 1 skipped**.
- Flash fix verified live in the browser (diameter sample, CDP-instrumented):
  after the fix, a nested-row click produces only `applyTransaction` data
  refreshes with **zero** `deselectAll` / `setSelected`, and the API/DOM
  selection equals the clicked row at every event. No flash.

---

## 5. Friction and red flags in the final implementation

1. **The two batches are entangled in the same files and one commit-less diff.**
   `file_list_tree_view.py` and `tree_widget.py` contain both the 014 scroll
   work and the 015 flash fix. Reviewing/reverting one independently is not
   clean. Recommend committing as two logical commits if the history matters.

2. **Scroll-into-view (014) is only ~80% reliable and is known-imperfect.** It
   scrolls to the file group ancestor via `ensureNodeVisible`. Rows far down the
   list whose preceding files have expanded subtrees often do not end up
   visible. This was explicitly left as a partial/failed feature by the user;
   it ships but should not be treated as done.

3. **The rule doc contains a statement that is now known to be false.**
   `.cursor/rules/aggrid-source-of-truth.mdc` asserts "Web mode
   (`CLOUDSCOPE_NATIVE=0`) disables file loading". In practice, sample datasets
   load fine in web mode via the toolbar history/hamburger menu — which is how
   the 015 fix was verified. This line should be corrected or removed so future
   work does not skip browser verification on a false excuse.

4. **The flash fix reverses a ticket 001 premise but relies on empirical AG Grid
   behavior.** "`update` transactions preserve selection" was verified in the
   browser for `update`-only transactions. The `add`/`remove` cases are argued
   (surviving nodes keep selection) but not each independently re-verified live.
   If a future refresh path *removes* the selected row, the grid ends with no
   selection (expected, but worth noting).

5. **The idempotent guard trusts `self._selected_row_ids` as ground truth.** It
   skips grid commands when the requested selection equals the tracked
   selection. If tracked state ever diverges from the actual grid selection
   (e.g. a transaction removed then re-added the selected row without updating
   tracking), the guard could skip a needed re-selection. No such path is known
   today, but it is an implicit invariant the code now depends on.

6. **`current_selection_source` is per-view mutable state updated on every
   selection event.** It is correct for the synchronous handler flow used here,
   but any future async reordering between `FileSelectionChanged` and
   channel/ROI events could make the recorded source stale for a scroll
   decision.
