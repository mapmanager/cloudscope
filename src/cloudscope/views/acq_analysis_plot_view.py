"""View for plotting selected AcqImage analysis results."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from nicegui import ui

from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisPlotData
from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis
from cloudscope.event_bus import EventBus
from cloudscope.events.acq_image_events import (
    AcqImageEventSelectionChanged,
    AcqImageEventXRangeSelectedIntent,
    AcqImageEventsChanged,
)
from cloudscope.events.analysis import (
    AnalysisCompleted,
    BeginPlotXRangeSelection,
    CancelPlotXRangeSelection,
)
from cloudscope.events.roi import RoiChanged
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent, x_ranges_equal
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.plotly_plot.models import PlotlyTraceData
from nicewidgets.plotly_plot.widget import PlotlyPlotWidget

from cloudscope.utils.logging import get_logger
logger = get_logger(__name__)

PRIMARY_KYMOGRAPH_GROUP = "primary_kymograph"


class AcqAnalysisPlotView(BaseView):
    """Display the canonical x/y plot for the active primary kymograph analysis.

    The view is intentionally thin. It does not know analysis-specific table
    columns; it asks the active ``primary_kymograph`` analysis (radon velocity
    or diameter, enforced exclusive by ``AcqAnalysisSet``) for ``AnalysisPlotData``.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional page/controller state object.
        title: Card title.
        initially_visible: Whether this view starts visible.
        dark_mode: Initial Plotly layout theme state.
        dark_mode_provider: Optional callable returning current app dark-mode state.
    """

    view_id = ViewId.ACQ_ANALYSIS_PLOT
    disable_when_busy = False

    def __init__(
        self,
        event_bus: EventBus,
        app_state: Any | None = None,
        *,
        title: str = "Analysis plot",
        initially_visible: bool = True,
        dark_mode: bool = False,
        dark_mode_provider: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self.title = title
        self._dark_mode_provider = dark_mode_provider
        self._initial_dark_mode = bool(dark_mode)
        self._chart: PlotlyPlotWidget | None = None
        self._events_visible = True
        # Latest app-level ``primary_x_range`` cache, updated from
        # ``PrimaryXRangeChanged``. Re-applied to the plot after every
        # ``_refresh_plot`` so user/state range survives analysis-row clicks
        # (same file) where the controller intentionally does not reset.
        self._primary_x_range: tuple[float | None, float | None] = (None, None)
        self._chart_originated_x_range = False

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the analysis plot view.

        Args:
            parent: Optional NiceGUI parent.

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
        """Subscribe to analysis/ROI state events while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed))
        self.add_subscription(self.event_bus.subscribe(RoiChanged, self._on_roi_changed))
        self.add_subscription(self.event_bus.subscribe(BeginPlotXRangeSelection, self._on_begin_plot_x_range_selection))
        self.add_subscription(self.event_bus.subscribe(CancelPlotXRangeSelection, self._on_cancel_plot_x_range_selection))
        self.add_subscription(self.event_bus.subscribe(AcqImageEventsChanged, self._on_acq_image_events_changed))
        self.add_subscription(self.event_bus.subscribe(AcqImageEventSelectionChanged, self._on_acq_image_event_selection_changed))
        self.add_subscription(
            self.event_bus.subscribe(PrimaryXRangeChanged, self._on_primary_x_range_changed)
        )
        self.add_subscription(self.event_bus.subscribe(ThemeChanged, self._on_theme_changed))

    def refresh_from_state(self) -> None:
        """Refresh the plot from the current selection.

        Returns:
            None.
        """
        self._sync_theme_from_provider()
        self._refresh_plot()

    def on_primary_selection_changed(self) -> None:
        """Refresh the plot when file/channel/ROI selection changes.

        Returns:
            None.
        """
        # logger.info('')

        self._refresh_plot()

    def set_x_axis_limits(self, x_min: float | None, x_max: float | None) -> None:
        """Set chart x-axis limits.

        Args:
            x_min: Minimum x value, or None for auto.
            x_max: Maximum x value, or None for auto.

        Returns:
            None.
        """
        if self._chart is not None:
            self._chart.set_x_axis_limits(x_min, x_max)

    def reset_x_axis_limits(self) -> None:
        """Reset chart x-axis limits to automatic scaling.

        Returns:
            None.
        """
        if self._chart is not None:
            self._chart.reset_x_axis_limits()

    def _build_content(self) -> None:
        """Build static card content.

        Returns:
            None.
        """
        # each view is adding this label with name, comment it out
        # ui.label(self.title).classes("text-lg font-semibold shrink-0")
        
        self._chart = PlotlyPlotWidget(
            theme="dark" if self._initial_dark_mode else "light",
            show_legend=False,
            on_x_range_selected=self._on_x_range_selected,
            on_x_range_changed=self._on_chart_x_range_changed,
        )
        self._chart.container.classes("w-full h-full min-h-0 flex-1")

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh the plot when any primary-kymograph analysis finishes.

        Args:
            event: Analysis completion event.

        Returns:
            None.
        """
        if event.selection.file_id != self.current_selection.file_id:
            return
        if event.selection.channel != self.current_selection.channel:
            return
        if event.selection.roi_id != self.current_selection.roi_id:
            return
        
        logger.warning('')

        self._refresh_plot()

    def _on_roi_changed(self, event: RoiChanged) -> None:
        """Refresh the plot when ROI mutation may have removed analysis.

        Args:
            event: ROI changed state event.

        Returns:
            None.
        """
        if event.selection.file_id != self.current_selection.file_id:
            return

        logger.warning('')

        self._refresh_plot()

    def _on_begin_plot_x_range_selection(self, event: BeginPlotXRangeSelection) -> None:
        """Enter chart x-range selection mode when selection matches.

        Args:
            event: Begin selection state event.
        """
        if self._chart is None:
            return
        if event.selection.file_id != self.current_selection.file_id:
            return
        if event.selection.channel != self.current_selection.channel:
            return
        if event.selection.roi_id != self.current_selection.roi_id:
            return
        self._chart.begin_select_x_range()

    def _on_cancel_plot_x_range_selection(self, event: CancelPlotXRangeSelection) -> None:
        """Cancel chart x-range selection mode.

        Args:
            event: Cancel selection state event.
        """
        _ = event
        if self._chart is not None:
            self._chart.cancel_select_x_range()

    def _on_acq_image_events_changed(self, event: AcqImageEventsChanged) -> None:
        """Refresh chart overlays from event state.

        Args:
            event: Events-changed state event.
        """
        if self._chart is None:
            return
        if event.selection.file_id != self.current_selection.file_id:
            return
        if event.selection.channel != self.current_selection.channel:
            return
        if event.selection.roi_id != self.current_selection.roi_id:
            return
        self._events_visible = event.visible
        self._chart.events.set_events(_overlay_rows_to_objects(event.rows))
        self._chart.events.select_event(None if event.selected_event_id is None else str(event.selected_event_id))
        self._chart.events.set_visible(event.visible)

    def _on_acq_image_event_selection_changed(self, event: AcqImageEventSelectionChanged) -> None:
        """Apply selected event styling without rebuilding overlays.

        Args:
            event: Event-selection state event.
        """
        if self._chart is None:
            return
        try:
            self._chart.events.select_event(None if event.selected_event_id is None else str(event.selected_event_id))
        except KeyError:
            self._chart.events.select_event(None)

    def _on_x_range_selected(self, x0: float, x1: float) -> None:
        """Publish user-selected x range to the event controller.

        Args:
            x0: First x coordinate.
            x1: Second x coordinate.
        """
        self.event_bus.publish(
            AcqImageEventXRangeSelectedIntent(
                selection=self._copy_current_selection(),
                x0=float(x0),
                x1=float(x1),
            )
        )

    def _on_chart_x_range_changed(
        self, x_min: float | None, x_max: float | None
    ) -> None:
        """Producer hook: turn chart datazoom into an app-level intent.

        Args:
            x_min: Minimum x value, or ``None`` for auto.
            x_max: Maximum x value, or ``None`` for auto.

        Returns:
            None.
        """
        candidate = (x_min, x_max)
        if x_ranges_equal(candidate, self._primary_x_range):
            return
        self._chart_originated_x_range = True
        self.event_bus.publish(SetPrimaryXRangeIntent(x_min=x_min, x_max=x_max))

    def _on_theme_changed(self, event: ThemeChanged) -> None:
        """Apply application theme changes to the child plot."""
        if self._chart is None:
            return
        self._chart.set_dark_mode(event.dark_mode)

    def _sync_theme_from_provider(self) -> None:
        """Apply current application theme when a provider is available."""
        if self._chart is None or self._dark_mode_provider is None:
            return
        self._chart.set_dark_mode(bool(self._dark_mode_provider()))

    def _on_primary_x_range_changed(self, event: PrimaryXRangeChanged) -> None:
        """Consumer: cache the authoritative x-range and apply it to the chart.

        Args:
            event: State event from :class:`XRangeController`.

        Returns:
            None.
        """
        self._primary_x_range = (event.x_min, event.x_max)
        if self._chart_originated_x_range:
            self._chart_originated_x_range = False
            return
        self._apply_primary_x_range_to_chart()

    def _apply_primary_x_range_to_chart(self) -> None:
        """Push the cached ``primary_x_range`` to the chart.

        Idempotent: ``(None, None)`` calls ``reset_x_axis_limits``; otherwise
        ``set_x_axis_limits(x_min, x_max)``. Skipped when the chart has not
        been built yet.

        Returns:
            None.
        """
        if self._chart is None:
            return
        x_min, x_max = self._primary_x_range
        if x_ranges_equal(self._chart.x_range_limits, self._primary_x_range):
            return
        if x_min is None or x_max is None:
            self._chart.reset_x_axis_limits()
            return
        self._chart.set_x_axis_limits(x_min, x_max)

    def _copy_current_selection(self):
        """Return a copied current selection."""
        from cloudscope.state import PrimarySelection

        return PrimarySelection(
            file_id=self.current_selection.file_id,
            channel=self.current_selection.channel,
            roi_id=self.current_selection.roi_id,
        )

    def _refresh_plot(self) -> None:
        """Refresh chart data from the selected AcqImage analysis.

        Returns:
            None.
        """
        if self._chart is None:
            return

        plot_data = self._get_selected_plot_data()
        if plot_data is None:
            self._clear_chart(self._empty_message())
            return

        self._chart.set_placeholder_text(None)
        self._chart.set_series(
            traces=[
                PlotlyTraceData.from_sequences(
                    name=plot_data.series_name,
                    x=plot_data.x,
                    y=plot_data.y,
                )
            ]
        )
        self._refresh_event_overlays()
        # Re-apply the cached app-level x-range; ``set_series`` preserves the
        # widget's logical ``_x_range`` but the explicit re-apply keeps the
        # plot aligned with ``HomePageState`` on analysis-row clicks within
        # the same file.
        self._apply_primary_x_range_to_chart()

    def _clear_chart(self, message: str) -> None:
        """Remove plotted data, event overlays, and show empty-state text.

        Args:
            message: Human-readable empty-state message.

        Returns:
            None.
        """
        if self._chart is None:
            return
        self._chart.set_series(traces=[])
        self._chart.events.clear_events()
        self._chart.set_placeholder_text(message)

    def _refresh_event_overlays(self) -> None:
        """Refresh chart event overlays from backend state and visibility."""
        if self._chart is None:
            return
        self._chart.events.set_events(self._get_selected_event_overlays())
        self._chart.events.set_visible(self._events_visible)

    def _get_selected_plot_data(self) -> AnalysisPlotData | None:
        """Return plot data for the active primary-kymograph analysis.

        Returns:
            Plot data, or None when selection/analysis is unavailable.
        """
        acq_image = self.get_selected_acq_image()
        if acq_image is None:
            return None
        if self.current_selection.channel is None or self.current_selection.roi_id is None:
            return None
        analysis = acq_image.analysis_set.get_primary_kymograph_analysis(
            channel=int(self.current_selection.channel),
            roi_id=int(self.current_selection.roi_id),
        )
        if analysis is None:
            return None
        return analysis.get_plot_data()

    def _get_selected_event_overlays(self) -> list[object]:
        """Return selected event overlays from event analysis, if present.

        Returns:
            Backend event objects compatible with ``PlotlyPlotWidget.events``.
        """
        acq_image = self.get_selected_acq_image()
        if acq_image is None:
            return []
        if self.current_selection.channel is None or self.current_selection.roi_id is None:
            return []
        analysis = acq_image.analysis_set.get(
            AnalysisKey(
                EventAnalysis.analysis_name,
                int(self.current_selection.channel),
                int(self.current_selection.roi_id),
            )
        )
        if not isinstance(analysis, EventAnalysis):
            return []
        return analysis.get_events()

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
        return f"No primary-kymograph analysis for selected channel={self.current_selection.channel}, roi_id={self.current_selection.roi_id}"


class _OverlayRowObject:
    """Small adapter object for event rows used by chart overlays."""

    def __init__(self, row: dict[str, object]) -> None:
        """Create an overlay adapter from a row."""
        self.id = str(row["id"])
        self.x0 = float(row["x0"])
        self.x1 = float(row["x1"])
        self.event_type = str(row.get("event_type", "user"))


def _overlay_rows_to_objects(rows: list[dict[str, object]]) -> list[_OverlayRowObject]:
    """Convert event rows into chart overlay objects."""
    return [_OverlayRowObject(dict(row)) for row in rows]
