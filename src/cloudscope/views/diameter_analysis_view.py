"""Left-panel view for diameter analysis controls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from nicegui import ui

from acqstore.acq_image.analysis.model import AnalysisKey, DetectionParamSchema
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind, RunAnalysisIntent, RunBatchAnalysisIntent
from cloudscope.events.roi import RoiChanged
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.dialogs.batch_analysis_dialog import BatchAnalysisDialog
from cloudscope.views.view_ids import ViewId


def _load_diameter_analysis_class() -> type[Any] | None:
    """Load the AcqStore diameter analysis class.

    Returns:
        ``DiameterAnalysis`` class when available, otherwise None.
    """
    try:
        from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import (
            DiameterAnalysis,
        )
    except Exception:
        return None
    return DiameterAnalysis


def _field_visible_for_method(field: DetectionParamSchema, selected_method: str) -> bool:
    """Return whether a schema field should be shown for the selected method.

    Args:
        field: Detection parameter schema entry.
        selected_method: Active ``diameter_method`` value.

    Returns:
        True when the field applies to the selected method.
    """
    if field.methods is None:
        return True
    return selected_method in field.methods


class DiameterAnalysisView(BaseView):
    """Display diameter controls and publish analysis intents.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional page/controller state object.
        initially_visible: Whether this view starts visible.
        visible_file_ids_provider: Optional async callback returning file ids
            from currently visible, filtered, sorted file-table rows.
    """

    view_id = ViewId.DIAMETER_ANALYSIS

    def __init__(
        self,
        event_bus: EventBus,
        app_state: Any | None = None,
        *,
        initially_visible: bool = False,
        visible_file_ids_provider: Callable[[], Awaitable[list[str]]] | None = None,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._visible_file_ids_provider = visible_file_ids_provider
        self._params_container: ui.column | None = None
        self._results_container: ui.column | None = None
        self._run_button: ui.button | None = None
        self._batch_button: ui.button | None = None
        self._param_controls: dict[str, Any] = {}
        self._schema_by_name: dict[str, DetectionParamSchema] = {}

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the diameter analysis panel.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        card_classes = "w-full h-full min-h-0 flex flex-col"
        if parent is None:
            with ui.card().classes(card_classes) as self.root:
                self._build_content()
        else:
            with parent:
                with ui.card().classes(card_classes) as self.root:
                    self._build_content()
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to analysis completion events while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed))
        self.add_subscription(self.event_bus.subscribe(RoiChanged, self._on_roi_changed))

    def refresh_from_state(self) -> None:
        """Refresh UI from the cached primary selection.

        Returns:
            None.
        """
        self._refresh_selection_dependent_ui()

    def on_primary_selection_changed(self) -> None:
        """Refresh selection-dependent UI after BaseView updates selection.

        Returns:
            None.
        """
        self._refresh_selection_dependent_ui()

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh results when diameter analysis finishes.

        Args:
            event: Analysis completion event.

        Returns:
            None.
        """
        if event.analysis_kind is not AnalysisKind.DIAMETER:
            return
        if event.selection != self.current_selection:
            return
        self._build_results_controls()

    def _on_roi_changed(self, event: RoiChanged) -> None:
        """Refresh controls after ROI mutations.

        Args:
            event: ROI changed state event.

        Returns:
            None.
        """
        if event.selection.file_id != self.current_selection.file_id:
            return
        self._refresh_selection_dependent_ui()

    def _build_content(self) -> None:
        """Build static panel content.

        Returns:
            None.
        """
        ui.label("Diameter analysis").classes("text-lg font-semibold shrink-0")
        self.build_selection_label()
        self._params_container = ui.column().classes(
            "w-full gap-2 min-h-0 flex-1 overflow-y-auto pr-1"
        )
        self._build_param_controls()
        self._results_container = ui.column().classes("w-full gap-2 shrink-0")
        self._build_results_controls()
        self._run_button = ui.button("Run Diameter Analysis", on_click=self._on_run_clicked).classes(
            "w-full shrink-0"
        )
        self._batch_button = ui.button("Batch analyze visible rows", on_click=self._on_batch_clicked).classes(
            "w-full shrink-0"
        )
        self._refresh_run_button()

    def _selected_diameter_method(self) -> str:
        """Return the currently selected diameter detection method.

        Returns:
            Selected ``diameter_method`` value.
        """
        control = self._param_controls.get("diameter_method")
        if control is None:
            return "threshold_width"
        value = control.value
        return str(value) if value is not None else "threshold_width"

    def _refresh_param_visibility(self) -> None:
        """Show or hide parameter controls for the active detection method.

        Returns:
            None.
        """
        selected_method = self._selected_diameter_method()
        for name, control in self._param_controls.items():
            field = self._schema_by_name.get(name)
            if field is None:
                continue
            visible = _field_visible_for_method(field, selected_method)
            control.visible = visible
            control.update()

    def _build_param_controls(self) -> None:
        """Render editable detection parameter controls from analysis schema.

        Returns:
            None.
        """
        if self._params_container is None:
            return
        self._params_container.clear()
        self._param_controls.clear()
        self._schema_by_name.clear()
        with self._params_container:
            cls = _load_diameter_analysis_class()
            if cls is None:
                ui.label("Diameter analysis plugin is not available.").classes("text-sm text-orange-600")
                return
            ui.label("Detection parameters").classes("text-sm font-medium")
            defaults = cls.get_default_detection_params()
            for field in cls.get_detection_schema():
                self._schema_by_name[field.name] = field
                if not field.visible:
                    continue
                label = field.display_name
                if field.unit:
                    label = f"{label} ({field.unit})"
                choices = field.choices
                if choices is not None:
                    control = ui.select(
                        label=label,
                        options=list(choices),
                        value=defaults.get(field.name),
                    ).classes("w-full")
                    if field.name == "diameter_method":
                        control.on_value_change(lambda _event=None: self._refresh_param_visibility())
                elif field.value_type.value == "bool":
                    control = ui.checkbox(text=label, value=bool(defaults.get(field.name)))
                elif field.value_type.value in {"int", "float"}:
                    control = ui.number(label=label, value=defaults.get(field.name)).classes("w-full")
                else:
                    control = ui.input(label=label, value=str(defaults.get(field.name, ""))).classes("w-full")
                if not field.editable:
                    control.props("readonly")
                if field.description:
                    control.tooltip(str(field.description))
                self._param_controls[field.name] = control
            self._refresh_param_visibility()

    def _build_results_controls(self) -> None:
        """Render a compact summary of existing diameter results.

        Returns:
            None.
        """
        if self._results_container is None:
            return
        self._results_container.clear()
        acq_image = self.get_selected_acq_image()
        selection = self.current_selection
        with self._results_container:
            ui.label("Results").classes("text-sm font-medium")
            if acq_image is None:
                ui.label("No AcqImage selected.").classes("text-xs opacity-70")
                return
            if selection.channel is None or selection.roi_id is None:
                ui.label("Select a channel and ROI to inspect results.").classes("text-xs opacity-70")
                return
            key = AnalysisKey(
                analysis_name=AnalysisKind.DIAMETER.value,
                channel=int(selection.channel),
                roi_id=int(selection.roi_id),
            )
            analysis = acq_image.analysis_set.get(key)
            if analysis is None:
                ui.label("No diameter result for this channel/ROI.").classes("text-xs opacity-70")
                return
            summary = analysis.result.summary
            table = analysis.result.table
            ui.label(f"Summary: {summary}").classes("text-xs break-all")
            if table is not None:
                ui.label(f"Rows: {len(table)}").classes("text-xs opacity-70")

    def _current_detection_params(self) -> dict[str, object]:
        """Return current detection parameter values from controls.

        Returns:
            Detection parameter mapping.

        Raises:
            RuntimeError: If the diameter analysis plugin is unavailable.
        """
        cls = _load_diameter_analysis_class()
        if cls is None:
            raise RuntimeError("Diameter analysis plugin is not available")
        params = cls.get_default_detection_params()
        for name, control in self._param_controls.items():
            if not control.visible:
                continue
            params[name] = control.value
        cls.validate_detection_params(params)
        return params

    def _selection_snapshot(self) -> PrimarySelection:
        """Return a copied selection snapshot for an analysis intent.

        Returns:
            Copied primary selection.
        """
        return PrimarySelection(
            file_id=self.current_selection.file_id,
            channel=self.current_selection.channel,
            roi_id=self.current_selection.roi_id,
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
                analysis_kind=AnalysisKind.DIAMETER,
                selection=selection,
                detection_params=detection_params,
            )
        )

    async def _on_batch_clicked(self) -> None:
        """Publish a batch-analysis intent for visible file-table rows.

        Returns:
            None.
        """
        selection = self._selection_snapshot()
        if selection.channel is None or selection.roi_id is None:
            ui.notify("Select a channel and ROI before running batch analysis.", type="warning")
            return
        if self._visible_file_ids_provider is None:
            ui.notify("Visible file-table rows are not available.", type="negative")
            return
        try:
            file_ids = await self._visible_file_ids_provider()
            detection_params = self._current_detection_params()
        except Exception as exc:
            ui.notify(f"Batch analysis could not start: {exc}", type="negative")
            return
        if not file_ids:
            ui.notify("No visible file-table rows to analyze.", type="warning")
            return

        def _run_batch(confirmed_file_ids: tuple[str, ...]) -> None:
            """Publish confirmed batch-analysis intent.

            Args:
                confirmed_file_ids: File ids confirmed by the dialog.

            Returns:
                None.
            """
            self.event_bus.publish(
                RunBatchAnalysisIntent(
                    analysis_kind=AnalysisKind.DIAMETER,
                    file_ids=confirmed_file_ids,
                    channel=int(selection.channel),
                    roi_id=int(selection.roi_id),
                    detection_params=detection_params,
                )
            )

        BatchAnalysisDialog(
            analysis_label="diameter",
            file_ids=file_ids,
            channel=int(selection.channel),
            roi_id=int(selection.roi_id),
            on_run=_run_batch,
        ).open()

    def _refresh_selection_dependent_ui(self) -> None:
        """Refresh all UI that depends on current selection.

        Returns:
            None.
        """
        self.refresh_selection_label()
        self._refresh_run_button()
        self._build_results_controls()

    def _refresh_run_button(self) -> None:
        """Refresh run button state.

        Returns:
            None.
        """
        enabled = self.has_valid_primary_selection()
        if self._run_button is not None:
            self._run_button.enabled = enabled
            self._run_button.update()
        if self._batch_button is not None:
            self._batch_button.enabled = enabled and self._visible_file_ids_provider is not None
            self._batch_button.update()
