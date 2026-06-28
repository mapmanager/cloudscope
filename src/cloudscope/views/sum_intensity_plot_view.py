"""View for plotting selected sum-intensity analysis results."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from acqstore.acq_image.analysis.model import AnalysisKey
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_analysis import (
    SumIntensityAnalysis,
)
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_core import (
    ResultPoints,
    ResultTrace,
    SumIntensityEventPointKey,
    SumIntensityTraceKey,
)
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind
from cloudscope.events.roi import RoiChanged
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.plotly_plot.models import MeasurementChangeEvent
from nicewidgets.plotly_plot.widget import PlotlyPlotWidget


class SumIntensityPlotView(BaseView):
    """Display sum-intensity traces and event overlays for the active selection.

    This CloudScope view owns a reusable :class:`PlotlyPlotWidget` child and is
    intentionally limited to GUI orchestration. All scientific values and
    plot-ready arrays come from the public AcqStore ``SumIntensityAnalysis`` API.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional page/controller state object.
        title: View title.
        initially_visible: Whether this view starts visible.
    """

    view_id = ViewId.SUM_INTENSITY_PLOT
    disable_when_busy = False

    def __init__(
        self,
        event_bus: EventBus,
        app_state: Any | None = None,
        *,
        title: str = "Sum intensity plot",
        initially_visible: bool = True,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self.title = title
        self._plot: PlotlyPlotWidget | None = None
        self._status_label: ui.label | None = None
        self._primary_x_range: tuple[float | None, float | None] = (None, None)
        self._last_measurement_event: MeasurementChangeEvent | None = None

    @property
    def last_measurement_event(self) -> MeasurementChangeEvent | None:
        """Return the last Plotly measurement callback payload seen by this view."""
        return self._last_measurement_event

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the sum-intensity plot view.

        Args:
            parent: Optional NiceGUI parent element.

        Returns:
            Root element for this view.
        """
        if parent is None:
            with ui.column().classes("w-full h-full min-h-0 flex flex-col overflow-hidden flex-1") as self.root:
                self._build_content()
        else:
            with parent:
                with ui.column().classes("w-full h-full min-h-0 flex flex-col overflow-hidden flex-1") as self.root:
                    self._build_content()
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to events that can change displayed sum-intensity results.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed))
        self.add_subscription(self.event_bus.subscribe(RoiChanged, self._on_roi_changed))
        self.add_subscription(self.event_bus.subscribe(PrimaryXRangeChanged, self._on_primary_x_range_changed))

    def refresh_from_state(self) -> None:
        """Refresh the plot from current application state.

        Returns:
            None.
        """
        self._refresh_plot()

    def on_primary_selection_changed(self) -> None:
        """Refresh the plot when the selected file/channel/ROI changes.

        Returns:
            None.
        """
        self._refresh_plot()

    def set_x_axis_limits(self, x_min: float | None, x_max: float | None) -> None:
        """Set Plotly x-axis limits.

        Args:
            x_min: Minimum x-axis value, or ``None`` for automatic scaling.
            x_max: Maximum x-axis value, or ``None`` for automatic scaling.

        Returns:
            None.
        """
        self._primary_x_range = (x_min, x_max)
        self._apply_primary_x_range_to_plot()

    def reset_x_axis_limits(self) -> None:
        """Reset Plotly x-axis limits to automatic scaling.

        Returns:
            None.
        """
        self.set_x_axis_limits(None, None)

    def _build_content(self) -> None:
        """Build static child controls.

        Returns:
            None.
        """
        self._plot = PlotlyPlotWidget(
            title=self.title,
            x_label="Time (s)",
            y_label="Signal",
            on_x_range_changed=self._on_plot_x_range_changed,
            on_measurement_changed=self._on_measurement_changed,
        )
        self._plot.container.classes("w-full h-full min-h-0 flex-1")
        self._status_label = ui.label("No sum-intensity analysis selected").classes("text-xs opacity-70 shrink-0")

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh after matching sum-intensity analysis completion.

        Args:
            event: Analysis completion state event.

        Returns:
            None.
        """
        if event.analysis_kind is not AnalysisKind.SUM_INTENSITY:
            return
        if event.selection.file_id != self.current_selection.file_id:
            return
        if event.selection.channel != self.current_selection.channel:
            return
        if event.selection.roi_id != self.current_selection.roi_id:
            return
        self._refresh_plot()

    def _on_roi_changed(self, event: RoiChanged) -> None:
        """Refresh when ROI changes may affect selected analysis results.

        Args:
            event: ROI changed state event.

        Returns:
            None.
        """
        if event.selection.file_id != self.current_selection.file_id:
            return
        self._refresh_plot()

    def _on_plot_x_range_changed(self, x_min: float | None, x_max: float | None) -> None:
        """Publish user-driven Plotly x-range changes as app-level intent.

        Args:
            x_min: Minimum x-axis value, or ``None`` for automatic scaling.
            x_max: Maximum x-axis value, or ``None`` for automatic scaling.

        Returns:
            None.
        """
        self.event_bus.publish(SetPrimaryXRangeIntent(x_min=x_min, x_max=x_max))

    def _on_primary_x_range_changed(self, event: PrimaryXRangeChanged) -> None:
        """Apply authoritative app-level x-axis range to the child plot.

        Args:
            event: Primary x-range state event.

        Returns:
            None.
        """
        self._primary_x_range = (event.x_min, event.x_max)
        self._apply_primary_x_range_to_plot()

    def _on_measurement_changed(self, event: MeasurementChangeEvent) -> None:
        """Store measurement callbacks for future detection-parameter wiring.

        Ticket 083 only wires the callback boundary. Later tickets can translate
        specific measurement names into CloudScope intents for sum-intensity
        detection-parameter edits.

        Args:
            event: Measurement callback payload from ``PlotlyPlotWidget``.

        Returns:
            None.
        """
        self._last_measurement_event = event

    def _apply_primary_x_range_to_plot(self) -> None:
        """Push cached x-range state into the child Plotly widget.

        Returns:
            None.
        """
        if self._plot is None:
            return
        x_min, x_max = self._primary_x_range
        if x_min is None or x_max is None:
            self._plot.reset_x_axis_limits()
            return
        self._plot.set_x_axis_limits(x_min, x_max)

    def _refresh_plot(self) -> None:
        """Refresh Plotly traces and overlays from selected sum-intensity analysis.

        Returns:
            None.
        """
        if self._plot is None:
            return
        analysis = self._get_selected_sum_intensity_analysis()
        if analysis is None:
            self._clear_plot(self._empty_message())
            return
        try:
            self._plot.clear_traces()
            self._plot.clear_scatters()
            self._add_trace(analysis.get_trace(SumIntensityTraceKey.DF_F_SIGNAL))
            self._add_trace(analysis.get_trace(SumIntensityTraceKey.D_DF_F_SIGNAL))
            self._add_event_points(analysis.get_event_points(SumIntensityEventPointKey.ONSETS))
            self._add_event_points(analysis.get_event_points(SumIntensityEventPointKey.PEAKS))
            self._add_width_traces(analysis.get_width_trace())
        except (KeyError, ValueError) as exc:
            self._clear_plot(f"Sum-intensity plot unavailable: {exc}")
            return
        self._apply_primary_x_range_to_plot()
        if self._status_label is not None:
            self._status_label.text = self._summary_status_text(analysis)

    def _clear_plot(self, message: str) -> None:
        """Clear plot contents and set empty-state text.

        Args:
            message: Human-readable status text.

        Returns:
            None.
        """
        if self._plot is not None:
            self._plot.clear_traces()
            self._plot.clear_scatters()
        if self._status_label is not None:
            self._status_label.text = message

    def _add_trace(self, trace: ResultTrace) -> None:
        """Add one continuous result trace to the child plot.

        Args:
            trace: Public AcqStore result trace.

        Returns:
            None.
        """
        if self._plot is None:
            return
        self._plot.add_trace(name=str(trace.name), x=trace.x, y=trace.y)

    def _add_event_points(self, points: ResultPoints) -> None:
        """Add sparse event markers when the point collection is non-empty.

        Args:
            points: Public AcqStore event points.

        Returns:
            None.
        """
        if self._plot is None or len(points.x) == 0:
            return
        self._plot.plot_scatter(name=str(points.name), x=points.x, y=points.y)

    def _add_width_traces(self, traces: ResultTrace | tuple[ResultTrace, ...]) -> None:
        """Add NaN-separated peak-width segment traces.

        Args:
            traces: One result trace or a tuple of result traces from AcqStore.

        Returns:
            None.
        """
        if isinstance(traces, tuple):
            for trace in traces:
                if len(trace.x) > 0:
                    self._add_trace(trace)
            return
        if len(traces.x) > 0:
            self._add_trace(traces)

    def _get_selected_sum_intensity_analysis(self) -> SumIntensityAnalysis | None:
        """Return sum-intensity analysis for the active file/channel/ROI selection.

        Returns:
            Matching analysis, or ``None`` when unavailable.
        """
        acq_image = self.get_selected_acq_image()
        if acq_image is None:
            return None
        if self.current_selection.channel is None or self.current_selection.roi_id is None:
            return None
        analysis = acq_image.analysis_set.get(
            AnalysisKey(
                SumIntensityAnalysis.analysis_name,
                int(self.current_selection.channel),
                int(self.current_selection.roi_id),
            )
        )
        if not isinstance(analysis, SumIntensityAnalysis):
            return None
        return analysis

    def _summary_status_text(self, analysis: SumIntensityAnalysis) -> str:
        """Return concise status text from backend summary values.

        Args:
            analysis: Selected sum-intensity analysis.

        Returns:
            Human-readable summary status.
        """
        summary = analysis.get_summary_values()
        peak_count = summary.get("num_peaks", 0)
        f0 = summary.get("f0_baseline", None)
        if f0 is None:
            return f"Sum-intensity peaks: {peak_count}"
        try:
            f0_text = f"{float(f0):.4g}"
        except (TypeError, ValueError):
            f0_text = str(f0)
        return f"Sum-intensity peaks: {peak_count}; F0: {f0_text}"

    def _empty_message(self) -> str:
        """Return status text for the current empty plot state.

        Returns:
            Human-readable empty-state message.
        """
        if self.current_selection.file_id is None:
            return "No file selected"
        if self.current_selection.channel is None:
            return "No channel selected"
        if self.current_selection.roi_id is None:
            return "No ROI selected"
        return (
            "No sum-intensity analysis for "
            f"channel={self.current_selection.channel}, roi_id={self.current_selection.roi_id}"
        )
