"""Reusable batch-analysis dialog with preview and live results."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from nicegui import ui

from acqstore.acq_image.analysis.batch.preview import BatchPreviewRow
from acqstore.acq_image.analysis.batch.roi_mode import RoiBatchMode
from acqstore.acq_image.analysis.batch.types import BatchFileOutcome, BatchFileResult
from cloudscope.event_bus import EventBus, EventSubscription
from cloudscope.events.analysis import (
    BatchAnalysisCompleted,
    BatchFileAnalysisCompleted,
    CancelTaskIntent,
    TaskKind,
    TaskProgressChanged,
)


@dataclass(frozen=True, slots=True)
class BatchAnalysisDialogResult:
    """User-confirmed batch-analysis options.

    Args:
        file_ids: Ordered file identifiers to process.
        roi_mode: ROI selection mode.
        roi_id: Shared ROI id for existing-ROI mode, otherwise None.
    """

    file_ids: tuple[str, ...]
    roi_mode: RoiBatchMode
    roi_id: int | None


class BatchAnalysisDialog:
    """Modal dialog for batch analysis over visible table rows.

    Args:
        event_bus: Page-scoped event bus for progress, results, and cancellation.
        batch_id: Unique id used to correlate batch result events.
        analysis_label: Human-readable analysis label.
        file_ids: Ordered file identifiers captured from the visible, filtered,
            sorted file-table rows.
        channel: Channel index that will be used for every file.
        current_roi_id: Current ROI selection used as preferred existing-ROI default.
        common_roi_ids: Rectangular ROI ids present on every visible file.
        preview_rows_provider: Callback returning preview rows for a mode/ROI.
        on_run: Callback invoked when the user confirms the batch.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        batch_id: str,
        analysis_label: str,
        file_ids: Sequence[str],
        channel: int,
        current_roi_id: int | None,
        common_roi_ids: Sequence[int],
        preview_rows_provider: Callable[[RoiBatchMode, int | None], Sequence[BatchPreviewRow]],
        on_run: Callable[[BatchAnalysisDialogResult], None],
    ) -> None:
        self._event_bus = event_bus
        self._batch_id = str(batch_id)
        self._analysis_label = analysis_label
        self._file_ids = tuple(file_ids)
        self._channel = int(channel)
        self._current_roi_id = current_roi_id
        self._common_roi_ids = tuple(int(roi_id) for roi_id in common_roi_ids)
        self._preview_rows_provider = preview_rows_provider
        self._on_run = on_run
        self._dialog: ui.dialog | None = None
        self._roi_mode_radio: ui.radio | None = None
        self._roi_select: ui.select | None = None
        self._preview_table: ui.table | None = None
        self._progress_column: ui.column | None = None
        self._progress: ui.linear_progress | None = None
        self._progress_caption: ui.label | None = None
        self._done_label: ui.label | None = None
        self._close_button: ui.button | None = None
        self._cancel_button: ui.button | None = None
        self._run_button: ui.button | None = None
        self._subscriptions: list[EventSubscription] = []
        self._running = False

    def open(self) -> None:
        """Build and open the dialog.

        Returns:
            None.
        """
        with ui.dialog() as dialog, ui.card().classes("w-[44rem] max-w-full"):
            self._dialog = dialog
            dialog.props("persistent")
            ui.label(f"Batch analyze {self._analysis_label}").classes("text-lg font-semibold")
            ui.label(
                f"This will analyze {len(self._file_ids)} visible/filtered file-table rows "
                f"using channel={self._channel}."
            ).classes("text-sm")
            self._roi_mode_radio = ui.radio(
                {
                    RoiBatchMode.ANALYZE_EXISTING_ROI.value: "Analyze existing ROI",
                    RoiBatchMode.ADD_NEW_ROI.value: "Add new ROI per file",
                },
                value=RoiBatchMode.ANALYZE_EXISTING_ROI.value,
                on_change=lambda _event=None: self._on_roi_inputs_changed(),
            ).props("dense")
            default_roi = self._default_existing_roi_id()
            self._roi_select = ui.select(
                options={roi_id: f"ROI {roi_id}" for roi_id in self._common_roi_ids},
                value=default_roi,
                label="Existing ROI present in every visible file",
                on_change=lambda _event=None: self._on_roi_inputs_changed(),
            ).classes("w-full")
            self._preview_table = ui.table(
                columns=[
                    {"name": "file", "label": "File", "field": "file"},
                    {"name": "outcome", "label": "Outcome", "field": "outcome"},
                    {"name": "message", "label": "Message", "field": "message"},
                ],
                rows=[],
                row_key="file",
            ).classes("w-full text-xs")
            with ui.column().classes("w-full gap-1") as progress_column:
                self._progress_column = progress_column
                self._progress = ui.linear_progress(value=0.0).classes("w-full")
                self._progress_caption = ui.label("").classes("text-xs opacity-70")
                progress_column.visible = False
            self._done_label = ui.label("").classes("text-sm font-medium")
            self._done_label.visible = False
            with ui.row().classes("w-full justify-end gap-2"):
                self._close_button = ui.button("Close", on_click=self._close_clicked).props("flat")
                self._cancel_button = ui.button("Cancel run", on_click=self._cancel_clicked).props(
                    "outline color=negative"
                )
                self._cancel_button.visible = False
                self._run_button = ui.button("Run batch", on_click=self._run_clicked)
        self._subscribe()
        self._refresh_preview_rows()
        self._sync_roi_controls()
        dialog.open()

    def dispose(self) -> None:
        """Unsubscribe, close, and delete the dialog.

        Returns:
            None.
        """
        for subscription in tuple(self._subscriptions):
            subscription.unsubscribe()
        self._subscriptions.clear()
        dialog = self._dialog
        self._dialog = None
        if dialog is not None:
            dialog.close()
            dialog.delete()

    def _run_clicked(self) -> None:
        """Invoke the confirmation callback and enter running state.

        Returns:
            None.
        """
        roi_mode = self._current_roi_mode()
        roi_id = self._current_roi_id_for_mode(roi_mode)
        if roi_mode is RoiBatchMode.ANALYZE_EXISTING_ROI and roi_id is None:
            ui.notify("Choose an ROI that is present in every visible file.", type="warning")
            return
        self._set_running_chrome()
        self._on_run(
            BatchAnalysisDialogResult(
                file_ids=self._file_ids,
                roi_mode=roi_mode,
                roi_id=roi_id,
            )
        )

    def _close_clicked(self) -> None:
        """Close the dialog when no batch is running."""
        if self._running:
            return
        self.dispose()

    def _cancel_clicked(self) -> None:
        """Request cancellation of the active batch task."""
        self._event_bus.publish(CancelTaskIntent(task_kind=TaskKind.BATCH_ANALYSIS))

    def _subscribe(self) -> None:
        """Subscribe to batch task/result events."""
        self._subscriptions.append(
            self._event_bus.subscribe(BatchFileAnalysisCompleted, self._on_batch_file_completed)
        )
        self._subscriptions.append(
            self._event_bus.subscribe(BatchAnalysisCompleted, self._on_batch_completed)
        )
        self._subscriptions.append(
            self._event_bus.subscribe(TaskProgressChanged, self._on_task_progress)
        )

    def _on_roi_inputs_changed(self) -> None:
        """Refresh ROI control state and preview rows after ROI input changes."""
        self._sync_roi_controls()
        self._refresh_preview_rows()

    def _sync_roi_controls(self) -> None:
        """Enable or disable ROI select based on mode and running state."""
        if self._roi_select is None:
            return
        existing_mode = self._current_roi_mode() is RoiBatchMode.ANALYZE_EXISTING_ROI
        self._roi_select.enabled = existing_mode and not self._running
        self._roi_select.update()

    def _refresh_preview_rows(self) -> None:
        """Refresh preview table from the current ROI controls."""
        if self._preview_table is None or self._running:
            return
        roi_mode = self._current_roi_mode()
        roi_id = self._current_roi_id_for_mode(roi_mode)
        rows = self._preview_rows_provider(roi_mode, roi_id)
        self._preview_table.rows = [self._row_from_preview(row) for row in rows]
        self._preview_table.update()

    def _set_running_chrome(self) -> None:
        """Disable idle controls and show progress controls."""
        self._running = True
        if self._roi_mode_radio is not None:
            self._roi_mode_radio.disable()
        if self._roi_select is not None:
            self._roi_select.disable()
        if self._run_button is not None:
            self._run_button.disable()
        if self._close_button is not None:
            self._close_button.disable()
        if self._cancel_button is not None:
            self._cancel_button.visible = True
        if self._progress_column is not None:
            self._progress_column.visible = True
        if self._progress is not None:
            self._progress.value = 0.0
        if self._progress_caption is not None:
            self._progress_caption.text = "Starting batch"

    def _set_done_chrome(self, *, success: bool, message: str) -> None:
        """Show terminal batch state."""
        self._running = False
        if self._cancel_button is not None:
            self._cancel_button.visible = False
        if self._close_button is not None:
            self._close_button.enable()
        if self._done_label is not None:
            self._done_label.visible = True
            self._done_label.text = "Done." if success else message

    def _on_task_progress(self, event: TaskProgressChanged) -> None:
        """Update progress controls from batch progress events."""
        if event.task_kind is not TaskKind.BATCH_ANALYSIS:
            return
        if self._progress is not None:
            denom = 1 if event.total <= 0 else event.total
            self._progress.value = min(1.0, max(0.0, event.current / denom))
        if self._progress_caption is not None:
            self._progress_caption.text = event.message

    def _on_batch_file_completed(self, event: BatchFileAnalysisCompleted) -> None:
        """Apply one per-file result row."""
        if event.batch_id != self._batch_id or self._preview_table is None:
            return
        self._upsert_table_row(self._row_from_result(event.result))

    def _on_batch_completed(self, event: BatchAnalysisCompleted) -> None:
        """Apply final batch result rows and terminal state."""
        if event.batch_id != self._batch_id:
            return
        if self._preview_table is not None:
            self._preview_table.rows = [self._row_from_result(result) for result in event.results]
            self._preview_table.update()
        self._set_done_chrome(success=event.success, message=event.message)

    def _upsert_table_row(self, row: dict[str, str]) -> None:
        """Replace or append a table row by file label."""
        if self._preview_table is None:
            return
        rows = list(self._preview_table.rows)
        key = row["file"]
        for index, existing in enumerate(rows):
            if existing.get("file") == key:
                rows[index] = row
                break
        else:
            rows.append(row)
        self._preview_table.rows = rows
        self._preview_table.update()

    def _current_roi_mode(self) -> RoiBatchMode:
        """Return the currently selected ROI mode."""
        if self._roi_mode_radio is None:
            return RoiBatchMode.ANALYZE_EXISTING_ROI
        return RoiBatchMode(self._roi_mode_radio.value)

    def _current_roi_id_for_mode(self, roi_mode: RoiBatchMode) -> int | None:
        """Return the current ROI id, or None for add-new mode."""
        if roi_mode is RoiBatchMode.ADD_NEW_ROI:
            return None
        if self._roi_select is None or self._roi_select.value is None:
            return None
        return int(self._roi_select.value)

    def _default_existing_roi_id(self) -> int | None:
        """Return current ROI if common, otherwise the first common ROI."""
        if self._current_roi_id in self._common_roi_ids:
            return self._current_roi_id
        if not self._common_roi_ids:
            return None
        return self._common_roi_ids[0]

    def _row_from_preview(self, row: BatchPreviewRow) -> dict[str, str]:
        """Map a preview row to a table row."""
        return {
            "file": row.file_name,
            "outcome": row.outcome.value,
            "message": row.message,
        }

    def _row_from_result(self, result: BatchFileResult) -> dict[str, str]:
        """Map a final/per-file result to a table row."""
        return {
            "file": Path(result.file_path).name,
            "outcome": self._outcome_label(result.outcome),
            "message": "" if result.outcome is BatchFileOutcome.OK else result.message,
        }

    def _outcome_label(self, outcome: BatchFileOutcome) -> str:
        """Return compact display text for a runtime outcome."""
        if outcome is BatchFileOutcome.OK:
            return "ok"
        if outcome is BatchFileOutcome.SKIPPED_MISSING_ROI:
            return "skipped missing ROI"
        if outcome is BatchFileOutcome.SKIPPED_CONFLICT:
            return "skipped conflict"
        return outcome.value
