# 017 Tree scroll client context and target report

## Files changed

- `src/nicewidgets/tree_widget/tree_widget.py`
- `tests/nicewidgets/test_tree_widget_smoke.py`
- `docs-dev/cursor_tickets/017_tree_scroll_client_context_and_target_report.md`

## Summary of implementation

- Updated `TreeWidget.scroll_row_id_into_view()` to dispatch JavaScript through
  `self._grid.client.run_javascript(...)` instead of the ambient
  `ui.run_javascript(...)` helper.
- The explicit grid client makes programmatic scrolling safe when selection is
  published from an asynchronous lazy-load completion task with no active
  NiceGUI slot stack.
- The method now retains the actual requested AG Grid row node instead of
  replacing it with the top-level file ancestor.
- The implementation uses AG Grid's documented
  `setRowNodeExpanded(target, true, true, {forceSync: true})` API to expand the
  requested row and all parent nodes synchronously.
- The synchronous expansion contract allows `ensureNodeVisible()` to target the
  requested child immediately, without manual parent traversal or an animation-
  frame timing assumption.
- Existing selection-source gating remains unchanged: direct user clicks in the
  file-list tree do not trigger automatic scrolling, while supported external
  selection sources such as pool plots still do.

## Tests added or modified

- Replaced the old ancestor-scroll assertion with coverage that verifies:
  - JavaScript is sent through the grid element's explicit client;
  - the actual requested row id is resolved;
  - AG Grid's public `setRowNodeExpanded()` API expands all ancestors;
  - synchronous expansion is requested with `{forceSync: true}`;
  - `ensureNodeVisible()` targets the selected row rather than its root file
    ancestor;
  - manual parent traversal and `requestAnimationFrame()` are not used.
- Updated the empty-row-id test to use the explicit fake grid client and verify
  no JavaScript is sent.
- Retained the existing no-grid no-op test and CloudScope source-gating tests.

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_tree_widget_smoke.py tests/cloudscope/test_file_list_tree_view.py -q
uv run pytest -q
```

## Test results

Focused tests:

```text
78 passed in 5.63s
```

Full suite:

```text
1868 passed, 16 skipped, 15 warnings in 33.13s
```

The 16 skips are existing missing uploaded/sample fixture skips. The warnings
are existing collection, SciPy deprecation, and all-NaN raster warnings.

## Concerns or follow-ups

- Native-app visual verification was not available in this container. The
  changed JavaScript flow is covered structurally by unit tests, and the full
  automated suite passes.
- The implementation now relies on AG Grid's documented synchronous expansion
  option rather than a browser-frame delay. If packaged-client behavior differs,
  verify it live before adding retries or timers.
