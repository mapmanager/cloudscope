"""Left-panel view for Radon velocity analysis controls."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from cloudscope.event_bus import EventBus
from cloudscope.events import (
    AnalysisKind,
    AppBusyChanged,
    CancelTaskIntent,
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
    RunAnalysisIntent,
    TaskKind,
)
from cloudscope.state import PrimarySelection
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
    """Display Radon velocity controls and publish analysis intents.

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
        self._run_button: ui.button | None = None
        self._cancel_button: ui.button | None = None
        self._param_controls: dict[str, Any] = {}
        self._current_task_id: str | None = None

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

    def handle_app_busy_changed(self, event: AppBusyChanged) -> None:
        """Customize busy behavior so the Cancel button remains usable.

        Args:
            event: App busy state event.

        Returns:
            None.
        """
        is_analysis_busy = event.is_busy and event.task_kind is TaskKind.ANALYSIS
        self._current_task_id = event.task_id if is_analysis_busy else None

        if self._run_button is not None:
            self._run_button.enabled = not event.is_busy
            self._run_button.update()
        if self._cancel_button is not None:
            self._cancel_button.visible = is_analysis_busy
            self._cancel_button.enabled = is_analysis_busy
            self._cancel_button.update()

    def _build_content(self) -> None:
        """Build static panel content.

        Returns:
            None.
        """
        ui.label("Velocity analysis").classes("text-lg font-semibold")
        self._selection_label = ui.label("No file selected").classes("text-sm opacity-70")
        self._params_container = ui.column().classes("w-full gap-2")
        self._build_param_controls()
        self._run_button = ui.button("Run Analysis", on_click=self._on_run_clicked).classes("w-full")
        self._cancel_button = ui.button("Cancel Analysis", on_click=self._on_cancel_clicked).props("outline color=negative").classes("w-full")
        self._cancel_button.visible = False

    def _build_param_controls(self) -> None:
        """Render editable detection parameter controls from analysis schema.

        Returns:
            None.
        """
        if self._params_container is None:
            return
        self._params_container.clear()
        self._param_controls.clear()
        with self._params_container:
            cls = _load_radon_velocity_analysis_class()
            if cls is None:
                ui.label("Radon velocity analysis plugin is not available.").classes("text-sm text-orange-600")
                return
            ui.label("Detection parameters").classes("text-sm font-medium")
            defaults = cls.get_default_detection_params()
            for field in cls.get_detection_schema():
                if not getattr(field, "visible", True):
                    continue
                label = field.display_name
                if getattr(field, "unit", None):
                    label = f"{label} ({field.unit})"
                choices = getattr(field, "choices", None)
                if choices is not None:
                    control = ui.select(
                        label=label,
                        options=list(choices),
                        value=defaults.get(field.name),
                    ).classes("w-full")
                elif field.value_type.value == "bool":
                    control = ui.checkbox(text=label, value=bool(defaults.get(field.name)))
                elif field.value_type.value in {"int", "float"}:
                    control = ui.number(label=label, value=defaults.get(field.name)).classes("w-full")
                else:
                    control = ui.input(label=label, value=str(defaults.get(field.name, ""))).classes("w-full")
                if not getattr(field, "editable", True):
                    control.props("readonly")
                description = getattr(field, "description", "")
                if description:
                    ui.label(str(description)).classes("text-xs opacity-70")
                self._param_controls[field.name] = control

    def _current_detection_params(self) -> dict[str, object]:
        """Return current detection parameter values from controls.

        Returns:
            Detection parameter mapping.

        Raises:
            RuntimeError: If the Radon analysis plugin is unavailable.
        """
        cls = _load_radon_velocity_analysis_class()
        if cls is None:
            raise RuntimeError("Radon velocity analysis plugin is not available")
        params = cls.get_default_detection_params()
        for name, control in self._param_controls.items():
            params[name] = control.value
        cls.validate_detection_params(params)
        return params

    def _selection_snapshot(self) -> PrimarySelection:
        """Return a copied selection snapshot for an analysis intent.

        Returns:
            Copied primary selection.
        """
        return PrimarySelection(
            file_id=self._file_id,
            channel=self._channel,
            roi_id=self._roi_id,
        )

    def _on_run_clicked(self) -> None:
        """Publish a run-analysis intent for the current selection.

        Returns:
            None.
        """
        selection = self._selection_snapshot()
        if selection.file_id is None or selection.channel is None or selection.roi_id is None:
            ui.notify("Select a file, channel, and ROI before running analysis.", type="warning")
            return
        try:
            detection_params = self._current_detection_params()
        except Exception as exc:
            ui.notify(f"Invalid detection parameters: {exc}", type="negative")
            return
        self.event_bus.publish(
            RunAnalysisIntent(
                analysis_kind=AnalysisKind.RADON_VELOCITY,
                selection=selection,
                detection_params=detection_params,
            )
        )

    def _on_cancel_clicked(self) -> None:
        """Publish a cancel-analysis intent.

        Returns:
            None.
        """
        self.event_bus.publish(
            CancelTaskIntent(
                task_kind=TaskKind.ANALYSIS,
                task_id=self._current_task_id,
            )
        )

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
