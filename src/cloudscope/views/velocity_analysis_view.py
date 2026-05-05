"""Left-panel view for Radon velocity analysis controls."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from cloudscope.event_bus import EventBus
from cloudscope.events import ChannelSelectionChanged, FileSelectionChanged, RoiSelectionChanged
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId


def _load_radon_velocity_analysis_class() -> type[Any] | None:
    """Load the optional AcqStore Radon velocity analysis class.

    Returns:
        ``RadonVelocityAnalysis`` class when available, otherwise None.
    """
    try:
        from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import (
            RadonVelocityAnalysis,
        )
    except Exception:
        return None
    return RadonVelocityAnalysis


class VelocityAnalysisView(BaseView):
    """Display Radon velocity detection params and a placeholder run button.

    This pass intentionally does not run analysis. The run button is present so
    the UI shape is ready for the next analysis-intent/controller ticket.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional page/controller state object.
        initially_visible: Whether this view starts visible.
    """

    view_id = ViewId.VELOCITY_ANALYSIS

    def __init__(
        self,
        event_bus: EventBus,
        app_state: Any | None = None,
        *,
        initially_visible: bool = False,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._file_id: str | None = None
        self._channel: int | None = None
        self._roi_id: int | None = None
        self._selection_label: ui.label | None = None
        self._params_container: ui.column | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the velocity analysis panel.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        if parent is None:
            with ui.card().classes("w-full") as self.root:
                self._build_content()
        else:
            with parent:
                with ui.card().classes("w-full") as self.root:
                    self._build_content()
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to selection events while the view is visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed))
        self.add_subscription(self.event_bus.subscribe(ChannelSelectionChanged, self._on_channel_selection_changed))
        self.add_subscription(self.event_bus.subscribe(RoiSelectionChanged, self._on_roi_selection_changed))

    def refresh_from_state(self) -> None:
        """Refresh selection label from current app state.

        Returns:
            None.
        """
        if self.app_state is not None:
            selection = getattr(self.app_state, "selection", None)
            if selection is not None:
                self._file_id = selection.file_id
                self._channel = selection.channel
                self._roi_id = selection.roi_id
        self._refresh_selection_label()

    def _build_content(self) -> None:
        """Build static panel content.

        Returns:
            None.
        """
        ui.label("Velocity analysis").classes("text-lg font-semibold")
        self._selection_label = ui.label("No file selected").classes("text-sm opacity-70")
        self._params_container = ui.column().classes("w-full gap-1")
        self._build_param_summary()
        ui.button("Run Analysis", on_click=self._on_run_clicked).props("outline").classes("w-full")

    def _build_param_summary(self) -> None:
        """Render detection parameter schema/defaults.

        Returns:
            None.
        """
        if self._params_container is None:
            return
        self._params_container.clear()
        with self._params_container:
            cls = _load_radon_velocity_analysis_class()
            if cls is None:
                ui.label("Radon velocity analysis plugin is not available.").classes("text-sm text-orange-600")
                return
            ui.label("Detection parameters").classes("text-sm font-medium")
            for field in cls.get_detection_schema():
                if not getattr(field, "visible", True):
                    continue
                choices = getattr(field, "choices", None)
                suffix = f" choices={tuple(choices)!r}" if choices is not None else ""
                description = getattr(field, "description", "")
                ui.label(
                    f"{field.display_name}: default={field.default!r}{suffix}"
                ).classes("text-xs")
                if description:
                    ui.label(str(description)).classes("text-xs opacity-70")

    def _on_run_clicked(self) -> None:
        """Handle placeholder run-analysis button click.

        Returns:
            None.
        """
        ui.notify("Analysis execution will be wired in the analysis-controller ticket.", type="info")

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        """Update selection cache from file-selection state.

        Args:
            event: File selection state event.

        Returns:
            None.
        """
        self._file_id = event.file_id
        self._channel = event.channel
        self._roi_id = event.roi_id
        self._refresh_selection_label()

    def _on_channel_selection_changed(self, event: ChannelSelectionChanged) -> None:
        """Update selected channel.

        Args:
            event: Channel selection state event.

        Returns:
            None.
        """
        self._channel = event.channel
        self._refresh_selection_label()

    def _on_roi_selection_changed(self, event: RoiSelectionChanged) -> None:
        """Update selected ROI.

        Args:
            event: ROI selection state event.

        Returns:
            None.
        """
        self._roi_id = event.roi_id
        self._refresh_selection_label()

    def _refresh_selection_label(self) -> None:
        """Refresh selection text.

        Returns:
            None.
        """
        if self._selection_label is None:
            return
        if self._file_id is None:
            self._selection_label.text = "No file selected"
            return
        self._selection_label.text = (
            f"file={self._file_id}, channel={self._channel}, roi={self._roi_id}"
        )
