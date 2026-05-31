# Ticket 021 — Batch dialog preview and live results

## Summary

Expanded the CloudScope batch-analysis dialog from a simple confirmation prompt
into a persistent modal with ROI-mode selection, common-ROI selection, preview
rows, live per-file result updates, progress display, and cancellation.

Velocity and diameter views now compute read-only AcqStore preview rows before
opening the dialog and publish the new batch-analysis intent contract when the
user starts a run.

## Files changed

- `src/cloudscope/views/dialogs/batch_analysis_dialog.py`
  - Added `BatchAnalysisDialogResult`.
  - Made the dialog persistent.
  - Added ROI mode controls:
    - `Analyze existing ROI`
    - `Add new ROI per file`
  - Added existing-ROI select populated with rectangular ROI ids common to all
    visible files.
  - Added preview/results table.
  - Added progress bar/caption and terminal status label.
  - Added cancel button that publishes
    `CancelTaskIntent(task_kind=TaskKind.BATCH_ANALYSIS)`.
  - Subscribes to `BatchFileAnalysisCompleted`, `BatchAnalysisCompleted`, and
    `TaskProgressChanged`.
  - Applies per-file results live and final result rows at completion.
- `src/cloudscope/views/velocity_analysis_view.py`
  - Resolves visible file ids to loaded AcqImages before opening the dialog.
  - Computes common rectangular ROI ids with
    `roi_intersection_across_acq_images`.
  - Supplies `preview_batch_rows` provider to the dialog.
  - Publishes `RunBatchAnalysisIntent` using the dialog-selected `roi_mode` and
    `roi_id`.
- `src/cloudscope/views/diameter_analysis_view.py`
  - Same dialog preview/result wiring as velocity.
- `tests/cloudscope/test_batch_analysis_dialog.py`
  - New dialog behavior tests.
- `docs/codex_tickets/021_batch_dialog_preview_live_results_report.md`
  - This report.

## Tests added or modified

Added `tests/cloudscope/test_batch_analysis_dialog.py` coverage for:

- Existing-ROI run options passed to the callback.
- Add-new-ROI mode passing `roi_id=None`.
- Batch cancel intent publishing.
- Matching per-file batch result updates.
- Final batch completion rows and done-state UI.

Existing affected tests remained green:

- `tests/cloudscope/test_velocity_analysis_view.py`
- `tests/cloudscope/test_diameter_analysis_view.py`
- `tests/cloudscope/test_analysis_controller.py`
- `tests/acqstore/test_batch_preview.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_batch_analysis_dialog.py \
              tests/cloudscope/test_velocity_analysis_view.py \
              tests/cloudscope/test_diameter_analysis_view.py \
              tests/cloudscope/test_analysis_controller.py \
              tests/acqstore/test_batch_preview.py -q
uv run pytest -q
```

## Test results

Targeted:

```text
62 passed in 0.94s
```

Full suite:

```text
756 passed, 3 warnings in 2.64s
```

The warnings are pre-existing:

- `PytestCollectionWarning` for `TestEvent`.
- Two `RuntimeWarning: All-NaN slice encountered` warnings from raster-service
  tests.

## Concerns or follow-ups

- The batch dialog updates live from `BatchFileAnalysisCompleted`; the generic
  task progress dialog intentionally ignores `TaskKind.BATCH_ANALYSIS`.
- Current view button enablement still depends on an active primary selection,
  so opening the dialog without a selected ROI is not part of this ticket even
  though `ADD_NEW_ROI` execution itself does not require a shared ROI id.
- The dialog currently uses the backend preview helper from the calling analysis
  view. This keeps `BatchAnalysisDialog` reusable and avoids making it own
  `app_state`.
