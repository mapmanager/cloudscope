"""View for plotting selected sum-intensity analysis results."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from nicegui import run, ui

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
    SumIntensitySummaryKey,
    SumIntensityTraceKey,
)
from cloudscope.app_config import home_stack_layout_margins_profile
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import (
    AnalysisCompleted,
    AnalysisKind,
    AnalysisUiMode,
    AnalysisUiModeChanged,
    BeginAnalysisUiModeIntent,
    CancelAnalysisUiModeIntent,
    UpdateAnalysisDetectionParamsIntent,
)
from cloudscope.events.roi import RoiChanged
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent, x_ranges_equal
from cloudscope.plot_axis_labels import kymograph_time_x_label
from cloudscope.session_state import (
    VIEW_SESSION_SCHEMA_VERSION,
    require_keys,
    require_schema_version,
    selection_guard_from_selection,
)
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.sum_intensity_plot_toolbar import SumIntensityPlotToolbar
from cloudscope.views.view_ids import ViewId
from nicewidgets.plotly_plot.display_options import PlotlyPlotDisplayOptions
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
_MANUAL_F0_MEASUREMENT_NAME = "manual-f0"
_AUTO_F0_TRACE_NAME = "Auto F0"
_MANUAL_F0_LINE_COLOR = "#facc15"
_AUTO_F0_LINE_COLOR = "#38bdf8"


@dataclass(slots=True)
class SumIntensityPlotViewState:
    """Serializable reconnect session state for :class:`SumIntensityPlotView`.

    Owning the blob shape here keeps the view thin. In addition to the child
    Plotly widget display options, this view has per-series overlay visibility
    (derivative, peak-width traces, onsets, peaks, diameter) driven by
    context-menu toggles, so ``series_visibility`` is captured and restored.

    Args:
        selection_guard: Selection identity captured at export time and used by
            :class:`BaseView` to skip stale reconnect blobs.
        display_options: Child Plotly widget display options.
        series_visibility: Visibility per context-menu series name.
        schema_version: Session blob schema version.
    """

    selection_guard: dict[str, Any]
    display_options: PlotlyPlotDisplayOptions = field(default_factory=PlotlyPlotDisplayOptions)
    series_visibility: dict[str, bool] = field(default_factory=dict)
    schema_version: int = VIEW_SESSION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable session blob.

        Returns:
            Mapping with schema version, selection guard, nested display
            options, and per-series visibility.
        """
        return {
            'schema_version': self.schema_version,
            'selection_guard': dict(self.selection_guard),
            'display_options': self.display_options.to_dict(),
            'series_visibility': dict(self.series_visibility),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SumIntensityPlotViewState:
        """Build state from a blob produced by :meth:`to_dict`.

        Args:
            data: Session blob from :meth:`export_session_state`.

        Returns:
            Reconstructed :class:`SumIntensityPlotViewState`.

        Raises:
            KeyError: If required keys (including ``schema_version``) are absent.
            ValueError: If ``schema_version`` is unsupported.
        """
        require_schema_version(data)
        require_keys(data, 'selection_guard', 'display_options', 'series_visibility')
        return cls(
            selection_guard=dict(data['selection_guard']),
            display_options=PlotlyPlotDisplayOptions.from_dict(data['display_options']),
            series_visibility={
                str(name): bool(visible)
                for name, visible in dict(data['series_visibility']).items()
            },
            schema_version=int(data.get('schema_version', VIEW_SESSION_SCHEMA_VERSION)),
        )


def _schedule_coro(coro: Coroutine[Any, Any, None]) -> None:
    """Run ``coro`` on the running loop, or ``asyncio.run`` when no loop exists.

    Args:
        coro: Coroutine to schedule.

    Returns:
        None.
    """
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


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
        self._toolbar: SumIntensityPlotToolbar | None = None
        self._f0_container: ui.element | None = None
        self._f0_plot: PlotlyPlotWidget | None = None
        self._plot: PlotlyPlotWidget | None = None
        self._primary_x_range: tuple[float | None, float | None] = (None, None)
        self._plot_originated_x_range = False
        self._last_measurement_event: MeasurementChangeEvent | None = None
        self._plot_refresh_generation = 0
        self._set_f0_mode = False
        self._pending_f0: float | None = None
        self._auto_f0: float | None = None
        self._set_f0_x: tuple[float, ...] = ()
        self._manual_f0_line_present = False
        self._auto_f0_trace_present = False
        self._live_set_running = False

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
        if not self._should_suppress_reconnect_hydrate():
            self._refresh_plot_from_current_selection()
        return self.root

    def export_session_state(self) -> dict[str, Any]:
        """Return reconnect session chrome for the sum-intensity plot.

        Returns:
            Session blob with display options.
        """
        plot = self._plot
        display_options = (
            plot.display_options if plot is not None else PlotlyPlotDisplayOptions()
        )
        state = SumIntensityPlotViewState(
            selection_guard=selection_guard_from_selection(self.current_selection),
            display_options=display_options,
            series_visibility=self._current_series_visibility(),
        )
        return state.to_dict()

    def apply_session_state(self, data: dict[str, Any]) -> None:
        """Apply reconnect session chrome to the sum-intensity plot widget.

        Args:
            data: Session blob from :meth:`export_session_state`.

        Returns:
            None.
        """
        state = SumIntensityPlotViewState.from_dict(data)
        self._apply_plot_display_options(state.display_options)
        self._apply_series_visibility(state.series_visibility)

    def _cache_reconnect_primary_x_range(
        self,
        primary_x_range: tuple[float | None, float | None],
    ) -> None:
        """Cache shared x-range from reconnect hydrate.

        Args:
            primary_x_range: Authoritative x-range from ``HomePageState``.

        Returns:
            None.
        """
        self._primary_x_range = primary_x_range

    def _apply_plot_display_options(self, options: PlotlyPlotDisplayOptions) -> None:
        """Push display options into the child Plotly widget.

        Args:
            options: Desired widget display options.

        Returns:
            None.
        """
        if self._plot is None:
            return
        self._plot.set_x_axis_labels_visible(options.show_x_axis_labels)
        self._plot.set_y_axis_labels_visible(options.show_y_axis_labels)
        self._plot.set_plotly_toolbar_visible(options.show_plotly_toolbar)
        self._plot.set_hover_info_visible(options.show_hover_info)
        self._plot.set_legend_visible(options.show_legend)

    def _current_series_visibility(self) -> dict[str, bool]:
        """Return visibility per context-menu series from the child widget.

        Returns:
            Mapping of series name to visibility for each registered menu item,
            or an empty mapping when the plot is not built.
        """
        if self._plot is None:
            return {}
        return {
            item.series_name: self._plot.is_series_visible(item.series_name)
            for item in self._sum_intensity_series_menu_items()
        }

    def _apply_series_visibility(self, series_visibility: dict[str, bool]) -> None:
        """Restore per-series overlay visibility into the child widget.

        Uses :meth:`PlotlyPlotWidget.set_series_visible_state` so visibility is
        applied even before plot data is loaded; the next refresh honors it.

        Args:
            series_visibility: Mapping of series name to visibility.

        Returns:
            None.
        """
        if self._plot is None:
            return
        for name, visible in series_visibility.items():
            self._plot.set_series_visible_state(name, visible)
        self._apply_y2_label()

    def subscribe_events(self) -> None:
        """Subscribe to events that can change displayed sum-intensity results.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed))
        self.add_subscription(self.event_bus.subscribe(RoiChanged, self._on_roi_changed))
        self.add_subscription(self.event_bus.subscribe(PrimaryXRangeChanged, self._on_primary_x_range_changed))
        self.add_subscription(self.event_bus.subscribe(ThemeChanged, self._on_theme_changed))
        self.add_subscription(
            self.event_bus.subscribe(AnalysisUiModeChanged, self._on_analysis_ui_mode_changed)
        )

    def refresh_from_state(self) -> None:
        """Refresh the plot from current application state.

        Returns:
            None.
        """
        self._sync_theme_from_provider()
        self._refresh_plot_from_current_selection()

    def on_primary_selection_changed(self) -> None:
        """Refresh the plot when the selected file/channel/ROI changes.

        Returns:
            None.
        """
        self._refresh_plot_from_current_selection()

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

        Layout (top to bottom): Edit F0 toolbar, F0 plot, primary df/f0 plot.
        Toolbar and F0 plot are hidden until Edit F0 mode is active.

        Returns:
            None.
        """
        self._toolbar = SumIntensityPlotToolbar(
            on_set_manual_f0=self._on_set_manual_f0_clicked,
            on_set_auto_f0=self._on_set_auto_f0_clicked,
            on_close=self._on_edit_f0_close_clicked,
            on_percentile_changed=self._on_edit_f0_percentile_preview,
        )
        self._toolbar.build()
        self._toolbar.set_visible(False)

        with ui.element("div").classes(
            "w-full shrink-0 min-h-0 h-40"
        ) as self._f0_container:
            self._f0_plot = PlotlyPlotWidget(
                display_options=PlotlyPlotDisplayOptions(
                    theme="dark" if self._initial_dark_mode else "light",
                    show_legend=False,
                    show_x_axis_labels=True,
                    show_y_axis_labels=True,
                ),
                on_x_range_changed=self._on_plot_x_range_changed,
                on_measurement_changed=self._on_f0_measurement_changed,
                layout_margins_profile=home_stack_layout_margins_profile(),
            )
            self._f0_plot.container.classes("w-full h-full min-h-0")
        self._f0_container.set_visibility(False)

        self._plot = PlotlyPlotWidget(
            display_options=PlotlyPlotDisplayOptions(
                theme="dark" if self._initial_dark_mode else "light",
                show_legend=False,
                show_x_axis_labels=True,
                show_y_axis_labels=False,
            ),
            on_x_range_changed=self._on_plot_x_range_changed,
            on_series_visibility_changed=self._on_series_visibility_changed,
            on_build_context_menu=self._build_primary_plot_context_menu,
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
        if event.analysis_kind is AnalysisKind.SUM_INTENSITY and self._live_set_running:
            self._live_set_running = False
            if self._toolbar is not None:
                self._toolbar.set_actions_enabled(True)
        self._refresh_plot_from_current_selection()

    def _on_roi_changed(self, event: RoiChanged) -> None:
        """Refresh when ROI changes may affect selected analysis results.

        Args:
            event: ROI changed state event.

        Returns:
            None.
        """
        if event.selection.file_id != self.current_selection.file_id:
            return
        self._refresh_plot_from_current_selection()

    def _on_plot_x_range_changed(self, x_min: float | None, x_max: float | None) -> None:
        """Publish user-driven Plotly x-range changes as app-level intent.

        Shared by the primary plot and the Edit F0 plot so either child can
        drive the app primary x-range.

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

    def _on_f0_measurement_changed(self, event: MeasurementChangeEvent) -> None:
        """Track Manual F0 H-line drags on the Edit F0 plot.

        Args:
            event: Measurement callback payload from ``PlotlyPlotWidget``.

        Returns:
            None.
        """
        self._last_measurement_event = event
        if not self._set_f0_mode:
            return
        if event.name != _MANUAL_F0_MEASUREMENT_NAME:
            return
        if event.kind != "line":
            return
        self._pending_f0 = float(event.position)
        if self._toolbar is not None:
            self._toolbar.set_pending_f0(self._pending_f0)

    def _on_analysis_ui_mode_changed(self, event: AnalysisUiModeChanged) -> None:
        """Enter or leave Edit F0 mode from authoritative controller state.

        Args:
            event: Analysis UI mode state event.

        Returns:
            None.
        """
        if event.is_active:
            if event.mode is not AnalysisUiMode.SET_F0:
                return
            if event.analysis_kind is not AnalysisKind.SUM_INTENSITY:
                return
            if event.selection != self._selection_snapshot():
                return
            self._enter_edit_f0_mode()
            return
        if self._set_f0_mode:
            self._exit_edit_f0_mode()

    def _build_primary_plot_context_menu(self, _widget: PlotlyPlotWidget) -> None:
        """Add Checkable Edit F0 entry to the primary plot context menu.

        Args:
            _widget: Plotly widget rebuilding its menu (unused).

        Returns:
            None.
        """
        prefix = "✓ " if self._set_f0_mode else ""
        ui.menu_item(f"{prefix}Edit F0", on_click=self._on_edit_f0_menu_clicked)

    def _on_edit_f0_menu_clicked(self) -> None:
        """Toggle Edit F0 mode from the primary plot context menu.

        Returns:
            None.
        """
        if self._set_f0_mode:
            self._on_edit_f0_close_clicked()
            return
        analysis = self._get_selected_sum_intensity_analysis()
        if analysis is None:
            ui.notify("No sum-intensity analysis for the current selection.", type="warning")
            return
        if analysis.result.table is None:
            ui.notify("Run sum-intensity analysis before editing F0.", type="warning")
            return
        f0 = analysis.get_summary_value(SumIntensitySummaryKey.F0_BASELINE)
        if not isinstance(f0, (int, float)):
            ui.notify("Sum-intensity analysis has no F0 baseline to edit.", type="warning")
            return
        self.event_bus.publish(
            BeginAnalysisUiModeIntent(
                analysis_kind=AnalysisKind.SUM_INTENSITY,
                mode=AnalysisUiMode.SET_F0,
                selection=self._selection_snapshot(),
            )
        )

    def _on_set_manual_f0_clicked(self) -> None:
        """Commit Manual F0 detection params and run sum-intensity analysis.

        Returns:
            None.
        """
        if not self._set_f0_mode or self._live_set_running:
            return
        if self._pending_f0 is None:
            ui.notify("Drag the Manual F0 line before setting.", type="warning")
            return
        self._live_set_running = True
        if self._toolbar is not None:
            self._toolbar.set_actions_enabled(False)
        self.event_bus.publish(
            UpdateAnalysisDetectionParamsIntent(
                analysis_kind=AnalysisKind.SUM_INTENSITY,
                selection=self._selection_snapshot(),
                param_updates={
                    "baseline_method": "manual",
                    "manual_f0_baseline": float(self._pending_f0),
                },
                run_analysis=True,
            )
        )

    def _on_set_auto_f0_clicked(self) -> None:
        """Commit percentile Auto F0 detection params and run analysis.

        Returns:
            None.
        """
        if not self._set_f0_mode or self._toolbar is None or self._live_set_running:
            return
        try:
            percentile = self._toolbar.get_baseline_percentile()
        except (RuntimeError, TypeError) as exc:
            ui.notify(f"Invalid percentile: {exc}", type="warning")
            return
        self._live_set_running = True
        self._toolbar.set_actions_enabled(False)
        self.event_bus.publish(
            UpdateAnalysisDetectionParamsIntent(
                analysis_kind=AnalysisKind.SUM_INTENSITY,
                selection=self._selection_snapshot(),
                param_updates={
                    "baseline_method": "percentile",
                    "baseline_percentile": float(percentile),
                },
                run_analysis=True,
            )
        )

    def _on_edit_f0_close_clicked(self) -> None:
        """Leave Edit F0 mode without changing detection parameters.

        Returns:
            None.
        """
        if not self._set_f0_mode:
            return
        self.event_bus.publish(
            CancelAnalysisUiModeIntent(
                analysis_kind=AnalysisKind.SUM_INTENSITY,
                mode=AnalysisUiMode.SET_F0,
                selection=self._selection_snapshot(),
            )
        )

    def _on_edit_f0_percentile_preview(self, percentile: float) -> None:
        """Preview Auto F0 on the F0 plot when the percentile control changes.

        Args:
            percentile: Toolbar percentile value.

        Returns:
            None.
        """
        if not self._set_f0_mode or self._f0_plot is None:
            return
        analysis = self._get_selected_sum_intensity_analysis()
        if analysis is None or analysis.result.table is None:
            return
        try:
            auto_f0 = analysis.get_percentile_f0_baseline(percentile=float(percentile))
        except ValueError:
            return
        self._auto_f0 = float(auto_f0)
        self._update_auto_f0_trace()

    def _enter_edit_f0_mode(self) -> None:
        """Show the Edit F0 toolbar and F0 plot; leave the primary plot unchanged.

        Returns:
            None.
        """
        if self._f0_plot is None or self._f0_container is None:
            return
        analysis = self._get_selected_sum_intensity_analysis()
        if analysis is None or analysis.result.table is None:
            ui.notify("No sum-intensity analysis for the current selection.", type="warning")
            return
        f0 = analysis.get_summary_value(SumIntensitySummaryKey.F0_BASELINE)
        if not isinstance(f0, (int, float)):
            ui.notify("Sum-intensity analysis has no F0 baseline to edit.", type="warning")
            return
        percentile = analysis.get_summary_value(SumIntensitySummaryKey.BASELINE_PERCENTILE)
        if not isinstance(percentile, (int, float)):
            percentile = float(analysis.detection_params["baseline_percentile"])
        auto_f0 = analysis.get_percentile_f0_baseline(percentile=float(percentile))
        self._set_f0_mode = True
        self._pending_f0 = float(f0)
        self._auto_f0 = float(auto_f0)
        self._live_set_running = False
        if self._toolbar is not None:
            self._toolbar.enter_edit_f0_mode()
            self._toolbar.set_baseline_percentile(float(percentile))
            self._toolbar.set_pending_f0(self._pending_f0)
            self._toolbar.set_actions_enabled(True)
        self._f0_container.set_visibility(True)
        self._refresh_f0_plot(preserve_manual_line=False)

    def _exit_edit_f0_mode(self) -> None:
        """Hide Edit F0 chrome; primary df/f0 plot is left as-is.

        Returns:
            None.
        """
        self._set_f0_mode = False
        self._pending_f0 = None
        self._auto_f0 = None
        self._set_f0_x = ()
        self._live_set_running = False
        self._remove_f0_overlays()
        if self._f0_plot is not None:
            self._f0_plot.set_series()
            self._f0_plot.set_placeholder_text(None)
        if self._f0_container is not None:
            self._f0_container.set_visibility(False)
        if self._toolbar is not None:
            self._toolbar.exit_edit_f0_mode()

    def _refresh_f0_plot(self, *, preserve_manual_line: bool) -> None:
        """Rebuild the Edit F0 plot from the selected analysis.

        Args:
            preserve_manual_line: When True, keep ``_pending_f0`` for the Manual
                H-line; otherwise initialize from summary ``f0_baseline``.

        Returns:
            None.
        """
        if self._f0_plot is None or not self._set_f0_mode:
            return
        analysis = self._get_selected_sum_intensity_analysis()
        if analysis is None or analysis.result.table is None:
            self._f0_plot.set_series()
            self._f0_plot.set_placeholder_text("No sum-intensity analysis for Edit F0")
            return
        if not preserve_manual_line or self._pending_f0 is None:
            f0 = analysis.get_summary_value(SumIntensitySummaryKey.F0_BASELINE)
            if isinstance(f0, (int, float)):
                self._pending_f0 = float(f0)
        percentile = (
            self._toolbar.get_baseline_percentile()
            if self._toolbar is not None
            else float(analysis.detection_params["baseline_percentile"])
        )
        try:
            self._auto_f0 = float(
                analysis.get_percentile_f0_baseline(percentile=float(percentile))
            )
        except ValueError as exc:
            self._f0_plot.set_series()
            self._f0_plot.set_placeholder_text(f"Edit F0 unavailable: {exc}")
            return
        self._remove_f0_overlays()
        trace = analysis.get_trace(SumIntensityTraceKey.DETRENDED_NORM_SUM_INTENSITY)
        self._set_f0_x = tuple(float(value) for value in trace.x.tolist())
        self._f0_plot.set_series(
            traces=[
                PlotlyTraceData.from_sequences(
                    name=str(trace.name),
                    x=trace.x,
                    y=trace.y,
                    visible=True,
                )
            ],
            scatters=[],
        )
        self._f0_plot.set_placeholder_text(None)
        x_label = kymograph_time_x_label(
            self.get_selected_acq_image(),
            fallback=trace.x_label,
        )
        self._f0_plot.set_x_label(x_label)
        self._f0_plot.set_y_label(trace.y_label)
        self._apply_primary_x_range_to_f0_plot()
        self._add_auto_f0_trace()
        if self._pending_f0 is not None:
            self._f0_plot.add_measurement_line(
                name=_MANUAL_F0_MEASUREMENT_NAME,
                orientation="horizontal",
                value=self._pending_f0,
                editable=True,
                color=_MANUAL_F0_LINE_COLOR,
                dash="solid",
                show_legend=False,
            )
            self._manual_f0_line_present = True
            if self._toolbar is not None:
                self._toolbar.set_pending_f0(self._pending_f0)

    def _add_auto_f0_trace(self) -> None:
        """Add the non-editable Auto F0 line as a continuous Plotly trace.

        Returns:
            None.
        """
        if self._f0_plot is None or self._auto_f0 is None or not self._set_f0_x:
            return
        y_values = tuple(self._auto_f0 for _ in self._set_f0_x)
        self._f0_plot.add_trace(
            name=_AUTO_F0_TRACE_NAME,
            x=self._set_f0_x,
            y=y_values,
            line_color=_AUTO_F0_LINE_COLOR,
            line_dash="dot",
        )
        self._auto_f0_trace_present = True

    def _update_auto_f0_trace(self) -> None:
        """Update the Auto F0 trace y values from ``_auto_f0``.

        Returns:
            None.
        """
        if (
            self._f0_plot is None
            or not self._auto_f0_trace_present
            or self._auto_f0 is None
            or not self._set_f0_x
        ):
            return
        y_values = tuple(self._auto_f0 for _ in self._set_f0_x)
        self._f0_plot.update_trace(name=_AUTO_F0_TRACE_NAME, x=self._set_f0_x, y=y_values)

    def _remove_f0_overlays(self) -> None:
        """Remove Manual F0 shape and Auto F0 trace from the F0 plot.

        Returns:
            None.
        """
        if self._f0_plot is None:
            self._manual_f0_line_present = False
            self._auto_f0_trace_present = False
            return
        if self._manual_f0_line_present:
            try:
                self._f0_plot.remove_measurement_line(_MANUAL_F0_MEASUREMENT_NAME)
            except KeyError:
                pass
            self._manual_f0_line_present = False
        if self._auto_f0_trace_present:
            try:
                self._f0_plot.remove_trace(_AUTO_F0_TRACE_NAME)
            except KeyError:
                pass
            self._auto_f0_trace_present = False

    def _selection_snapshot(self) -> PrimarySelection:
        """Return a copied selection snapshot for analysis UI intents.

        Returns:
            Copied primary selection.
        """
        return PrimarySelection(
            file_id=self.current_selection.file_id,
            channel=self.current_selection.channel,
            roi_id=self.current_selection.roi_id,
        )

    def _on_series_visibility_changed(self, series_name: str, visible: bool) -> None:
        """Refresh the right y-axis label when derivative or diameter toggles.

        The widget owns per-series visibility state; this view only reacts to
        the y2-axis label because ``visible`` is re-read from the widget in
        :meth:`_apply_y2_label`. The ``visible`` argument is part of the widget
        callback contract and is intentionally not used directly here.

        Args:
            series_name: Context-menu series name.
            visible: Visibility after the toggle.

        Returns:
            None.
        """
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
        """Apply an application theme change to the child Plotly widgets.

        Args:
            event: Theme state event published by the page header.

        Returns:
            None.
        """
        if self._plot is not None:
            self._plot.set_dark_mode(event.dark_mode)
        if self._f0_plot is not None:
            self._f0_plot.set_dark_mode(event.dark_mode)

    def _sync_theme_from_provider(self) -> None:
        """Apply the current application theme when a provider is available.

        Returns:
            None.
        """
        if self._dark_mode_provider is None:
            return
        dark = bool(self._dark_mode_provider())
        if self._plot is not None:
            self._plot.set_dark_mode(dark)
        if self._f0_plot is not None:
            self._f0_plot.set_dark_mode(dark)

    def _apply_primary_x_range_to_plot(self) -> None:
        """Push cached x-range state into the primary Plotly widget.

        Returns:
            None.
        """
        if self._plot is None:
            return
        x_min, x_max = self._primary_x_range
        if x_min is None or x_max is None:
            self._plot.reset_x_axis_limits()
        else:
            self._plot.set_x_axis_limits(x_min, x_max)
        self._apply_primary_x_range_to_f0_plot()

    def _apply_primary_x_range_to_f0_plot(self) -> None:
        """Push cached x-range state into the Edit F0 Plotly widget.

        Returns:
            None.
        """
        if self._f0_plot is None or not self._set_f0_mode:
            return
        x_min, x_max = self._primary_x_range
        if x_min is None or x_max is None:
            self._f0_plot.reset_x_axis_limits()
            return
        self._f0_plot.set_x_axis_limits(x_min, x_max)

    def _refresh_plot_from_current_selection(self) -> None:
        """Schedule async plot refresh from the current selection.

        Returns:
            None.
        """
        self._plot_refresh_generation += 1
        generation = self._plot_refresh_generation
        _schedule_coro(self._refresh_plot_async(generation))

    async def _refresh_plot_async(self, generation: int) -> None:
        """Push plot data after the NiceGUI client finishes mounting.

        Args:
            generation: Monotonic refresh token; stale tasks are dropped after
                superseding selection refreshes (for example build-time empty
                refreshes after async load publishes selection).

        Returns:
            None.
        """
        await run.io_bound(lambda: None)
        if generation != self._plot_refresh_generation:
            return
        self._refresh_plot()

    def _refresh_plot(self) -> None:
        """Refresh Plotly traces and overlays from selected sum-intensity analysis.

        The primary df/f0 plot always refreshes. When Edit F0 is active, the
        dedicated F0 plot is refreshed separately.

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
        if self._set_f0_mode:
            self._refresh_f0_plot(preserve_manual_line=True)

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
