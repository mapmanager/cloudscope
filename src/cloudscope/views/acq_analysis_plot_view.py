"""View for plotting selected AcqImage analysis results."""

from __future__ import annotations

from typing import Any

from nicegui import ui

from acqstore.acq_image.analysis.model import AnalysisPlotData
from cloudscope.event_bus import EventBus
from cloudscope.events import AnalysisCompleted, RoiChanged
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.echart_widget.widget import EChartWidget

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
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self.title = title
        self._status_label: ui.label | None = None
        self._chart: EChartWidget | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the analysis plot view.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        if parent is None:
            with ui.card().classes("w-full h-full min-h-0 flex flex-col overflow-hidden flex-1") as self.root:
                self._build_content()
        else:
            with parent:
                with ui.card().classes("w-full h-full min-h-0 flex flex-col overflow-hidden flex-1") as self.root:
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

    def refresh_from_state(self) -> None:
        """Refresh the plot from the current selection.

        Returns:
            None.
        """
        self._refresh_plot()

    def on_primary_selection_changed(self) -> None:
        """Refresh the plot when file/channel/ROI selection changes.

        Returns:
            None.
        """
        logger.info('')

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
        
        self._chart = EChartWidget()
        self._chart.container.classes("w-full h-full min-h-0 flex-1")

        self._status_label = ui.label("No analysis selected").classes("text-sm opacity-70 shrink-0")

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

    def _refresh_plot(self) -> None:
        """Refresh chart data from the selected AcqImage analysis.

        Returns:
            None.
        """
        if self._chart is None or self._status_label is None:
            return

        plot_data = self._get_selected_plot_data()
        if plot_data is None:
            self._chart.clear()
            self._status_label.text = self._empty_message()
            return

        self._chart.set_line_data(
            x=plot_data.x,
            y=plot_data.y,
            x_label=plot_data.x_label,
            y_label=plot_data.y_label,
            series_name=plot_data.series_name,
        )
        self._status_label.text = f"{plot_data.series_name}: {len(plot_data.x)} points"

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
