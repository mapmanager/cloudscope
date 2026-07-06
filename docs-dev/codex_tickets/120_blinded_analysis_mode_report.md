# 120 Blinded Analysis Mode Report

## Files changed

- `src/cloudscope/app_config.py`
- `src/cloudscope/blinded_display.py`
- `src/cloudscope/events/app_config.py`
- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/pages/pool_page.py`
- `src/cloudscope/views/app_config_view.py`
- `src/cloudscope/views/base_view.py`
- `src/cloudscope/views/dialogs/batch_analysis_dialog.py`
- `src/cloudscope/views/diameter_analysis_view.py`
- `src/cloudscope/views/file_list_tree_view.py`
- `src/cloudscope/views/file_list_view.py`
- `src/cloudscope/views/footer_view.py`
- `src/cloudscope/views/left_toolbar_view.py`
- `src/cloudscope/views/velocity_analysis_view.py`
- `src/cloudscope/views/velocity_pool_view.py`
- `tests/cloudscope/test_app_config_splitters.py`
- `tests/cloudscope/test_blinded_display.py`
- `tests/cloudscope/test_file_list_tree_view.py`
- `tests/cloudscope/test_footer_view.py`
- `tests/cloudscope/test_left_toolbar_view.py`
- `tests/cloudscope/test_velocity_pool_view.py`

## Summary of implementation

- Added persisted blinded-analysis state to `AppConfig` with typed `get_blinded()` and `set_blinded()` helpers.
- Added `BlindedAnalysisModeChanged` in `cloudscope.events.app_config`.
- Added CloudScope-only display masking helpers in `cloudscope.blinded_display` for file labels, file-list/tree rows, pool DataFrames, and pool selection maps.
- Added a Config-panel checkbox that saves blinded mode immediately and publishes the mode-change event.
- Wired view-level blinded state through `BaseView`, Home page, and Pool page.
- Masked file-list/tree visible file identity, parent/grandparent folders, and experimental metadata while preserving real row ids and selection paths.
- Masked footer and analysis-panel selection labels using stable `File N` labels.
- Disabled the Experiment Metadata toolbar button while blinded and closed the panel when blinded mode is turned on.
- Kept load/save controls, recent paths, native pickers, save paths, and App Info/logs unblinded.
- Kept backend analysis-pool caches unblinded and masked only the DataFrames handed to `NicePool`; pool row selections translate through private display-to-real maps.
- Masked batch-analysis dialog preview/result file labels while preserving real `file_ids` in submitted batch intents.

## Tests added or modified

- Added helper tests for label maps, file-tree masking, pool DataFrame masking, and real-selection maps.
- Added a regression test for blinded pool masking with nullable numeric metadata columns.
- Added config persistence tests for blinded mode.
- Added footer blinded label test.
- Added file-list tree blinded refresh test.
- Added left-toolbar metadata disable/close tests.
- Added velocity-pool masked DataFrame and row-selection mapping test.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_blinded_display.py tests/cloudscope/test_app_config_splitters.py tests/cloudscope/test_footer_view.py tests/cloudscope/test_left_toolbar_view.py tests/cloudscope/test_velocity_pool_view.py tests/cloudscope/test_file_list_tree_view.py tests/cloudscope/test_app_config_view.py
uv run pytest tests/cloudscope
uv run pytest tests/cloudscope/test_pool_page.py::test_pool_page_uses_shared_runtime
uv run pytest tests/cloudscope
uv run pytest tests/cloudscope/test_blinded_display.py tests/cloudscope/test_velocity_pool_view.py
```

## Test results

- Focused tests: 67 passed.
- First broad `tests/cloudscope` run: 761 passed, 1 failed. The failure was `tests/cloudscope/test_pool_page.py::test_pool_page_uses_shared_runtime` because the page used a post-construction `set_blinded_provider()` call that the test double did not implement.
- Targeted rerun after constructor wiring fix: 1 passed.
- Final broad `tests/cloudscope` run: 762 passed, 1 existing collection warning in `tests/cloudscope/test_base_view.py`.
- Follow-up pool dtype regression tests: 21 passed.

## Concerns or follow-ups

- This is bias-reduction display masking, not a security boundary. Real paths remain in backend state, logs, load/save controls, pickers, and internal selection events by design.
- Pool grouping columns such as parent, grandparent, condition, and genotype collapse to the fixed `Blinded` display value in blinded mode. This matches the agreed v1 behavior.
- Pool display columns that receive blinded string labels are converted to object dtype before masking so nullable numeric metadata columns such as `depth` and `branch_order` do not reject the display value.
