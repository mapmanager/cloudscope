# Tree widget index column and loaded indicator fix

## Files changed

- `src/acqstore/acq_image/acq_analysis_set.py`
- `src/nicewidgets/tree_widget/tree_widget.py`
- `src/nicewidgets/tree_widget/config.py`
- `src/nicewidgets/tree_widget/README.md`
- `src/cloudscope/views/file_list_tree_view.py`
- `tests/acqstore/test_results_csv_loaded.py`
- `tests/nicewidgets/test_tree_widget_smoke.py`
- `tests/cloudscope/test_file_list_tree_view.py`

## Summary of implementation

### Loaded ✅ (actual root cause)

Not a NiceGUI thread/AG Grid refresh bug. After lazy load on real OIR files,
`get_schema_row()['loaded']` stayed `''` because `is_fully_loaded` was false:

- `images_loaded` = true (pixels loaded; primary image view worked)
- `analysis_csv_loaded` = false — `results_csv_loaded()` required **every**
  analysis to have a non-None `result.table`
- Files with `heart_rate` (summary-only, no CSV sidecar) never satisfied that
  check, so the schema never emitted `'✅'`

**Fix:** `AcqAnalysisSet.results_csv_loaded()` now requires a loaded table only
for analyses whose CSV sidecar file exists on disk. Analyses without a sidecar
(e.g. `heart_rate`) no longer block loaded state.

Tree view: on `FileSelectionChanged`, when `acq_image.images_loaded`, rebuild
the file subtree via `_replace_group_rows_from_acq_image` (same path as metadata
Apply).

Reverted incorrect guesses: `ui.timer` UI-thread hop in
`AcqImageDataController`, row-id index maps, and `ui.run_javascript` grid
refreshes.

### Index column

- Static AG Grid `:valueGetter`: blank when `node.level !== 0`, else 1-based
  index from `forEachNode` over level-0 nodes (load order).
- `replace_group_rows` preserves group position in `_rows`.
- Column width: `4 * cell_font_size_px` (min 36px).

## Tests added or modified

- Added: `tests/acqstore/test_results_csv_loaded.py` (2 tests)
- Added/updated tree widget and file-list tree view smoke tests
- Modified: index column width tests

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_results_csv_loaded.py tests/cloudscope/test_file_list_tree_view.py tests/nicewidgets/test_tree_widget_smoke.py -q
```

Verified on dev dataset:

```bash
uv run python -c "..."  # load_lazy_data on A98_0002.oir -> loaded '✅'
```

## Test results

- **52 passed**
- Dev OIR file after `load_lazy_data`: `is_fully_loaded=True`, `loaded='✅'`

## Concerns or follow-ups

- Manual GUI check: click cold file row → wait for load → Loaded column shows ✅.
- If index width still clips at very large file counts (>999), bump multiplier
  slightly or pass a larger `table_font_size_px`.
