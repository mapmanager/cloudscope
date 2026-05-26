"""Reusable batch-analysis confirmation dialog."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from nicegui import ui


class BatchAnalysisDialog:
    """Small confirmation dialog for batch analysis over visible table rows.

    Args:
        analysis_label: Human-readable analysis label.
        file_ids: Ordered file identifiers captured from the visible, filtered,
            sorted file-table rows.
        channel: Channel index that will be used for every file.
        roi_id: ROI identifier that will be used for every file.
        on_run: Callback invoked with ``file_ids`` when the user confirms.
    """

    def __init__(
        self,
        *,
        analysis_label: str,
        file_ids: Sequence[str],
        channel: int,
        roi_id: int,
        on_run: Callable[[tuple[str, ...]], None],
    ) -> None:
        self._analysis_label = analysis_label
        self._file_ids = tuple(file_ids)
        self._channel = int(channel)
        self._roi_id = int(roi_id)
        self._on_run = on_run
        self._dialog: ui.dialog | None = None

    def open(self) -> None:
        """Build and open the dialog.

        Returns:
            None.
        """
        with ui.dialog() as dialog, ui.card().classes("w-[32rem] max-w-full"):
            self._dialog = dialog
            ui.label(f"Batch analyze {self._analysis_label}").classes("text-lg font-semibold")
            ui.label(
                f"This will analyze {len(self._file_ids)} visible/filtered file-table rows "
                f"using channel={self._channel}, roi={self._roi_id}."
            ).classes("text-sm")
            with ui.scroll_area().classes("w-full h-40 border rounded p-2"):
                for file_id in self._file_ids[:100]:
                    ui.label(file_id).classes("text-xs font-mono")
                if len(self._file_ids) > 100:
                    ui.label(f"... {len(self._file_ids) - 100} more").classes("text-xs opacity-70")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancel", on_click=dialog.close).props("flat")
                ui.button("Run batch", on_click=self._run_clicked)
        dialog.open()

    def _run_clicked(self) -> None:
        """Invoke the confirmation callback and close the dialog.

        Returns:
            None.
        """
        if self._dialog is not None:
            self._dialog.close()
        self._on_run(self._file_ids)
