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
- Any collapsed ancestors of the requested row are expanded from root to leaf.
- Scrolling is deferred with `requestAnimationFrame()` so AG Grid can update its
  displayed row model after expansion before `ensureNodeVisible()` targets the
  selected child row.
- Existing selection-source gating remains unchanged: direct user clicks in the
  file-list tree do not trigger automatic scrolling, while supported external
  selection sources such as pool plots still do.

## Tests added or modified

- Replaced the old ancestor-scroll assertion with coverage that verifies:
  - JavaScript is sent through the grid element's explicit client;
  - the actual requested row id is resolved;
  - collapsed ancestors are expanded;
  - scrolling is deferred with `requestAnimationFrame()`;
  - `ensureNodeVisible()` targets the selected row rather than its root file
    ancestor.
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
78 passed in 5.83s
```

Full suite:

```text
1868 passed, 16 skipped, 15 warnings in 29.21s
```

The 16 skips are existing missing uploaded/sample fixture skips. The warnings
are existing collection, SciPy deprecation, and all-NaN raster warnings.

## Concerns or follow-ups

- Native-app visual verification was not available in this container. The
  changed JavaScript flow is covered structurally by unit tests, and the full
  automated suite passes.
- The implementation uses one `requestAnimationFrame()` after ancestor
  expansion. This is the smallest browser-side delay needed to allow AG Grid to
  refresh displayed rows before scrolling. If a packaged-client-specific AG
  Grid timing issue is observed later, verify live before adding retries or
  timers.
