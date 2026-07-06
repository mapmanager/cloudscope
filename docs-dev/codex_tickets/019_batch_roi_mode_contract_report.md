# Ticket 019 — Batch ROI mode contract and per-file events

## Summary

Wired `RoiBatchMode` through CloudScope's batch-analysis intent/controller
contract and prepared the runtime for a richer batch dialog. Batch analysis now
uses a dedicated `TaskKind.BATCH_ANALYSIS`, can carry `ADD_NEW_ROI` with
`roi_id=None`, and emits batch-specific per-file and final completion events.

The current dialog UI remains visually simple for this ticket. Existing GUI
behavior is preserved by sending `RoiBatchMode.ANALYZE_EXISTING_ROI` from the
velocity and diameter batch buttons. The expanded modal UI comes in a later
ticket.

## Files changed

- `src/cloudscope/events/analysis.py`
  - Added `TaskKind.BATCH_ANALYSIS`.
  - Added `RoiBatchMode` and `BatchFileResult` imports.
  - Extended `RunBatchAnalysisIntent` with `batch_id`, `roi_mode`, and nullable
    `roi_id`.
  - Added `BatchFileAnalysisCompleted`.
  - Extended `BatchAnalysisCompleted` with `batch_id`, `roi_mode`, nullable
    `roi_id`, and final `results`.
- `src/cloudscope/task_runner.py`
  - Added `TaskRunnerMessageKind.EVENT`.
  - Added `TaskContext.report_event(event)`.
  - `TaskRunner.drain_messages()` now publishes queued worker events on the
    NiceGUI/UI thread.
- `src/cloudscope/views/task_progress_dialog_view.py`
  - Ignores `TaskKind.BATCH_ANALYSIS` progress because the expanded batch dialog
    will own batch progress UX.
- `src/acqstore/acq_image/analysis/batch/types.py`
  - Added `BatchFileOutcome.SKIPPED_CONFLICT`.
- `src/acqstore/acq_image/analysis/batch/radon_velocity_batch_strategy.py`
  - Catches `AnalysisExclusionError` and returns `SKIPPED_CONFLICT`.
- `src/acqstore/acq_image/analysis/batch/diameter_batch_strategy.py`
  - Same conflict handling as Radon velocity.
- `src/cloudscope/controllers/analysis_controller.py`
  - Batch tasks now run as `TaskKind.BATCH_ANALYSIS`.
  - Batch cancellation routes through the requested task kind.
  - Batch validation accepts `roi_mode`, requires `roi_id` only for
    `ANALYZE_EXISTING_ROI`, and rejects non-None `roi_id` for `ADD_NEW_ROI`.
  - Removed preflight primary-analysis conflict blocking for batch runs.
  - `_batch_strategy_for_event()` passes the requested `roi_mode` to AcqStore.
  - `_run_batch_analysis_worker()` returns `list[BatchFileResult]` and emits
    `BatchFileAnalysisCompleted` for each file via `TaskContext.report_event`.
  - `_publish_batch_analysis_completed()` publishes final result payloads and
    sends `AnalysisCompleted` refresh events only for result rows with concrete
    ROI ids.
- `src/cloudscope/views/velocity_analysis_view.py`
  - Current dialog path now supplies `batch_id` and
    `RoiBatchMode.ANALYZE_EXISTING_ROI` to the new intent contract.
- `src/cloudscope/views/diameter_analysis_view.py`
  - Same intent-contract update as velocity.
- Tests updated/added in:
  - `tests/cloudscope/test_analysis_controller.py`
  - `tests/cloudscope/test_task_runner.py`
  - `tests/cloudscope/test_task_progress_dialog_view.py`
  - `tests/acqstore/test_radon_batch.py`
  - `tests/acqstore/test_diameter_batch.py`

## Tests added or modified

- Added TaskRunner coverage for queued worker events published on the UI thread.
- Added TaskProgressDialogView coverage proving batch-analysis progress is
  ignored by the generic task dialog.
- Added AnalysisController coverage for:
  - `ADD_NEW_ROI` batch intents with `roi_id=None`.
  - rejection of `ADD_NEW_ROI` with a shared ROI id.
  - final `BatchAnalysisCompleted` result payloads and per-file refresh events.
  - batch runs using `TaskKind.BATCH_ANALYSIS`.
- Added AcqStore batch-strategy coverage for conflict rows returning
  `SKIPPED_CONFLICT` instead of `FAILED`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_analysis_controller.py \
              tests/cloudscope/test_task_runner.py \
              tests/cloudscope/test_task_progress_dialog_view.py \
              tests/cloudscope/test_velocity_analysis_view.py \
              tests/cloudscope/test_diameter_analysis_view.py \
              tests/acqstore/test_radon_batch.py \
              tests/acqstore/test_diameter_batch.py -q
uv run pytest -q
```

## Test results

Targeted:

```text
69 passed in 1.33s
```

Full suite:

```text
746 passed, 3 warnings in 2.64s
```

The warnings are pre-existing:

- `PytestCollectionWarning` for `TestEvent`.
- Two `RuntimeWarning: All-NaN slice encountered` warnings from raster-service
  tests.

## Concerns or follow-ups

- The current `BatchAnalysisDialog` still only exposes existing-ROI behavior in
  the GUI. The new contract supports `ADD_NEW_ROI`, but the richer UI comes in
  Ticket 021.
- Final `AnalysisCompleted` events are published only for rows with concrete ROI
  ids. This is correct for refreshing successful `ADD_NEW_ROI` rows, but the
  later live-results dialog should use `BatchFileAnalysisCompleted` and
  `BatchAnalysisCompleted` as its source of truth for skipped/failed/cancelled
  rows.
- Conflict handling is now per-file `SKIPPED_CONFLICT`, not a whole-batch
  preflight block.
