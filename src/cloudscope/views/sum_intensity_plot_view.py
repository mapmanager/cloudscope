"""View for plotting selected sum-intensity analysis results."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import DiameterAnalysis
from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisPlotData
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_analysis import (
    SumIntensityAnalysis,
)
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_core import (
    PeakWidthLevel,
    ResultPoints,
    ResultTrace,
    SumIntensityEventPointKey,
    SumIntensityTraceKey,
)
from cloudscope.app_config import home_stack_layout_margins_profile
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind
from cloudscope.events.roi import RoiChanged
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent, x_ranges_equal
from cloudscope.plot_axis_labels import kymograph_time_x_label
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.plotly_plot.models import (
    MeasurementChangeEvent,
    PlotlyScatterData,
    PlotlySeriesMenuItem,
    PlotlyTraceData,
    PlotlyYAxisSide,
)
from nicewidgets.plotly_plot.widget import PlotlyPlotWidget

_DIAMETER_TRACE_NAME = "Diameter"
_DERIVATIVE_TRACE_NAME = "Derivative of df/f0"
_DERIVATIVE_Y2_LABEL = "d(df/f0)/dt (1/s)"


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
        dark_mode: Initial Plotly layout theme state.
        dark_mode_provider: Optional callable returning the current application
            dark-mode state when the view is shown after being hidden.
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
        dark_mode: bool = False,
        dark_mode_provider: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self.title = title
        self._dark_mode_provider = dark_mode_provider
        self._initial_dark_mode = bool(dark_mode)
        self._plot: PlotlyPlotWidget | None = None
        self._primary_x_range: tuple[float | None, float | None] = (None, None)
        self._plot_originated_x_range = False
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
        self.add_subscription(self.event_bus.subscribe(ThemeChanged, self._on_theme_changed))

    def refresh_from_state(self) -> None:
        """Refresh the plot from current application state.

        Returns:
            None.
        """
        self._sync_theme_from_provider()
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
            theme="dark" if self._initial_dark_mode else "light",
            show_legend=False,
            show_x_axis_labels=True,
            show_y_axis_labels=False,
            on_x_range_changed=self._on_plot_x_range_changed,
            on_measurement_changed=self._on_measurement_changed,
            on_series_visibility_changed=self._on_series_visibility_changed,
            layout_margins_profile=home_stack_layout_margins_profile(),
        )
        self._plot.register_series_menu_items(self._sum_intensity_series_menu_items())
        self._plot.container.classes("w-full h-full min-h-0 flex-1")

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh after matching sum-intensity or diameter analysis completion.

        Args:
            event: Analysis completion state event.

        Returns:
            None.
        """
        if event.analysis_kind not in {AnalysisKind.SUM_INTENSITY, AnalysisKind.DIAMETER}:
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
        candidate = (x_min, x_max)
        if x_ranges_equal(candidate, self._primary_x_range):
            return
        self._plot_originated_x_range = True
        self.event_bus.publish(SetPrimaryXRangeIntent(x_min=x_min, x_max=x_max))

    def _on_primary_x_range_changed(self, event: PrimaryXRangeChanged) -> None:
        """Apply authoritative app-level x-axis range to the child plot.

        Args:
            event: Primary x-range state event.

        Returns:
            None.
        """
        self._primary_x_range = (event.x_min, event.x_max)
        if self._plot_originated_x_range:
            self._plot_originated_x_range = False
            return
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

    def _on_series_visibility_changed(self, series_name: str, visible: bool) -> None:
        """Refresh the right y-axis label when derivative or diameter toggles.

        Args:
            series_name: Context-menu series name.
            visible: Visibility after the toggle.

        Returns:
            None.
        """
        del visible
        if series_name in {_DERIVATIVE_TRACE_NAME, _DIAMETER_TRACE_NAME}:
            self._apply_y2_label()

    def _apply_y2_label(self) -> None:
        """Set the right y-axis title from visible derivative/diameter overlays.

        Returns:
            None.
        """
        if self._plot is None:
            return
        deriv_visible = self._plot.is_series_visible(_DERIVATIVE_TRACE_NAME)
        diam_visible = self._plot.is_series_visible(_DIAMETER_TRACE_NAME)
        if not deriv_visible and not diam_visible:
            self._plot.set_y2_label("")
        elif deriv_visible:
            self._plot.set_y2_label(_DERIVATIVE_Y2_LABEL)
        else:
            analysis = self._get_selected_diameter_analysis()
            if analysis is not None:
                self._plot.set_y2_label(analysis.get_plot_data().y_label)
            else:
                self._plot.set_y2_label("Diameter (um)")

    def _on_theme_changed(self, event: ThemeChanged) -> None:
        """Apply an application theme change to the child Plotly widget.

        Args:
            event: Theme state event published by the page header.

        Returns:
            None.
        """
        if self._plot is None:
            return
        self._plot.set_dark_mode(event.dark_mode)

    def _sync_theme_from_provider(self) -> None:
        """Apply the current application theme when a provider is available.

        Returns:
            None.
        """
        if self._plot is None or self._dark_mode_provider is None:
            return
        self._plot.set_dark_mode(bool(self._dark_mode_provider()))

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
            traces, scatters = self._build_series_from_analysis(analysis)
            self._plot.set_series(traces=traces, scatters=scatters)
        except (KeyError, ValueError) as exc:
            self._clear_plot(f"Sum-intensity plot unavailable: {exc}")
            return
        self._apply_y2_label()
        self._apply_axis_labels(analysis)
        self._apply_primary_x_range_to_plot()

    def _apply_axis_labels(self, analysis: SumIntensityAnalysis) -> None:
        """Set x/y axis titles from the canonical df/f0 plot data.

        Args:
            analysis: Selected sum-intensity analysis.

        Returns:
            None.
        """
        if self._plot is None:
            return
        plot_data = analysis.get_plot_data()
        if plot_data is None:
            return
        x_label = kymograph_time_x_label(
            self.get_selected_acq_image(),
            fallback=plot_data.x_label,
        )
        self._plot.set_x_label(x_label)
        self._plot.set_y_label(plot_data.y_label)

    def _build_series_from_analysis(
        self,
        analysis: SumIntensityAnalysis,
    ) -> tuple[list[PlotlyTraceData], list[PlotlyScatterData]]:
        """Build Plotly trace and scatter models from a sum-intensity analysis.

        Args:
            analysis: Selected sum-intensity analysis.

        Returns:
            Tuple of continuous traces and scatter overlays for ``set_series``.
        """
        traces = [
            self._trace_data(analysis.get_trace(SumIntensityTraceKey.DF_F_SIGNAL)),
            self._trace_data(
                analysis.get_trace(SumIntensityTraceKey.D_DF_F_SIGNAL),
                y_axis="right",
            ),
        ]
        width_traces = analysis.get_width_trace()
        if isinstance(width_traces, tuple):
            for trace in width_traces:
                if len(trace.x) > 0:
                    traces.append(self._trace_data(trace))
        elif len(width_traces.x) > 0:
            traces.append(self._trace_data(width_traces))

        scatters: list[PlotlyScatterData] = []
        for points in (
            analysis.get_event_points(SumIntensityEventPointKey.ONSETS),
            analysis.get_event_points(SumIntensityEventPointKey.PEAKS),
        ):
            if len(points.x) > 0:
                scatters.append(self._scatter_data(points))
        diameter_trace = self._diameter_trace_data()
        if diameter_trace is not None:
            traces.append(diameter_trace)
        return traces, scatters

    @staticmethod
    def _sum_intensity_series_menu_items() -> list[PlotlySeriesMenuItem]:
        """Return context-menu toggles for optional sum-intensity overlays.

        Returns:
            Menu item definitions keyed by AcqStore ``ResultTrace`` /
            ``ResultPoints`` names.
        """
        items = [
            PlotlySeriesMenuItem(
                series_name=_DERIVATIVE_TRACE_NAME,
                label=_DERIVATIVE_TRACE_NAME,
                default_visible=False,
                kind="trace",
            ),
        ]
        for level in PeakWidthLevel:
            name = f"Peak {level.value.replace('_', ' ')}"
            items.append(
                PlotlySeriesMenuItem(
                    series_name=name,
                    label=name,
                    default_visible=level is PeakWidthLevel.WIDTH_50,
                    kind="trace",
                )
            )
        items.extend(
            [
                PlotlySeriesMenuItem(
                    series_name="Onsets",
                    label="Onsets",
                    default_visible=True,
                    kind="scatter",
                ),
                PlotlySeriesMenuItem(
                    series_name="Peaks",
                    label="Peaks",
                    default_visible=True,
                    kind="scatter",
                ),
                PlotlySeriesMenuItem(
                    series_name=_DIAMETER_TRACE_NAME,
                    label="Diameter",
                    default_visible=False,
                    kind="trace",
                    separator_before=True,
                ),
            ]
        )
        return items

    def _trace_data(
        self,
        trace: ResultTrace,
        *,
        y_axis: PlotlyYAxisSide = "left",
    ) -> PlotlyTraceData:
        """Convert one AcqStore result trace to Plotly trace data.

        Args:
            trace: Public AcqStore result trace.
            y_axis: Primary ``y`` axis (``"left"``) or overlaid ``y2`` axis
                (``"right"``).

        Returns:
            Immutable Plotly trace data.
        """
        visible = True
        if self._plot is not None:
            visible = self._plot.is_series_visible(str(trace.name))
        return PlotlyTraceData.from_sequences(
            name=str(trace.name),
            x=trace.x,
            y=trace.y,
            visible=visible,
            y_axis=y_axis,
        )

    def _diameter_trace_data(self) -> PlotlyTraceData | None:
        """Return optional diameter overlay trace from the active diameter analysis.

        Returns:
            Plotly trace on ``yaxis2`` when diameter plot data exists, else ``None``.
        """
        diameter_analysis = self._get_selected_diameter_analysis()
        if diameter_analysis is None:
            return None
        plot_data = diameter_analysis.get_plot_data()
        if plot_data is None:
            return None
        return self._plot_data_trace(plot_data, y_axis="right")

    def _plot_data_trace(
        self,
        plot_data: AnalysisPlotData,
        *,
        y_axis: PlotlyYAxisSide = "left",
    ) -> PlotlyTraceData:
        """Convert :class:`AnalysisPlotData` to Plotly trace data.

        Args:
            plot_data: Display-ready analysis plot payload.
            y_axis: Primary ``y`` axis (``"left"``) or overlaid ``y2`` axis
                (``"right"``).

        Returns:
            Immutable Plotly trace data.
        """
        visible = True
        if self._plot is not None:
            visible = self._plot.is_series_visible(str(plot_data.series_name))
        return PlotlyTraceData.from_sequences(
            name=str(plot_data.series_name),
            x=plot_data.x,
            y=plot_data.y,
            visible=visible,
            y_axis=y_axis,
        )

    def _scatter_data(self, points: ResultPoints) -> PlotlyScatterData:
        """Convert one AcqStore point collection to Plotly scatter data.

        Args:
            points: Public AcqStore event points.

        Returns:
            Immutable Plotly scatter overlay data.
        """
        visible = True
        if self._plot is not None:
            visible = self._plot.is_series_visible(str(points.name))
        return PlotlyScatterData.from_sequences(
            name=str(points.name),
            x=points.x,
            y=points.y,
            visible=visible,
        )

    def _clear_plot(self, message: str) -> None:
        """Clear plot contents and set empty-state text.

        Args:
            message: Human-readable status text.

        Returns:
            None.
        """
        if self._plot is not None:
            self._plot.set_series()
            self._plot.set_y2_label("")
            self._plot.set_placeholder_text(message)

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

    def _get_selected_diameter_analysis(self) -> DiameterAnalysis | None:
        """Return diameter analysis for the active file/channel/ROI selection.

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
                DiameterAnalysis.analysis_name,
                int(self.current_selection.channel),
                int(self.current_selection.roi_id),
            )
        )
        if not isinstance(analysis, DiameterAnalysis):
            return None
        return analysis

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
