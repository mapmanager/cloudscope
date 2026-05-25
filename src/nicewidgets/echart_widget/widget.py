"""NiceGUI ECharts line-plot widget."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from nicegui import ui

from nicewidgets.echart_widget.event_overlay import EChartEventOverlayApi
from nicewidgets.echart_widget.models import EChartAxisRange, EChartLineData

from cloudscope.utils.logging import get_logger
logger = get_logger(__name__)


class EChartWidget:
    """Thin wrapper around ``ui.echart`` for one analysis line plot.

    The widget owns ECharts options and exposes separate public APIs for primary
    line data and event overlays. It does not know anything about AcqStore or
    CloudScope.
    """

    def __init__(
        self,
        *,
        on_x_range_selected: Callable[[float, float], None] | None = None,
    ) -> None:
        """Create an empty ECharts widget.

        Args:
            on_x_range_selected: Optional callback for user brush-selected
                x-ranges.
        """
        self._line_data: EChartLineData | None = None
        self._x_range = EChartAxisRange()
        self._pending_x_range: tuple[float, float] | None = None
        self._selecting_x = False
        self._on_x_range_selected = on_x_range_selected
        self.events = EChartEventOverlayApi(self)

        self.container = ui.echart(self._empty_options())
        self.container.on("chart:datazoom", self._on_datazoom)
        self.container.on("chart:brushselected", self._on_brush_selected)
        self.container.on("chart:mouseup", self._on_mouseup)
        self.container.on("mouseup", self._on_mouseup)
        self.container.on("chart:dblclick", self._on_double_click)
        self.container.on("dblclick", self._on_double_click)

    def set_line_data(
        self,
        *,
        x: Sequence[float],
        y: Sequence[float],
        x_label: str,
        y_label: str,
        series_name: str = "series",
    ) -> None:
        """Replace the plotted line data and redraw the chart.

        Args:
            x: X-axis values.
            y: Y-axis values.
            x_label: Human-readable x-axis label.
            y_label: Human-readable y-axis label.
            series_name: Human-readable series name.
        """
        self._line_data = EChartLineData.from_sequences(
            x=x,
            y=y,
            x_label=x_label,
            y_label=y_label,
            series_name=series_name,
        )
        self.apply()

    def clear(self) -> None:
        """Clear plotted data, event overlays, and reset axis limits."""
        self._line_data = None
        self._x_range = EChartAxisRange()
        self.events.clear_events()
        self.apply()

    def set_x_axis_limits(self, x_min: float | None, x_max: float | None) -> None:
        """Set x-axis value limits and redraw.

        Args:
            x_min: Minimum x-axis value, or None for auto.
            x_max: Maximum x-axis value, or None for auto.
        """
        self._x_range = EChartAxisRange(x_min=x_min, x_max=x_max)
        self.apply()

    def reset_x_axis_limits(self) -> None:
        """Reset x-axis range to automatic scaling."""
        self.set_x_axis_limits(None, None)

    def begin_select_x_range(self) -> None:
        """Enter one-shot user x-range selection mode."""
        self._selecting_x = True
        self._pending_x_range = None
        self._clear_brush()
        self.container.run_chart_method(
            "dispatchAction",
            {
                "type": "takeGlobalCursor",
                "key": "brush",
                "brushOption": {"brushType": "lineX", "brushMode": "single"},
            },
        )

    def cancel_select_x_range(self) -> None:
        """Cancel user x-range selection mode."""
        self._selecting_x = False
        self._pending_x_range = None
        self._clear_brush()
        self._disable_brush_cursor()

    def apply(self) -> None:
        """Apply current chart state to the NiceGUI ECharts element."""
        options = self.build_options()
        self.container.options.clear()
        self.container.options.update(options)
        self.container.update()

    def build_options(self) -> dict[str, Any]:
        """Build ECharts options for the current widget state.

        Returns:
            ECharts option dictionary.
        """
        if self._line_data is None:
            options = self._empty_options()
        else:
            options = build_line_options(self._line_data, self._x_range)
        if options["series"]:
            options["series"][0]["markArea"] = self.events.build_mark_area()
        return options

    def _on_datazoom(self, event: Any) -> None:
        """Log ECharts dataZoom events.

        Args:
            event: NiceGUI event arguments.
        """
        logger.debug("datazoom event: %s", getattr(event, "args", event))

    def _on_brush_selected(self, event: Any) -> None:
        """Cache the latest x-range while selecting.

        Args:
            event: NiceGUI brushselected event.
        """
        if not self._selecting_x:
            return
        coord_range = self._extract_x_brush_range(getattr(event, "args", {}))
        if coord_range is not None:
            self._pending_x_range = coord_range

    def _on_mouseup(self, event: Any) -> None:
        """Commit x-range selection on actual mouse release.

        Args:
            event: NiceGUI mouseup event.
        """
        _ = event
        if not self._selecting_x:
            return
        if self._pending_x_range is None:
            return
        x0, x1 = self._pending_x_range
        self.cancel_select_x_range()
        if self._on_x_range_selected is not None:
            self._on_x_range_selected(x0, x1)

    def _on_double_click(self, event: Any) -> None:
        """Reset x-axis range on double-click.

        Args:
            event: NiceGUI double-click event.
        """
        _ = event
        self.cancel_select_x_range()
        self.reset_x_axis_limits()

    def _clear_brush(self) -> None:
        """Clear the ECharts brush overlay."""
        self.container.run_chart_method(
            "dispatchAction",
            {"type": "brush", "command": "clear", "areas": []},
        )

    def _disable_brush_cursor(self) -> None:
        """Disable ECharts brush cursor mode."""
        self.container.run_chart_method(
            "dispatchAction",
            {
                "type": "takeGlobalCursor",
                "key": "brush",
                "brushOption": {"brushType": False},
            },
        )

    @staticmethod
    def _extract_x_brush_range(args: dict[str, Any]) -> tuple[float, float] | None:
        """Extract x-range from ECharts brushselected payload.

        Args:
            args: Event payload.

        Returns:
            ``(x_min, x_max)`` or None.
        """
        batch = args.get("batch", [])
        if not batch:
            return None
        areas = batch[0].get("areas", [])
        if not areas:
            return None
        coord_range = areas[0].get("coordRange")
        if coord_range is None or len(coord_range) != 2:
            return None
        x0 = float(coord_range[0])
        x1 = float(coord_range[1])
        return (min(x0, x1), max(x0, x1))

    @staticmethod
    def _empty_options() -> dict[str, Any]:
        """Return an empty value/value chart option.

        Returns:
            Empty ECharts option dictionary.
        """
        return {
            "animation": False,
            "animationDuration": 0,
            "animationDurationUpdate": 0,
            "grid": {"left": 55, "right": 20, "top": 24, "bottom": 45},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "value", "name": "", "min": None, "max": None},
            "yAxis": {"type": "value", "name": ""},
            "series": [],
            "brush": {"toolbox": ["lineX", "clear"], "xAxisIndex": 0, "brushMode": "single"},
        }


def build_line_options(line_data: EChartLineData, x_range: EChartAxisRange | None = None) -> dict[str, Any]:
    """Build ECharts options for one line plot.

    Args:
        line_data: Line data to plot.
        x_range: Optional x-axis range.

    Returns:
        ECharts option dictionary.
    """
    x_range = x_range or EChartAxisRange()
    return {
        "animation": False,
        "animationDuration": 0,
        "animationDurationUpdate": 0,
        "grid": {"left": 55, "right": 20, "top": 24, "bottom": 45},
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "value",
            "name": line_data.x_label,
            "nameLocation": "middle",
            "nameGap": 28,
            "min": x_range.x_min,
            "max": x_range.x_max,
        },
        "yAxis": {
            "type": "value",
            "name": line_data.y_label,
            "nameLocation": "middle",
            "nameGap": 38,
        },
        "series": [
            {
                "name": line_data.series_name,
                "type": "line",
                "data": [[x, y] for x, y in zip(line_data.x, line_data.y, strict=True)],
                "showSymbol": False,
                "lineStyle": {"width": 2},
                "animation": False,
                "animationDuration": 0,
                "animationDurationUpdate": 0,
            }
        ],
        "dataZoom": [{"type": "inside", "id": "dataZoomX", "xAxisIndex": 0, "filterMode": "none"}],
        "brush": {"toolbox": ["lineX", "clear"], "xAxisIndex": 0, "brushMode": "single"},
        "toolbox": {
            "feature": {
                "dataZoom": {"yAxisIndex": "none"},
                "restore": {},
                "brush": {"type": ["lineX", "clear"]},
            }
        },
    }
