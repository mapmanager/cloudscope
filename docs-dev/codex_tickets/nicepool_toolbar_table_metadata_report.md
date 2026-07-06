# NicePool toolbar, table, swarm fix, metadata to_dict

## Files changed

- `src/nicewidgets/nicepool/figure_generator.py`
- `src/nicewidgets/nicepool/pool_control_panel.py`
- `src/nicewidgets/nicepool/plot_pool_controller.py`
- `src/acqstore/acq_image/metadata.py`
- `src/cloudscope/views/velocity_pool_view.py`
- `tests/nicewidgets/test_plot_categorical_errors.py`
- `tests/nicewidgets/test_plot_pool_controller.py`
- `tests/acqstore/test_metadata.py`
- `tests/cloudscope/test_velocity_pool_view.py`

## Summary of implementation

- Fixed swarm plot color grouping to reuse sorted labels from
  `prepare_categorical_column` instead of `sorted(tmp["color"].unique())`.
- Split NicePool left toolbar into two rows; added **Copy full table** (full
  `self.df` as TSV via `copy_to_clipboard`, full text logged to console).
- Enabled `show_table_widget=True` in Velocity Pool view (table collapsed by
  default via existing vertical splitter).
- Excluded `_is_dirty` from `ExperimentMetadata.to_dict()` so sidecar saves
  no longer write internal state into `experiment_metadata`.

## One-off data fix (outside repo)

- Fixed 3 sidecar JSON files under
  `/Users/cudmore/Sites/cloudscope-data/data/manning_velocity_oir_20260625`
  (invalid `branch_order`/`depth` strings, missing `age`).

## Tests added or modified

- Added: `test_swarm_plot_with_color_grouping_does_not_crash_on_nullable_int_column`
- Modified: `test_swarm_plot_notifies_on_mixed_branch_order`
- Added: `test_copy_full_table_copies_entire_dataframe`
- Added: `test_experiment_metadata_to_dict_excludes_internal_dirty_flag`
- Modified: `test_velocity_pool_view` expects `show_table_widget=True`

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plot_categorical_errors.py tests/nicewidgets/test_plot_pool_controller.py tests/acqstore/test_metadata.py tests/cloudscope/test_velocity_pool_view.py -q
uv run pytest -q
```

## Test results

- Focused: **43 passed**
- Full suite: **1441 passed**, 5 failed (pre-existing in
  `tests/acqstore/test_acq_image_tree_rows.py`, unrelated to this ticket)

## Concerns or follow-ups

- Existing sidecars on disk may still contain `_is_dirty` until re-saved through
  CloudScope; new saves omit it.
