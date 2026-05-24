"""NiceGUI ECharts line-plot widget."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from nicegui import ui

from nicewidgets.echart_widget.models import EChartAxisRange, EChartLineData

from cloudscope.utils.logging import get_logger
logger = get_logger(__name__)


class EChartWidget:
    """Thin wrapper around ``ui.echart`` for one analysis line plot.

    The widget owns ECharts options and exposes a small public API for viewers.
    It does not know anything about AcqStore or CloudScope.
    """

    def __init__(self) -> None:
        """Create an empty ECharts widget."""
        
        self.container = ui.echart(self._empty_options())
        self.container.on('datazoom', self._on_datazoom)

        self._line_data: EChartLineData | None = None
        self._x_range = EChartAxisRange()

    def _on_datazoom(self, event: dict[str, Any]) -> None:
        """Handle data zoom event.

        Args:
            event: Data zoom event.
        """

        print(event)
        
        logger.info(f'datazoom event: {event}')

        # ECharts returns percentage values (0 to 100) for the visible range
        # start_percent = event.args.get('start', 0)
        # end_percent = event.args.get('end', 100)
        
        # Calculate approximate indices based on your dataset size
        # total_items = len(self._line_data.x)
        # start_index = int((start_percent / 100) * (total_items - 1))
        # end_index = int((end_percent / 100) * (total_items - 1))
        
        # Get the actual values corresponding to the selected range
        # selected_start_val = self._line_data.x[start_index]
        # selected_end_val = self._line_data.x[end_index]

        start_value = event.get('startValue', 0)
        end_value = event.get('endValue', 100)
        logger.info(f'Range changed! Visible range: {start_value} to {end_value}')

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

        Returns:
            None.
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
        """Clear plotted data and reset axis limits.

        Returns:
            None.
        """
        self._line_data = None
        self._x_range = EChartAxisRange()
        self.apply()

    def set_x_axis_limits(self, x_min: float | None, x_max: float | None) -> None:
        """Set x-axis value limits and redraw.

        Args:
            x_min: Minimum x-axis value, or None for auto.
            x_max: Maximum x-axis value, or None for auto.

        Returns:
            None.
        """
        self._x_range = EChartAxisRange(x_min=x_min, x_max=x_max)
        self.apply()

    def reset_x_axis_limits(self) -> None:
        """Reset x-axis range to automatic scaling.

        Returns:
            None.
        """
        self.set_x_axis_limits(None, None)

    def apply(self) -> None:
        """Apply current chart state to the NiceGUI ECharts element.

        Returns:
            None.
        """
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
            return self._empty_options()
        return build_line_options(self._line_data, self._x_range)

    @staticmethod
    def _empty_options() -> dict[str, Any]:
        """Return an empty value/value chart option.

        Returns:
            Empty ECharts option dictionary.
        """
        return {
            "grid": {"left": 55, "right": 20, "top": 24, "bottom": 45},
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "value", "name": "", "min": None, "max": None},
            "yAxis": {"type": "value", "name": ""},
            "series": [],
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
            }
        ],
        # abb
        "dataZoom": [
            {
                "type": "inside",
                'xAxisIndex': 0,
                # 'yAxisIndex': 0,
            }
        ],
    }
