"""Home-page footer showing the current file, channel, and ROI selection.

The view subscribes to CloudScope selection state events on the page
``EventBus`` (same bus as ``HomePageController``). It mirrors selection in
local cache like ``PlotlyImagePanel``: a file change resets all three fields;
channel and ROI events patch a single field. Display rules are implemented in
pure helpers so they can be unit-tested without NiceGUI.

**Build order:** At page top level, create ``ui.header`` first, then call
``build()`` here, then the main column — matching KymFlow ``HomePage.render``
(``build_header`` → ``FooterView.render`` → splitter/body). See NiceGUI page
layout (nicegui.io documentation, section page_layout) and Quasar ``q-layout``.
"""

from __future__ import annotations

from pathlib import Path

from nicegui import ui

from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import (
    AppStatusChanged,
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
    TaskProgressChanged,
)

# Shown when there is no file, or when channel / ROI is unset (per product spec).
_FOOTER_PLACEHOLDER = "—"


def footer_display_values(
    file_id: str | None,
    channel: int | None,
    roi_id: int | None,
) -> tuple[str, str, str]:
    """Compute footer strings for file basename, channel, and ROI.

    When ``file_id`` is ``None``, all three values are the placeholder: the
    footer does not show partial selection without a file.

    Args:
        file_id: Current file identifier, or ``None``.
        channel: Current channel index, or ``None``.
        roi_id: Current ROI identifier, or ``None``.

    Returns:
        ``(file, channel, roi)`` display strings (each may be the placeholder).
    """
    if file_id is None:
        return (_FOOTER_PLACEHOLDER, _FOOTER_PLACEHOLDER, _FOOTER_PLACEHOLDER)
    basename = str(Path(file_id).name)
    ch = _FOOTER_PLACEHOLDER if channel is None else str(channel)
    roi = _FOOTER_PLACEHOLDER if roi_id is None else str(roi_id)
    return (basename, ch, roi)


class SelectionFooterView:
    """NiceGUI footer that reflects primary selection state (MVC view).

    Subscribes to ``FileSelectionChanged``, ``ChannelSelectionChanged``, and
    ``RoiSelectionChanged``. The controller remains the single source of truth;
    this view only renders state events.

    Args:
        event_bus: Page-scoped event bus (same instance as ``HomePage``).
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._file_id: str | None = None
        self._channel: int | None = None
        self._roi_id: int | None = None
        self._file_label: ui.label | None = None
        self._channel_label: ui.label | None = None
        self._roi_label: ui.label | None = None
        self._status_label: ui.label | None = None

        self._event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed)
        self._event_bus.subscribe(ChannelSelectionChanged, self._on_channel_selection_changed)
        self._event_bus.subscribe(RoiSelectionChanged, self._on_roi_selection_changed)
        self._event_bus.subscribe(AppStatusChanged, self._on_app_status_changed)
        self._event_bus.subscribe(TaskProgressChanged, self._on_task_progress_changed)

    def build(self) -> None:
        """Create ``ui.footer`` with file, channel, and ROI labels.

        Must run while still at page top-level layout (before nested columns/cards),
        consistent with KymFlow's footer-before-body pattern.

        Labels are created with placeholder text; they update when selection
        events arrive (including after ``HomePageController.load_acq_image_list``).

        Returns:
            None.
        """
        with ui.footer().classes(
            "w-full px-3 py-1 text-xs flex items-center bg-gray-900 text-gray-200"
        ):
            with ui.row().classes("w-full items-center gap-6 min-w-0"):
                self._file_label = ui.label().classes("truncate max-w-[320px]")
                self._channel_label = ui.label().classes("truncate")
                self._roi_label = ui.label().classes("truncate")
                self._status_label = ui.label("Status: —").classes("truncate grow text-right")
        self._refresh_labels()

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        """Sync cache from a file switch (includes default channel and ROI)."""
        self._file_id = event.file_id
        self._channel = event.channel
        self._roi_id = event.roi_id
        self._refresh_labels()

    def _on_channel_selection_changed(self, event: ChannelSelectionChanged) -> None:
        """Update channel text after a narrow channel state event."""
        self._channel = event.channel
        self._refresh_labels()

    def _on_roi_selection_changed(self, event: RoiSelectionChanged) -> None:
        """Update ROI text after a narrow ROI state event."""
        self._roi_id = event.roi_id
        self._refresh_labels()

    def _refresh_labels(self) -> None:
        """Push cached selection into the three labels (no-op if not built yet)."""
        if self._file_label is None or self._channel_label is None or self._roi_label is None:
            return
        file_s, ch_s, roi_s = footer_display_values(self._file_id, self._channel, self._roi_id)
        self._file_label.text = f"File: {file_s}"
        self._channel_label.text = f"Channel: {ch_s}"
        self._roi_label.text = f"ROI: {roi_s}"

    def _on_app_status_changed(self, event: AppStatusChanged) -> None:
        """Render latest app-level status in footer."""
        if self._status_label is None:
            return
        color = {
            'info': 'text-blue-300',
            'warning': 'text-yellow-300',
            'error': 'text-red-300',
        }.get(event.level.value, 'text-gray-200')
        self._status_label.text = f"Status: {event.message}"
        self._status_label.classes(replace=f"truncate grow text-right {color}")

    def _on_task_progress_changed(self, event: TaskProgressChanged) -> None:
        """Render latest task progress in footer (latest event wins)."""
        if self._status_label is None:
            return
        self._status_label.text = f"Status: {event.task_label} - {event.message}"
