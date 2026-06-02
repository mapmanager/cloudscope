"""NiceGUI ECharts line-plot widget."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from typing import Any

from nicegui import app, ui

from nicewidgets.echart_widget.clipboard import (
    copy_echart_png_to_browser_clipboard,
    get_echart_png_bytes,
)
from nicewidgets.echart_widget.context_menu import EChartWidgetContextMenu
from nicewidgets.echart_widget.display_options import EChartDisplayOptions
from nicewidgets.echart_widget.event_overlay import EChartEventOverlayApi
from nicewidgets.echart_widget.models import EChartAxisRange, EChartLineData
from nicewidgets.utils.clipboard import copy_png_bytes_to_native_clipboard
from nicewidgets.utils.logging import get_logger

logger = get_logger(__name__)

# Callback type for continuous x-range changes (datazoom). ``(None, None)``
# means "auto / reset to full extent".
OnEChartXRangeChanged = Callable[[float | None, float | None], None]

_X_RANGE_ECHO_EPS = 1e-9

# JS callback string for ``xAxis.axisLabel.formatter``. ECharts' default tick
# formatter prints the raw axis value, which for explicitly set ``min`` / ``max``
# leaks full float precision (e.g. ``8.181001796798633``) at the first and last
# ticks while interior "nice" ticks stay clean. Rounding to three decimals and
# normalizing back to a number (``+x.toFixed(3)``) trims the long edges without
# adding trailing zeros to interior ticks. The leading ``:`` key prefix in the
# option dict tells NiceGUI's ``convertDynamicProperties`` to evaluate this
# string as a JS expression rather than embed it as a literal.
_X_AXIS_LABEL_FORMATTER_JS = "(value) => +value.toFixed(3)"


def _x_range_equal(
    a: tuple[float | None, float | None],
    b: tuple[float | None, float | None],
) -> bool:
    """Compare two ``(x_min, x_max)`` pairs with float tolerance and ``None`` support."""
    for av, bv in zip(a, b, strict=True):
        if av is None or bv is None:
            if av is not bv:
                return False
            continue
        if not (math.isfinite(av) and math.isfinite(bv)):
            return False
        if abs(av - bv) > _X_RANGE_ECHO_EPS:
            return False
    return True


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
        on_x_range_changed: OnEChartXRangeChanged | None = None,
        display_options: EChartDisplayOptions | None = None,
    ) -> None:
        """Create an empty ECharts widget.

        Args:
            on_x_range_selected: Optional callback for user brush-selected
                x-ranges (one-shot, used for ROI/event annotation flows).
            on_x_range_changed: Optional callback for continuous x-axis
                changes (ECharts datazoom). ``(None, None)`` means auto /
                reset to full extent.
            display_options: Optional initial display option set. Defaults to
                ``EChartDisplayOptions()`` (toolbar hidden).
        """
        self._line_data: EChartLineData | None = None
        self._x_range = EChartAxisRange()
        self._pending_x_range: tuple[float, float] | None = None
        self._selecting_x = False
        self._on_x_range_selected = on_x_range_selected
        self._on_x_range_changed = on_x_range_changed
        self._display_options = display_options or EChartDisplayOptions()
        # Last x-range applied via set_x_axis_limits / reset; used to suppress
        # the echo datazoom that ECharts fires when limits change programmatically.
        self._last_applied_x_range: tuple[float | None, float | None] | None = None
        self.events = EChartEventOverlayApi(self)

        initial_options = self._empty_options()
        self._apply_display_options_to_options(initial_options)
        self.container = ui.echart(initial_options)
        self.container.on("chart:datazoom", self._on_datazoom)
        self.container.on("chart:brushselected", self._on_brush_selected)
        self.container.on("chart:mouseup", self._on_mouseup)
        self.container.on("mouseup", self._on_mouseup)
        self.container.on("chart:dblclick", self._on_double_click)
        self.container.on("dblclick", self._on_double_click)

        self._ctx_menu: ui.context_menu | None = ui.context_menu()
        self._context_menu_builder = EChartWidgetContextMenu(get_widget=lambda: self)
        self.container.on("contextmenu", self._on_context_menu_event)

        # Start in "click+drag zooms the x-axis" mode so users get a chart
        # action by default. The toolbox itself stays hidden (per display
        # options) but the ``dataZoom`` feature is still in the options so the
        # ``dataZoomSelect`` cursor can be dispatched.
        self._activate_x_zoom_cursor()

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

        Records the applied pair so the subsequent ECharts datazoom echo does
        not re-fire ``on_x_range_changed``.
        """
        self._x_range = EChartAxisRange(x_min=x_min, x_max=x_max)
        self._last_applied_x_range = (x_min, x_max)
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
        # Restore the default x-axis zoom cursor so click+drag still zooms.
        self._activate_x_zoom_cursor()

    @property
    def display_options(self) -> EChartDisplayOptions:
        """Return mutable display options used by context-menu actions."""
        return self._display_options

    def set_toolbar_visible(self, visible: bool) -> None:
        """Show or hide the ECharts toolbox above the chart.

        The toolbox icons (dataZoom, restore, brush) are independent of the
        always-on click+drag x-zoom cursor; toggling them only affects the
        visible icon row.

        Args:
            visible: Whether the ECharts toolbox should be visible.
        """
        self._display_options.show_toolbar = bool(visible)
        self.apply()

    def set_hover_info_visible(self, visible: bool) -> None:
        """Show or hide the ECharts tooltip floating layer.

        Maps to ECharts' documented ``tooltip.show`` option
        (https://echarts.apache.org/en/option.html#tooltip.show). The tooltip
        ``trigger='axis'`` configuration is preserved; only the floating-layer
        visibility flips.

        Args:
            visible: Whether the tooltip floating layer should be visible.
        """
        self._display_options.show_hover_info = bool(visible)
        self.apply()

    async def copy_plot_to_clipboard(self) -> None:
        """Copy the current ECharts plot image to the active clipboard.

        Native NiceGUI desktop windows write PNG bytes via
        :func:`copy_png_bytes_to_native_clipboard`. Browser sessions use the
        browser ``Clipboard`` API through
        :func:`copy_echart_png_to_browser_clipboard`.
        """
        if self.container is None:
            ui.notify("No chart to copy.", type="warning")
            return

        try:
            native_cfg = getattr(app, "native", None)
            is_native_window = getattr(native_cfg, "main_window", None) is not None
            if is_native_window:
                png_bytes = await get_echart_png_bytes(self.container)
                copy_png_bytes_to_native_clipboard(png_bytes)
            else:
                await copy_echart_png_to_browser_clipboard(self.container)
            ui.notify("Chart copied to clipboard.", type="positive")
        except Exception as exc:
            logger.exception("Failed to copy ECharts plot to clipboard.")
            ui.notify(f"Copy failed: {exc}", type="negative")

    def _on_context_menu_event(self, _event) -> None:
        """Rebuild and open the ECharts widget right-click context menu."""
        if self._ctx_menu is None:
            return
        with self._ctx_menu.clear():
            self._context_menu_builder.build()
        self._ctx_menu.open()

    def _activate_x_zoom_cursor(self) -> None:
        """Arm ECharts' ``dataZoomSelect`` cursor (click+drag to zoom x-axis).

        ECharts requires the ``dataZoom`` toolbox feature to be present in the
        options for this action to take effect; that feature is always included
        by :func:`build_line_options` and :meth:`_empty_options`. Toolbox icon
        visibility is independent of cursor mode.
        """
        self.container.run_chart_method(
            "dispatchAction",
            {
                "type": "takeGlobalCursor",
                "key": "dataZoomSelect",
                "dataZoomSelectActive": True,
            },
        )

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
        self._apply_display_options_to_options(options)
        return options

    def _apply_display_options_to_options(self, options: dict[str, Any]) -> None:
        """Apply current display options to an ECharts option dictionary.

        Args:
            options: Mutable ECharts option dictionary built by
                :func:`build_line_options` or :meth:`_empty_options`.
        """
        toolbox = options.setdefault(
            "toolbox",
            {"feature": {"dataZoom": {"yAxisIndex": "none"}, "restore": {}, "brush": {"type": ["lineX", "clear"]}}},
        )
        if isinstance(toolbox, dict):
            toolbox["show"] = bool(self._display_options.show_toolbar)

        tooltip = options.setdefault("tooltip", {"trigger": "axis"})
        if isinstance(tooltip, dict):
            tooltip["show"] = bool(self._display_options.show_hover_info)

    def _on_datazoom(self, event: Any) -> None:
        """Forward ECharts dataZoom to ``on_x_range_changed`` (with echo dedup).

        Args:
            event: NiceGUI event arguments.
        """
        args = getattr(event, "args", event)
        logger.debug("datazoom event: %s", args)
        if self._on_x_range_changed is None:
            return
        new_range = self._extract_x_datazoom_range(args)
        if new_range is None:
            return
        if self._is_x_range_echo(new_range):
            return
        self._last_applied_x_range = new_range
        self._on_x_range_changed(new_range[0], new_range[1])

    def _is_x_range_echo(
        self, new_range: tuple[float | None, float | None]
    ) -> bool:
        """Return whether ``new_range`` matches the last applied limits.

        Args:
            new_range: Candidate ``(x_min, x_max)`` from a datazoom event.

        Returns:
            ``True`` when values match within float tolerance.
        """
        last = self._last_applied_x_range
        if last is None:
            return False
        return _x_range_equal(last, new_range)

    def _extract_x_datazoom_range(
        self, args: Any
    ) -> tuple[float | None, float | None] | None:
        """Extract an absolute ``(x_min, x_max)`` from an ECharts datazoom payload.

        ECharts datazoom events come in two flavors. ``startValue``/``endValue``
        are absolute axis values (preferred). ``start``/``end`` are percentages
        relative to the full extent; convert them using the current line data
        when available.

        Args:
            args: NiceGUI event args (dict-like, may also be wrapped under
                ``batch[0]``).

        Returns:
            ``(x_min, x_max)`` pair, or ``None`` when the payload cannot be
            interpreted.
        """
        payload: dict[str, Any] | None = None
        if isinstance(args, dict):
            payload = args
            batch = args.get("batch")
            if (
                payload.get("startValue") is None
                and payload.get("start") is None
                and isinstance(batch, list)
                and batch
                and isinstance(batch[0], dict)
            ):
                payload = batch[0]
        if not isinstance(payload, dict):
            return None

        start_value = payload.get("startValue")
        end_value = payload.get("endValue")
        if start_value is not None and end_value is not None:
            try:
                lo = float(start_value)
                hi = float(end_value)
            except (TypeError, ValueError):
                return None
            return (min(lo, hi), max(lo, hi))

        start_pct = payload.get("start")
        end_pct = payload.get("end")
        if start_pct is None or end_pct is None:
            return None
        if self._line_data is None or not self._line_data.x:
            return None
        try:
            lo_pct = float(start_pct)
            hi_pct = float(end_pct)
        except (TypeError, ValueError):
            return None
        if lo_pct <= 0.0 and hi_pct >= 100.0:
            return (None, None)
        full_lo = float(self._line_data.x[0])
        full_hi = float(self._line_data.x[-1])
        span = full_hi - full_lo
        if span <= 0.0:
            return None
        lo = full_lo + (min(lo_pct, hi_pct) / 100.0) * span
        hi = full_lo + (max(lo_pct, hi_pct) / 100.0) * span
        return (lo, hi)

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
        """Reset x-axis range on double-click and emit auto x-range.

        Args:
            event: NiceGUI double-click event.
        """
        _ = event
        self.cancel_select_x_range()
        self.reset_x_axis_limits()
        if self._on_x_range_changed is not None:
            self._on_x_range_changed(None, None)

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

        The ``toolbox`` block is present (with ``show=False``) so the
        ``dataZoomSelect`` cursor action can attach to it from the constructor
        even before line data is set.

        Returns:
            Empty ECharts option dictionary.
        """
        return {
            "animation": False,
            "animationDuration": 0,
            "animationDurationUpdate": 0,
            "grid": {"left": 10, "right": 10, "top": 10, "bottom": 10},
            "tooltip": {"trigger": "axis"},
            "xAxis": {
                "type": "value",
                "name": "",
                "min": None,
                "max": None,
                "axisLabel": {":formatter": _X_AXIS_LABEL_FORMATTER_JS},
            },
            "yAxis": {"type": "value", "name": ""},
            "series": [],
            "brush": {"toolbox": ["lineX", "clear"], "xAxisIndex": 0, "brushMode": "single"},
            "toolbox": {
                "show": False,
                "feature": {
                    "dataZoom": {"yAxisIndex": "none"},
                    "restore": {},
                    "brush": {"type": ["lineX", "clear"]},
                },
            },
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
    # ECharts' default ``type='value'`` axis applies a "nice ticks" algorithm
    # that rounds the auto-extent outward (e.g. [0, 9.4] -> [0, 10]). Pinning
    # ``min`` / ``max`` to the literal sentinels ``'dataMin'`` / ``'dataMax'``
    # disables the rounding while still letting ECharts pick tick stops. We
    # only do this for the x-axis; y-axis behavior is unchanged.
    x_min = x_range.x_min if x_range.x_min is not None else "dataMin"
    x_max = x_range.x_max if x_range.x_max is not None else "dataMax"
    return {
        "animation": False,
        "animationDuration": 0,
        "animationDurationUpdate": 0,
        # "grid": {"left": 55, "right": 20, "top": 24, "bottom": 45},
        "grid": {"left": 10, "right": 10, "top": 10, "bottom": 10},
        "tooltip": {"trigger": "axis"},
        "xAxis": {
            "type": "value",
            "name": line_data.x_label,
            "nameLocation": "middle",
            "nameGap": 28,
            "min": x_min,
            "max": x_max,
            "axisLabel": {":formatter": _X_AXIS_LABEL_FORMATTER_JS},
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
