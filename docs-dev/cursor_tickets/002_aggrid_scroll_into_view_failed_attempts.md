# 002 AG Grid scroll-into-view: failed attempts log

Status: **not implemented / reverted**. This is a cautionary record of repeated
failed attempts to make programmatic row selection in the file-list tree view
(`nicewidgets.tree_widget.TreeWidget`, backed by NiceGUI `ui.aggrid`) also
scroll the selected row into view. No scroll-into-view code currently exists;
the goal remains unmet.

## Goal (still unmet)

When a row is selected **programmatically** (e.g. the user clicks a point in a
Pool Plot, which drives a selection into the file-list tree), the tree should
scroll so the newly selected row is visible. Selection highlighting already
works; only the scroll does not.

## What is NOT the trigger

- `AcqImageListTreeView.refresh_from_state()` (called from `BaseView.on_show()`
  when the panel is revealed). Attempt 3 hooked scroll here. It is genuinely
  programmatic-only, but it is **not** the path exercised by the real scenario
  (cross-view selection like a Pool Plot click while the panel is already
  visible), so it did nothing useful.

## The real trigger path (source of truth)

Cross-view / programmatic selection arrives as:

```
<source> -> FileSelectionChanged
  -> BaseView._on_file_selection_changed
  -> BaseView.on_primary_selection_changed
  -> AcqImageListTreeView.on_primary_selection_changed
  -> AcqImageListTreeView._sync_table_selection
  -> TreeWidget.set_selected_row_ids(..., origin="state")
```

A **user click on a tree row** ALSO reaches the same
`set_selected_row_ids(origin="state")` via:

```
tree row click -> TreeWidget._on_select_emitted -> on_row_selected callback
  -> AcqImageListTreeView._on_row_selected -> publish SelectFileIntent
  -> controller -> FileSelectionChanged -> (same chain as above)
```

So `set_selected_row_ids` and `on_primary_selection_changed` are **shared** by
both user clicks and programmatic/cross-view selection, and at that point the
call is byte-for-byte identical (`origin="state"`). There is currently no
signal at that layer to distinguish "user clicked this tree row" from
"selection arrived from elsewhere".

## Attempts and why each failed

1. **Pending-selection + `gridReady`/`rowDataUpdated` retry** (earlier ticket
   001 territory). Retried `setSelected` on grid lifecycle events. This was
   aimed at a *paint* bug, not scroll, and did not address scroll at all.

2. **`ui.run_javascript` calling `getElement(id).api.ensureNodeVisible(node)`**
   (fire-and-forget). Did not move the viewport in practice. Fire-and-forget JS
   against the grid API was unreliable here; not the NiceGUI-sanctioned
   interaction channel.

3. **`run_grid_method('ensureIndexVisible', index, 'middle')` inside
   `set_selected_row_ids`.** The scroll call itself worked in the browser, BUT
   because `set_selected_row_ids` is on the shared path, it scrolled on **user
   clicks** too — re-centering a row the user just clicked. Bad UX. Reverted.

4. **`scroll_row_id_into_view` called only from `refresh_from_state()`.**
   Clean separation from user clicks, and `run_grid_method('ensureIndexVisible',
   ...)` is the NiceGUI-documented call
   (<https://nicegui.io/documentation/aggrid>). But `refresh_from_state` is the
   wrong trigger for the real scenario (see above), so it "did nothing" for the
   user's actual case (Pool Plot click). Reverted.

## Hard-won lessons (read before trying again)

- Do NOT attach scroll behavior to `TreeWidget.set_selected_row_ids` or
  `AcqImageListTreeView.on_primary_selection_changed` /
  `_sync_table_selection`: those are shared by user clicks and will cause
  click-time scrolling.
- The correct fix must distinguish selection **origin** (user tree-click echo
  vs. external/programmatic) BEFORE deciding to scroll. That signal does not
  exist today; it would need to be introduced (e.g. a real origin/source
  carried on `FileSelectionChanged` or a flag set by `_on_select_emitted` for
  the click echo). This is a design change, not a one-liner.
- The NiceGUI-sanctioned client call is
  `grid.run_grid_method('ensureIndexVisible', <index>[, position])`
  (verified against NiceGUI aggrid docs). `ui.run_javascript` against
  `api.*` was not reliable for scrolling in this app.
- For a tree with collapsed groups, a top-level row's displayed index equals
  its order among top-level rows (verified in-browser). This assumption breaks
  under sort/filter, which is another reason a naive index is fragile.
- Verify scroll behavior in the browser (per
  `.cursor/rules/verify-gui-in-browser.mdc` and
  `.cursor/rules/aggrid-source-of-truth.mdc`); unit tests asserting that a JS
  method name was emitted do NOT prove the viewport moved for the intended
  trigger.

## If attempting again

1. First add and thread a truthful selection **origin/source** through
   `FileSelectionChanged` so the tree can tell user-click echoes from external
   selections.
2. Only then, on the external/programmatic branch, call
   `run_grid_method('ensureIndexVisible', index)`.
3. Reproduce the exact user scenario (Pool Plot point click -> tree scrolls)
   in the browser before claiming success.
