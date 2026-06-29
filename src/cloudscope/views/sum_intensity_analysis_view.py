"""Left-panel view for sum-intensity analysis controls."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from acqstore.acq_image.analysis.model import (
    AnalysisKey,
    DetectionParamCategory,
    DetectionParamSchema,
    DetectionValueType,
)
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_analysis import (
    SumIntensityAnalysis,
)
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_presets import (
    SumIntensityPresetName,
)
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind, RunAnalysisIntent
from cloudscope.events.roi import RoiChanged
from cloudscope.state import PrimarySelection
from cloudscope.views.analysis_summary_display import build_analysis_summary_expansion_for_analysis
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId

_DETECTION_PARAM_COLUMNS = 2


def _category_heading_if_changed(
    previous_category: DetectionParamCategory | None,
    field: DetectionParamSchema,
) -> str | None:
    """Return a category section label when ``field`` starts a new visible group.

    Args:
        previous_category: Category of the last rendered visible field.
        field: Current schema entry.

    Returns:
        Category display string, or ``None`` when no heading is needed.
    """
    if not field.visible or field.category is None:
        return None
    if field.category is previous_category:
        return None
    return field.category.value


def _coerce_detection_param_value(field: DetectionParamSchema, value: object) -> object:
    """Coerce a raw GUI control value to the schema field type.

    NiceGUI ``ui.number`` returns floats even for integer fields. AcqStore
    validation requires true ``int`` values for ``DetectionValueType.INT``.

    Args:
        field: Detection parameter schema entry.
        value: Raw value from a control.

    Returns:
        Value coerced to the schema type when applicable.
    """
    if value is None:
        return value
    match field.value_type:
        case DetectionValueType.INT:
            if isinstance(value, bool):
                raise TypeError(f"{field.name!r} must be int, got: bool")
            return int(value)
        case DetectionValueType.FLOAT:
            if isinstance(value, bool):
                raise TypeError(f"{field.name!r} must be float or int, got: bool")
            return float(value)
        case DetectionValueType.BOOL:
            return bool(value)
        case DetectionValueType.STR:
            return str(value)
        case _:
            return value


def _field_visible_for_current_params(
    field: DetectionParamSchema,
    current_params: dict[str, object],
) -> bool:
    """Return whether a schema field applies to the current parameter choices.

    Args:
        field: Detection parameter schema entry.
        current_params: Current parameter values keyed by schema field name.

    Returns:
        True when ``field`` should be visible for the current controls.
    """
    if field.methods is None:
        return True
    active_values = {str(value) for value in current_params.values() if value is not None}
    return any(str(method) in active_values for method in field.methods)


class SumIntensityAnalysisView(BaseView):
    """Display sum-intensity controls and publish single-analysis intents.

    This view is intentionally limited to one selected file, channel, and ROI.
    Batch analysis and plotting are separate tickets. Scientific defaults,
    presets, validation, and summaries all come from AcqStore.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional page/controller state object.
        initially_visible: Whether this view starts visible.
    """

    view_id = ViewId.SUM_INTENSITY_ANALYSIS

    def __init__(
        self,
        event_bus: EventBus,
        app_state: Any | None = None,
        *,
        initially_visible: bool = False,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._preset_control: ui.select | None = None
        self._params_container: ui.column | None = None
        self._results_container: ui.column | None = None
        self._run_button: ui.button | None = None
        self._param_controls: dict[str, Any] = {}
        self._schema_by_name: dict[str, DetectionParamSchema] = {}

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the sum-intensity analysis panel.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        # Quasar q-card flex-wrap defaults can float later children (results, run
        # button) into a second column; flex-nowrap keeps the diameter-style stack.
        card_classes = "w-full h-full min-h-0 flex flex-col flex-nowrap"
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
        """Subscribe to analysis and ROI events while visible.

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
        """Refresh results when sum-intensity analysis finishes.

        Args:
            event: Analysis completion event.

        Returns:
            None.
        """
        if event.analysis_kind is not AnalysisKind.SUM_INTENSITY:
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
        ui.label("Sum intensity analysis").classes("text-lg font-semibold shrink-0")
        self.build_selection_label()
        self._build_preset_control()
        self._params_container = ui.column().classes("w-full gap-2 min-h-0 flex-1 overflow-y-auto pr-1")
        self._build_param_controls(self._preset_params(SumIntensityPresetName.MEDIUM.value))
        self._results_container = ui.column().classes("w-full gap-2 shrink-0")
        self._build_results_controls()
        with ui.row().classes("w-full gap-2 shrink-0 flex-nowrap"):
            self._run_button = ui.button(
                "Run Sum Intensity Analysis",
                on_click=self._on_run_clicked,
            ).classes("flex-1 min-w-0")
        self._refresh_run_button()

    def _build_preset_control(self) -> None:
        """Build the detection-preset selector.

        Returns:
            None.
        """
        presets = SumIntensityAnalysis.get_detection_presets()
        options = {preset.name.value: preset.display_name for preset in presets}
        self._preset_control = ui.select(
            label="Detection preset",
            options=options,
            value=SumIntensityPresetName.MEDIUM.value,
            on_change=lambda _event=None: self._on_preset_changed(),
        ).classes("w-full shrink-0")
        descriptions = [f"{preset.display_name}: {preset.description}" for preset in presets]
        self._preset_control.tooltip("\n".join(descriptions))

    def _on_preset_changed(self) -> None:
        """Apply the selected preset to all detection controls.

        Returns:
            None.
        """
        preset_name = self._selected_preset_name()
        self._build_param_controls(self._preset_params(preset_name))

    def _selected_preset_name(self) -> str:
        """Return the selected preset name.

        Returns:
            Preset enum string value.
        """
        if self._preset_control is None or self._preset_control.value is None:
            return SumIntensityPresetName.MEDIUM.value
        return str(self._preset_control.value)

    def _preset_params(self, preset_name: str) -> dict[str, object]:
        """Return copied detection params for one preset.

        Args:
            preset_name: Preset enum string value.

        Returns:
            Complete detection-parameter mapping.
        """
        return SumIntensityAnalysis.get_detection_preset_params(preset_name)

    def _build_param_controls(self, values: dict[str, object]) -> None:
        """Render editable detection parameter controls from analysis schema.

        Args:
            values: Initial values keyed by detection parameter name.

        Returns:
            None.
        """
        if self._params_container is None:
            return
        self._params_container.clear()
        self._param_controls.clear()
        self._schema_by_name.clear()
        with self._params_container:
            current_category: DetectionParamCategory | None = None
            category_grid: ui.grid | None = None
            for field in SumIntensityAnalysis.get_detection_schema():
                self._schema_by_name[field.name] = field
                if not field.visible:
                    continue
                heading = _category_heading_if_changed(current_category, field)
                if heading is not None:
                    ui.label(heading).classes("text-base font-semibold opacity-70")
                    with ui.column().classes("w-full pl-5"):
                        category_grid = ui.grid(columns=_DETECTION_PARAM_COLUMNS).classes("w-full gap-2")
                    current_category = field.category
                if category_grid is None:
                    continue
                with category_grid:
                    with ui.column().classes("gap-0 min-w-0 w-full"):
                        label = field.display_name
                        if field.unit:
                            label = f"{label} ({field.unit})"
                        choices = field.choices
                        value = values.get(field.name, field.default)
                        if choices is not None:
                            control = ui.select(
                                label=label, options=list(choices), value=value
                            ).classes("w-full")
                            control.on_value_change(
                                lambda _event=None: self._refresh_param_visibility()
                            )
                        elif field.value_type.value == "bool":
                            control = ui.checkbox(text=label, value=bool(value))
                        elif field.value_type is DetectionValueType.INT:
                            control = ui.number(
                                label=label,
                                value=int(value),
                                precision=0,
                            ).classes("w-full")
                        elif field.value_type is DetectionValueType.FLOAT:
                            control = ui.number(label=label, value=value).classes("w-full")
                        else:
                            control = ui.input(
                                label=label, value=str(value if value is not None else "")
                            ).classes("w-full")
                        if not field.editable:
                            control.props("readonly")
                        if field.description:
                            control.tooltip(str(field.description))
                        self._param_controls[field.name] = control
            self._refresh_param_visibility()

    def _refresh_param_visibility(self) -> None:
        """Show or hide controls based on the current schema method filters.

        Returns:
            None.
        """
        params = self._current_raw_control_values()
        for name, control in self._param_controls.items():
            field = self._schema_by_name.get(name)
            if field is None:
                continue
            control.visible = _field_visible_for_current_params(field, params)
            control.update()

    def _current_raw_control_values(self) -> dict[str, object]:
        """Return raw values from all current controls without validation.

        Returns:
            Parameter values keyed by control name.
        """
        return {name: control.value for name, control in self._param_controls.items()}

    def _build_results_controls(self) -> None:
        """Render a compact summary of existing sum-intensity results.

        Returns:
            None.
        """
        if self._results_container is None:
            return
        self._results_container.clear()
        analysis = self._selected_analysis()
        with self._results_container:
            if analysis is None:
                if self.get_selected_acq_image() is None:
                    ui.label("No AcqImage selected.").classes("text-xs opacity-70")
                elif self.current_selection.channel is None or self.current_selection.roi_id is None:
                    ui.label("Select a channel and ROI to inspect results.").classes("text-xs opacity-70")
                else:
                    ui.label("No sum-intensity result for this channel/ROI.").classes("text-xs opacity-70")
                return
            build_analysis_summary_expansion_for_analysis(analysis)

    def _current_detection_params(self) -> dict[str, object]:
        """Return current detection parameter values from visible controls.

        Returns:
            Detection parameter mapping.

        Raises:
            KeyError: If an unknown detection parameter is present.
            TypeError: If a value does not match the schema type.
            ValueError: If an enum value is not allowed.
        """
        params = self._preset_params(self._selected_preset_name())
        for name, control in self._param_controls.items():
            if not control.visible:
                continue
            field = self._schema_by_name[name]
            params[name] = _coerce_detection_param_value(field, control.value)
        SumIntensityAnalysis.validate_detection_params(params)
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
                analysis_kind=AnalysisKind.SUM_INTENSITY,
                selection=selection,
                detection_params=detection_params,
            )
        )

    def _refresh_selection_dependent_ui(self) -> None:
        """Refresh UI that depends on the current selection.

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
        if self._run_button is None:
            return
        self._run_button.enabled = self.has_valid_primary_selection()
        self._run_button.update()

    def _selected_analysis(self) -> Any | None:
        """Return the sum-intensity analysis for the current selection.

        Returns:
            Matching analysis instance, or ``None`` when unavailable.
        """
        acq_image = self.get_selected_acq_image()
        selection = self.current_selection
        if acq_image is None or selection.channel is None or selection.roi_id is None:
            return None
        key = AnalysisKey(
            analysis_name=AnalysisKind.SUM_INTENSITY.value,
            channel=int(selection.channel),
            roi_id=int(selection.roi_id),
        )
        return acq_image.analysis_set.get(key)
