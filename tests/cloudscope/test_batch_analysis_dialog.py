"""Tests for batch-analysis dialog state and event handling."""

from __future__ import annotations

from acqstore.acq_image.analysis.batch.preview import BatchPreviewOutcome, BatchPreviewRow
from acqstore.acq_image.analysis.batch.roi_mode import RoiBatchMode
from acqstore.acq_image.analysis.batch.types import BatchFileOutcome, BatchFileResult
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    AnalysisKind,
    BatchAnalysisCompleted,
    BatchFileAnalysisCompleted,
    CancelTaskIntent,
    TaskKind,
)
from cloudscope.views.dialogs.batch_analysis_dialog import BatchAnalysisDialog, BatchAnalysisDialogResult


class _Control:
    """Tiny UI control fake for dialog unit tests."""

    def __init__(self, value=None) -> None:
        """Create fake control."""
        self.value = value
        self.text = ""
        self.visible = True
        self.enabled = True
        self.rows = []
        self.updated = 0

    def disable(self) -> None:
        """Mark disabled."""
        self.enabled = False

    def enable(self) -> None:
        """Mark enabled."""
        self.enabled = True

    def update(self) -> None:
        """Record an update."""
        self.updated += 1


def _dialog(bus: EventBus | None = None) -> tuple[BatchAnalysisDialog, list[BatchAnalysisDialogResult]]:
    """Return a dialog with a captured run callback."""
    results: list[BatchAnalysisDialogResult] = []

    def _preview_rows(roi_mode: RoiBatchMode, roi_id: int | None):
        return [
            BatchPreviewRow(
                file_id="/tmp/a.oir",
                file_name="a.oir",
                analysis_name="diameter",
                channel=0,
                roi_mode=roi_mode,
                roi_id=roi_id,
                outcome=BatchPreviewOutcome.PENDING,
                message="will run",
            )
        ]

    dialog = BatchAnalysisDialog(
        event_bus=bus or EventBus(),
        batch_id="batch-1",
        analysis_label="diameter",
        file_ids=("/tmp/a.oir",),
        channel=0,
        current_roi_id=1,
        common_roi_ids=(1, 2),
        preview_rows_provider=_preview_rows,
        on_run=results.append,
    )
    return dialog, results


def _install_idle_controls(dialog: BatchAnalysisDialog) -> None:
    """Install fake controls needed by run-state methods."""
    dialog._roi_mode_radio = _Control(RoiBatchMode.ANALYZE_EXISTING_ROI.value)  # type: ignore[assignment]
    dialog._roi_select = _Control(1)  # type: ignore[assignment]
    dialog._run_button = _Control()  # type: ignore[assignment]
    dialog._close_button = _Control()  # type: ignore[assignment]
    dialog._cancel_button = _Control()  # type: ignore[assignment]
    dialog._progress_column = _Control()  # type: ignore[assignment]
    dialog._progress = _Control(0.0)  # type: ignore[assignment]
    dialog._progress_caption = _Control()  # type: ignore[assignment]


def test_run_clicked_emits_existing_roi_result() -> None:
    """Run click should pass selected existing ROI options to callback."""
    dialog, results = _dialog()
    _install_idle_controls(dialog)

    dialog._run_clicked()

    assert results == [
        BatchAnalysisDialogResult(
            file_ids=("/tmp/a.oir",),
            roi_mode=RoiBatchMode.ANALYZE_EXISTING_ROI,
            roi_id=1,
        )
    ]
    assert dialog._run_button.enabled is False
    assert dialog._cancel_button.visible is True


def test_run_clicked_emits_add_new_roi_result() -> None:
    """Add-new mode should pass roi_id=None."""
    dialog, results = _dialog()
    _install_idle_controls(dialog)
    dialog._roi_mode_radio.value = RoiBatchMode.ADD_NEW_ROI.value

    dialog._run_clicked()

    assert results[0].roi_mode is RoiBatchMode.ADD_NEW_ROI
    assert results[0].roi_id is None


def test_cancel_clicked_publishes_batch_cancel_intent() -> None:
    """Cancel button should request cancellation for batch-analysis tasks."""
    bus = EventBus()
    published: list[CancelTaskIntent] = []
    bus.subscribe(CancelTaskIntent, published.append)
    dialog, _results = _dialog(bus)

    dialog._cancel_clicked()

    assert published == [CancelTaskIntent(task_kind=TaskKind.BATCH_ANALYSIS)]


def test_batch_file_completed_updates_matching_batch_row() -> None:
    """Per-file results should update only their matching batch dialog."""
    dialog, _results = _dialog()
    dialog._preview_table = _Control()  # type: ignore[assignment]
    dialog._preview_table.rows = [{"file": "a.oir", "outcome": "pending", "message": "will run"}]
    result = BatchFileResult(
        file_path="/tmp/a.oir",
        analysis_name="diameter",
        channel=0,
        roi_id=1,
        outcome=BatchFileOutcome.OK,
        message="ok",
    )

    dialog._on_batch_file_completed(
        BatchFileAnalysisCompleted(
            batch_id="other",
            analysis_kind=AnalysisKind.DIAMETER,
            file_id="/tmp/a.oir",
            result=result,
        )
    )
    assert dialog._preview_table.rows[0]["outcome"] == "pending"

    dialog._on_batch_file_completed(
        BatchFileAnalysisCompleted(
            batch_id="batch-1",
            analysis_kind=AnalysisKind.DIAMETER,
            file_id="/tmp/a.oir",
            result=result,
        )
    )

    assert dialog._preview_table.rows[0]["outcome"] == "ok"


def test_batch_completed_sets_done_state_and_final_rows() -> None:
    """Final batch completion should set terminal UI state."""
    dialog, _results = _dialog()
    dialog._preview_table = _Control()  # type: ignore[assignment]
    dialog._done_label = _Control()  # type: ignore[assignment]
    dialog._close_button = _Control()  # type: ignore[assignment]
    dialog._cancel_button = _Control()  # type: ignore[assignment]
    result = BatchFileResult(
        file_path="/tmp/a.oir",
        analysis_name="diameter",
        channel=0,
        roi_id=1,
        outcome=BatchFileOutcome.OK,
        message="ok",
    )

    dialog._on_batch_completed(
        BatchAnalysisCompleted(
            batch_id="batch-1",
            analysis_kind=AnalysisKind.DIAMETER,
            file_ids=("/tmp/a.oir",),
            channel=0,
            roi_mode=RoiBatchMode.ANALYZE_EXISTING_ROI,
            roi_id=1,
            results=(result,),
            success=True,
            message="done",
        )
    )

    assert dialog._preview_table.rows == [{"file": "a.oir", "outcome": "ok", "message": ""}]
    assert dialog._done_label.visible is True
    assert dialog._done_label.text == "Done."
    assert dialog._close_button.enabled is True
    assert dialog._cancel_button.visible is False
