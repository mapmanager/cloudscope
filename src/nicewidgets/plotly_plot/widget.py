"""Reusable NiceGUI Plotly plotting widget."""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from nicegui import core, ui

from nicewidgets.plotly_plot.context_menu import PlotlyPlotContextMenu
from nicewidgets.plotly_plot.context_menu_guards import pywebview_plotly_plot_context_menu_guard_js
from nicewidgets.plotly_plot.display_options import PlotlyPlotDisplayOptions
from nicewidgets.plotly_plot.models import (
    MeasurementChangeEvent,
    MeasurementLine,
    MeasurementPair,
    PlotlyAxisRange,
    PlotlyLineOrientation,
    PlotlyScatterData,
    PlotlySeriesMenuItem,
    PlotlyTraceData,
)
from nicewidgets.raster_viewer.frontend.plotly_clipboard import (
    copy_plotly_png_to_browser_clipboard,
    get_plotly_png_bytes,
)
from nicewidgets.utils.clipboard import copy_png_bytes_to_native_clipboard
from nicewidgets.utils.desktop import is_pywebview_desktop
from nicewidgets.plotly_theme import (
    PlotlyThemeName,
    apply_plotly_theme_to_layout,
    normalize_plotly_theme,
    theme_for_name,
)
from nicewidgets.utils.logging import get_logger

logger = get_logger(__name__)

OnPlotlyXRangeChanged = Callable[[float | None, float | None], None]
OnMeasurementChanged = Callable[[MeasurementChangeEvent], None]

_X_RANGE_ECHO_EPS = 1e-9


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


_SeriesKind = Literal["trace", "scatter"]
_MeasurementKind = Literal["line", "pair"]


@dataclass(slots=True)
class _SeriesRef:
    """Internal mapping from a public series name to a Plotly trace index."""

    name: str
    kind: _SeriesKind


@dataclass(slots=True)
class _ShapeRef:
    """Internal mapping from a Plotly shape index to a measurement object."""

    name: str
    kind: _MeasurementKind
    line_number: int


def _normalize_orientation(orientation: str) -> PlotlyLineOrientation:
    """Normalize supported orientation aliases.

    Args:
        orientation: Orientation string. Supported values are ``horizontal``,
            ``vertical``, ``h``, and ``v``.

    Returns:
        Normalized orientation literal.

    Raises:
        ValueError: If the orientation is not supported.
    """
    value = str(orientation).strip().lower()
    if value in {"horizontal", "h"}:
        return "horizontal"
    if value in {"vertical", "v"}:
        return "vertical"
    raise ValueError(f"orientation must be 'horizontal' or 'vertical', got {orientation!r}")


def _validate_unique_name(name: str, existing: object | None, *, label: str) -> str:
    """Validate a non-empty unique public name.

    Args:
        name: Candidate name.
        existing: Existing object for this name, if any.
        label: Human-readable label for validation errors.

    Returns:
        Stripped name.

    Raises:
        ValueError: If the name is empty or already exists.
    """
    clean = str(name).strip()
    if not clean:
        raise ValueError(f"{label} name must not be empty")
    if existing is not None:
        raise ValueError(f"{label} {clean!r} already exists")
    return clean


_PLOTLY_PLOT_LEGEND: dict[str, Any] = {
    "orientation": "h",
    "xanchor": "center",
    "x": 0.5,
    "yanchor": "top",
    "y": -0.15,
}

_PLOTLY_PLOT_MARGIN_WITH_AXIS_LABELS: dict[str, int] = {
    "l": 60,
    "r": 24,
    "t": 10,
    "b": 72,
}

_PLOTLY_PLOT_MARGIN_COMPACT: dict[str, int] = {
    "l": 8,
    "r": 8,
    "t": 8,
    "b": 72,
}


def build_plotly_figure_dict(
    *,
    data: list[dict[str, Any]] | None = None,
    x_label: str = "x",
    y_label: str = "y",
    x_range: PlotlyAxisRange | None = None,
    shapes: list[dict[str, Any]] | None = None,
    theme: PlotlyThemeName = "light",
    show_axis_labels: bool = False,
    show_plotly_toolbar: bool = False,
) -> dict[str, Any]:
    """Build a NiceGUI-compatible Plotly figure dictionary.

    Args:
        data: Plotly trace dictionaries.
        x_label: X-axis label.
        y_label: Y-axis label.
        x_range: Optional explicit x-axis range.
        shapes: Optional Plotly layout shapes.
        theme: Plotly light/dark layout theme name.
        show_axis_labels: Whether axis decorations are visible.
        show_plotly_toolbar: Whether Plotly's modebar is visible.

    Returns:
        Dictionary with Plotly ``data``, ``layout``, and ``config`` keys.
    """
    range_model = x_range or PlotlyAxisRange()
    axis_label_visible = bool(show_axis_labels)
    xaxis: dict[str, Any] = {
        "title": {"text": x_label if axis_label_visible else ""},
        "showticklabels": axis_label_visible,
        "ticks": "outside" if axis_label_visible else "",
        "showline": axis_label_visible,
        "zeroline": False,
        "showgrid": axis_label_visible,
    }
    if range_model.x_min is not None and range_model.x_max is not None:
        xaxis["range"] = [range_model.x_min, range_model.x_max]
        xaxis["autorange"] = False
    else:
        xaxis["autorange"] = True

    yaxis: dict[str, Any] = {
        "title": {"text": y_label if axis_label_visible else ""},
        "autorange": True,
        "showticklabels": axis_label_visible,
        "ticks": "outside" if axis_label_visible else "",
        "showline": axis_label_visible,
        "zeroline": False,
        "showgrid": axis_label_visible,
    }

    margin = (
        dict(_PLOTLY_PLOT_MARGIN_WITH_AXIS_LABELS)
        if axis_label_visible
        else dict(_PLOTLY_PLOT_MARGIN_COMPACT)
    )

    layout: dict[str, Any] = {
        "xaxis": xaxis,
        "yaxis": yaxis,
        "shapes": list(shapes or []),
        "dragmode": "zoom",
        "margin": margin,
        "showlegend": True,
        "legend": dict(_PLOTLY_PLOT_LEGEND),
        "uirevision": "nicewidgets-plotly-plot",
    }
    apply_plotly_theme_to_layout(layout, normalize_plotly_theme(theme))
    return {
        "data": list(data or []),
        "layout": layout,
        "config": {
            "editable": True,
            "scrollZoom": True,
            "displaylogo": False,
            "responsive": True,
            "displayModeBar": bool(show_plotly_toolbar),
            "edits": {
                "shapePosition": True,
                "titleText": False,
                "axisTitleText": False,
                "legendText": False,
                "legendPosition": False,
            },
        },
    }


class PlotlyPlotWidget:
    """Interactive Plotly plotting widget for NiceGUI.

    This widget provides a reusable plotting interface for scientific traces,
    sparse marker overlays, editable measurement lines, and x-axis range
    synchronization. It intentionally hides Plotly layout-shape details from
    parent applications such as CloudScope.
    """

    def __init__(
        self,
        *,
        x_label: str = "x",
        y_label: str = "y",
        theme: PlotlyThemeName = "light",
        on_x_range_changed: OnPlotlyXRangeChanged | None = None,
        on_measurement_changed: OnMeasurementChanged | None = None,
    ) -> None:
        """Create an empty Plotly widget.

        Args:
            x_label: X-axis label.
            y_label: Y-axis label.
            theme: Initial Plotly light/dark layout theme.
            on_x_range_changed: Optional callback invoked after the user changes
                the x-axis range by zooming, panning, or autoranging. ``(None,
                None)`` means Plotly returned to autorange.
            on_measurement_changed: Optional callback invoked after the user
                drags a measurement line.
        """
        self._x_label = str(x_label)
        self._y_label = str(y_label)
        self._theme = normalize_plotly_theme(theme)
        self._display_options = PlotlyPlotDisplayOptions(theme=self._theme)
        self._on_x_range_changed = on_x_range_changed
        self._on_measurement_changed = on_measurement_changed
        self._x_range = PlotlyAxisRange()
        self._series_menu_items: list[PlotlySeriesMenuItem] = []
        self._series_visibility: dict[str, bool] = {}
        self._figure = build_plotly_figure_dict(
            x_label=self._x_label,
            y_label=self._y_label,
            x_range=self._x_range,
            theme=self._theme,
            show_axis_labels=self._display_options.show_axis_labels,
            show_plotly_toolbar=self._display_options.show_plotly_toolbar,
        )
        self._series_order: list[_SeriesRef] = []
        self._traces: dict[str, PlotlyTraceData] = {}
        self._scatters: dict[str, PlotlyScatterData] = {}
        self._measurements: dict[str, MeasurementLine | MeasurementPair] = {}
        self._shape_refs: list[_ShapeRef] = []
        self._measurement_callbacks: dict[str, OnMeasurementChanged] = {}
        self._last_applied_x_range: tuple[float | None, float | None] | None = None
        self._ignore_relayout = False
        self._ctx_menu: ui.context_menu | None = None
        self._context_menu_builder: PlotlyPlotContextMenu | None = None

        self.container = ui.plotly(self._figure)
        self.container.on("plotly_relayout", self._on_plotly_relayout)
        self._ctx_menu = ui.context_menu()
        self._context_menu_builder = PlotlyPlotContextMenu(get_widget=lambda: self)
        self.container.on("contextmenu", self._on_context_menu_event)
        if is_pywebview_desktop():
            ui.timer(0.05, self._install_pywebview_context_menu_guards, once=True)

    @property
    def display_options(self) -> PlotlyPlotDisplayOptions:
        """Return mutable display options used by context-menu actions."""
        return self._display_options

    @property
    def series_menu_items(self) -> tuple[PlotlySeriesMenuItem, ...]:
        """Return registered trace/scatter context-menu items."""
        return tuple(self._series_menu_items)

    def register_series_menu_items(self, items: Sequence[PlotlySeriesMenuItem]) -> None:
        """Register trace/scatter items shown in the right-click context menu.

        Existing visibility choices are preserved for series names that were
        registered previously in this widget instance.

        Args:
            items: Menu item definitions keyed by stable series names.

        Returns:
            None.
        """
        self._series_menu_items = list(items)
        for item in items:
            if item.series_name not in self._series_visibility:
                self._series_visibility[item.series_name] = bool(item.default_visible)

    def is_series_visible(self, series_name: str) -> bool:
        """Return whether one registered or loaded series is visible.

        Args:
            series_name: Stable trace or scatter overlay name.

        Returns:
            True when the series should render in the plot.
        """
        clean = str(series_name).strip()
        if clean in self._series_visibility:
            return bool(self._series_visibility[clean])
        return True

    def set_series_visible(self, series_name: str, visible: bool) -> None:
        """Set visibility for one loaded trace or scatter overlay.

        Args:
            series_name: Existing trace or scatter overlay name.
            visible: Whether the series should be visible.

        Raises:
            KeyError: If the series does not exist in the current figure.
        """
        clean = str(series_name).strip()
        self._series_visibility[clean] = bool(visible)
        if clean in self._traces:
            current = self._traces[clean]
            data = PlotlyTraceData.from_sequences(
                name=clean,
                x=current.x,
                y=current.y,
                visible=bool(visible),
            )
            self._traces[clean] = data
            index = self._series_index(clean, "trace")
            trace = self._trace_to_plotly(data)
            self._figure["data"][index] = trace
            self._restyle_plotly_trace(index, trace)
            return
        if clean in self._scatters:
            current = self._scatters[clean]
            data = PlotlyScatterData.from_sequences(
                name=clean,
                x=current.x,
                y=current.y,
                visible=bool(visible),
            )
            self._scatters[clean] = data
            index = self._series_index(clean, "scatter")
            trace = self._scatter_to_plotly(data)
            self._figure["data"][index] = trace
            self._restyle_plotly_trace(index, trace)
            return
        raise KeyError(f"series {clean!r} does not exist")

    def toggle_series_visible(self, series_name: str) -> bool:
        """Toggle visibility for one registered trace or scatter overlay.

        Args:
            series_name: Stable trace or scatter overlay name.

        Returns:
            Visibility after the toggle.

        Raises:
            KeyError: If ``series_name`` is not a registered menu item.
        """
        clean = str(series_name).strip()
        if not any(item.series_name == clean for item in self._series_menu_items):
            raise KeyError(f"series {clean!r} is not registered in the context menu")
        new_visible = not self.is_series_visible(clean)
        if clean in self._traces or clean in self._scatters:
            self.set_series_visible(clean, new_visible)
        else:
            self._series_visibility[clean] = new_visible
        return new_visible

    def set_axis_labels_visible(self, visible: bool) -> None:
        """Show or hide axis title text, ticks, lines, and grid lines.

        Args:
            visible: Whether axis decorations should be visible.

        Returns:
            None.
        """
        self._display_options.show_axis_labels = bool(visible)
        self._sync_axis_labels_to_plotly_dict()
        self._sync_margins_to_plotly_dict()
        self._relayout_axis_labels_and_margins()

    def set_plotly_toolbar_visible(self, visible: bool) -> None:
        """Set Plotly modebar visibility.

        Args:
            visible: Whether Plotly's modebar should be visible.

        Returns:
            None.
        """
        self._display_options.show_plotly_toolbar = bool(visible)
        self._sync_plotly_config_to_plotly_dict()
        self._react_plotly_config()

    def set_hover_info_visible(self, visible: bool) -> None:
        """Set Plotly hover-info visibility for all plot traces.

        Args:
            visible: Whether hover info should be visible.

        Returns:
            None.
        """
        self._display_options.show_hover_info = bool(visible)
        self._sync_hover_info_to_plotly_dict()
        self._restyle_hover_info()

    async def copy_plot_to_clipboard(self) -> None:
        """Copy the current Plotly plot image to the active clipboard.

        Native desktop mode uses ``pyperclipimg``. Browser mode uses the
        Clipboard API with a Plotly PNG export.

        Returns:
            None.
        """
        try:
            if is_pywebview_desktop():
                png_bytes = await get_plotly_png_bytes(self.container)
                copy_png_bytes_to_native_clipboard(png_bytes)
            else:
                await copy_plotly_png_to_browser_clipboard(self.container)
            ui.notify("Plot copied to clipboard.", type="positive")
        except Exception as exc:
            logger.exception("Failed to copy Plotly plot to clipboard.")
            ui.notify(f"Copy failed: {exc}", type="negative")

    def _on_context_menu_event(self, _event: Any) -> None:
        """Rebuild and open the Plotly plot context menu."""
        if self._ctx_menu is None or self._context_menu_builder is None:
            return
        with self._ctx_menu.clear():
            self._context_menu_builder.build()
        self._ctx_menu.open()

    def _install_pywebview_context_menu_guards(self) -> None:
        """Install desktop-only capture listeners so secondary taps open the menu."""
        js = pywebview_plotly_plot_context_menu_guard_js(plot_id=self.container.id)
        try:
            self.container.client.run_javascript(js, timeout=2.0)
        except RuntimeError:
            logger.debug("Could not install pywebview context-menu guards; client unavailable.")

    @property
    def figure(self) -> dict[str, Any]:
        """Return the current Plotly figure dictionary."""
        return self._figure

    def add_trace(
        self,
        *,
        name: str,
        x: Sequence[float],
        y: Sequence[float],
        visible: bool = True,
    ) -> None:
        """Add a named continuous ``scattergl`` line trace.

        Args:
            name: Stable caller-defined trace name.
            x: X-axis values.
            y: Y-axis values.
            visible: Whether the trace should be visible.

        Raises:
            ValueError: If the name already exists or data are invalid.
        """
        clean = _validate_unique_name(name, self._traces.get(str(name).strip()), label="trace")
        data = PlotlyTraceData.from_sequences(name=clean, x=x, y=y, visible=visible)
        self._traces[clean] = data
        self._series_order.append(_SeriesRef(name=clean, kind="trace"))
        trace = self._trace_to_plotly(data)
        self._figure["data"].append(trace)
        self._add_plotly_trace(trace)

    def update_trace(
        self,
        *,
        name: str,
        x: Sequence[float],
        y: Sequence[float],
        visible: bool | None = None,
    ) -> None:
        """Replace data for an existing named continuous trace.

        Args:
            name: Existing trace name.
            x: Replacement X-axis values.
            y: Replacement Y-axis values.
            visible: Optional replacement visibility. When ``None``, the
                existing visibility is preserved.

        Raises:
            KeyError: If the trace does not exist.
            ValueError: If replacement data are invalid.
        """
        clean = str(name).strip()
        current = self._traces.get(clean)
        if current is None:
            raise KeyError(f"trace {clean!r} does not exist")
        data = PlotlyTraceData.from_sequences(
            name=clean,
            x=x,
            y=y,
            visible=current.visible if visible is None else visible,
        )
        self._traces[clean] = data
        index = self._series_index(clean, "trace")
        trace = self._trace_to_plotly(data)
        self._figure["data"][index] = trace
        self._restyle_plotly_trace(index, trace)

    def remove_trace(self, name: str) -> None:
        """Remove a named continuous trace.

        Args:
            name: Existing trace name.

        Raises:
            KeyError: If the trace does not exist.
        """
        clean = str(name).strip()
        index = self._series_index(clean, "trace")
        self._traces.pop(clean)
        self._series_order.pop(index)
        self._figure["data"].pop(index)
        self._delete_plotly_trace(index)

    def clear_traces(self) -> None:
        """Remove all continuous traces while preserving scatter overlays."""
        for name in list(self._traces):
            self.remove_trace(name)

    def plot_scatter(
        self,
        *,
        name: str,
        x: Sequence[float],
        y: Sequence[float],
        visible: bool = True,
    ) -> None:
        """Add a named sparse ``scattergl`` marker overlay.

        Args:
            name: Stable caller-defined scatter overlay name.
            x: X-axis values.
            y: Y-axis values.
            visible: Whether the scatter overlay should be visible.

        Raises:
            ValueError: If the name already exists or data are invalid.
        """
        clean = _validate_unique_name(
            name,
            self._scatters.get(str(name).strip()),
            label="scatter",
        )
        data = PlotlyScatterData.from_sequences(name=clean, x=x, y=y, visible=visible)
        self._scatters[clean] = data
        self._series_order.append(_SeriesRef(name=clean, kind="scatter"))
        trace = self._scatter_to_plotly(data)
        self._figure["data"].append(trace)
        self._add_plotly_trace(trace)

    def update_scatter(
        self,
        *,
        name: str,
        x: Sequence[float],
        y: Sequence[float],
        visible: bool | None = None,
    ) -> None:
        """Replace data for an existing named scatter overlay.

        Args:
            name: Existing scatter overlay name.
            x: Replacement X-axis values.
            y: Replacement Y-axis values.
            visible: Optional replacement visibility. When ``None``, the
                existing visibility is preserved.

        Raises:
            KeyError: If the scatter overlay does not exist.
            ValueError: If replacement data are invalid.
        """
        clean = str(name).strip()
        current = self._scatters.get(clean)
        if current is None:
            raise KeyError(f"scatter {clean!r} does not exist")
        data = PlotlyScatterData.from_sequences(
            name=clean,
            x=x,
            y=y,
            visible=current.visible if visible is None else visible,
        )
        self._scatters[clean] = data
        index = self._series_index(clean, "scatter")
        trace = self._scatter_to_plotly(data)
        self._figure["data"][index] = trace
        self._restyle_plotly_trace(index, trace)

    def remove_scatter(self, name: str) -> None:
        """Remove a named scatter overlay.

        Args:
            name: Existing scatter overlay name.

        Raises:
            KeyError: If the scatter overlay does not exist.
        """
        clean = str(name).strip()
        index = self._series_index(clean, "scatter")
        self._scatters.pop(clean)
        self._series_order.pop(index)
        self._figure["data"].pop(index)
        self._delete_plotly_trace(index)

    def clear_scatters(self) -> None:
        """Remove all scatter overlays while preserving continuous traces."""
        for name in list(self._scatters):
            self.remove_scatter(name)

    def set_series(
        self,
        *,
        traces: Sequence[PlotlyTraceData] = (),
        scatters: Sequence[PlotlyScatterData] = (),
    ) -> None:
        """Replace all continuous traces and scatter overlays in one browser update.

        Measurement lines and layout shapes are preserved. Existing incremental
        ``add_trace`` / ``plot_scatter`` callers remain available; prefer this
        method when rebuilding the full plot contents at once.

        Args:
            traces: Replacement continuous traces.
            scatters: Replacement scatter overlays.

        Returns:
            None.
        """
        self._traces = {}
        self._scatters = {}
        self._series_order = []
        plotly_data: list[dict[str, Any]] = []
        for data in traces:
            visible = self.is_series_visible(data.name)
            stored = PlotlyTraceData(
                name=data.name,
                x=data.x,
                y=data.y,
                visible=visible,
            )
            self._traces[stored.name] = stored
            self._series_order.append(_SeriesRef(name=stored.name, kind="trace"))
            plotly_data.append(self._trace_to_plotly(stored))
        for data in scatters:
            visible = self.is_series_visible(data.name)
            stored = PlotlyScatterData(
                name=data.name,
                x=data.x,
                y=data.y,
                visible=visible,
            )
            self._scatters[stored.name] = stored
            self._series_order.append(_SeriesRef(name=stored.name, kind="scatter"))
            plotly_data.append(self._scatter_to_plotly(stored))
        self._figure["data"] = plotly_data
        self._sync_hover_info_to_plotly_dict()
        self._push_series_data()

    def set_theme(self, theme: PlotlyThemeName) -> None:
        """Set the Plotly light/dark layout theme.

        Args:
            theme: Theme name, either ``'light'`` or ``'dark'``.

        Returns:
            None.
        """
        self._theme = normalize_plotly_theme(theme)
        self._display_options.theme = self._theme
        self._sync_theme_to_plotly_dict()
        self._relayout_theme()

    def set_dark_mode(self, enabled: bool) -> None:
        """Set the Plotly layout theme from a dark-mode flag.

        Args:
            enabled: Whether dark mode is enabled.

        Returns:
            None.
        """
        self.set_theme("dark" if enabled else "light")

    def set_x_axis_limits(self, x_min: float | None, x_max: float | None) -> None:
        """Set x-axis limits programmatically.

        Args:
            x_min: Minimum x-axis value, or ``None`` for automatic scaling.
            x_max: Maximum x-axis value, or ``None`` for automatic scaling.

        Raises:
            ValueError: If both bounds are set and ``x_min >= x_max``.
        """
        new_range = (x_min, x_max)
        if _x_range_equal(new_range, (self._x_range.x_min, self._x_range.x_max)):
            self._last_applied_x_range = new_range
            return
        self._x_range = PlotlyAxisRange(x_min=x_min, x_max=x_max)
        self._last_applied_x_range = new_range
        xaxis = self._figure["layout"].setdefault("xaxis", {})
        if x_min is None or x_max is None:
            xaxis.pop("range", None)
            xaxis["autorange"] = True
            self._relayout({"xaxis.autorange": True})
            return
        xaxis["range"] = [float(x_min), float(x_max)]
        xaxis["autorange"] = False
        self._relayout({"xaxis.range": [float(x_min), float(x_max)], "xaxis.autorange": False})

    def reset_x_axis_limits(self) -> None:
        """Reset the x-axis to automatic scaling."""
        self.set_x_axis_limits(None, None)

    def add_measurement_line(
        self,
        *,
        name: str,
        orientation: str,
        value: float,
        visible: bool = True,
        on_changed: OnMeasurementChanged | None = None,
    ) -> MeasurementLine:
        """Add a draggable horizontal or vertical measurement line.

        Args:
            name: Stable caller-defined measurement name.
            orientation: ``horizontal``/``h`` or ``vertical``/``v``.
            value: Initial line position in data coordinates.
            visible: Whether the line should be visible.
            on_changed: Optional per-measurement callback.

        Returns:
            Mutable measurement line object owned by the widget.

        Raises:
            ValueError: If the name already exists or orientation is invalid.
        """
        clean = _validate_unique_name(
            name,
            self._measurements.get(str(name).strip()),
            label="measurement",
        )
        normalized = _normalize_orientation(orientation)
        line = MeasurementLine(
            name=clean,
            orientation=normalized,
            position=float(value),
            visible=bool(visible),
        )
        self._measurements[clean] = line
        if on_changed is not None:
            self._measurement_callbacks[clean] = on_changed
        self._append_measurement_shape(clean, "line", 1, normalized, float(value), visible)
        self._push_shapes()
        return line

    def remove_measurement_line(self, name: str) -> None:
        """Remove a single-line measurement.

        Args:
            name: Existing single-line measurement name.

        Raises:
            KeyError: If the measurement does not exist.
            ValueError: If the measurement is a pair.
        """
        self._remove_measurement(name, expected_kind="line")

    def add_measurement_pair(
        self,
        *,
        name: str,
        orientation: str,
        value1: float,
        value2: float,
        visible: bool = True,
        on_changed: OnMeasurementChanged | None = None,
    ) -> MeasurementPair:
        """Add a draggable pair of horizontal or vertical measurement lines.

        Args:
            name: Stable caller-defined measurement-pair name.
            orientation: ``horizontal``/``h`` or ``vertical``/``v``.
            value1: Initial first-line position in data coordinates.
            value2: Initial second-line position in data coordinates.
            visible: Whether both lines should be visible.
            on_changed: Optional per-measurement callback.

        Returns:
            Mutable measurement pair object owned by the widget.

        Raises:
            ValueError: If the name already exists or orientation is invalid.
        """
        clean = _validate_unique_name(
            name,
            self._measurements.get(str(name).strip()),
            label="measurement",
        )
        normalized = _normalize_orientation(orientation)
        pair = MeasurementPair(
            name=clean,
            orientation=normalized,
            position1=float(value1),
            position2=float(value2),
            visible=bool(visible),
        )
        self._measurements[clean] = pair
        if on_changed is not None:
            self._measurement_callbacks[clean] = on_changed
        self._append_measurement_shape(clean, "pair", 1, normalized, float(value1), visible)
        self._append_measurement_shape(clean, "pair", 2, normalized, float(value2), visible)
        self._push_shapes()
        return pair

    def remove_measurement_pair(self, name: str) -> None:
        """Remove a paired-line measurement.

        Args:
            name: Existing measurement-pair name.

        Raises:
            KeyError: If the measurement does not exist.
            ValueError: If the measurement is a single line.
        """
        self._remove_measurement(name, expected_kind="pair")

    def _series_index(self, name: str, kind: _SeriesKind) -> int:
        """Return the current Plotly trace index for a named series."""
        for index, ref in enumerate(self._series_order):
            if ref.name == name and ref.kind == kind:
                return index
        raise KeyError(f"{kind} {name!r} does not exist")

    def _remove_measurement(self, name: str, *, expected_kind: _MeasurementKind) -> None:
        """Remove a measurement and all associated Plotly shapes."""
        clean = str(name).strip()
        measurement = self._measurements.get(clean)
        if measurement is None:
            raise KeyError(f"measurement {clean!r} does not exist")
        is_pair = isinstance(measurement, MeasurementPair)
        if expected_kind == "pair" and not is_pair:
            raise ValueError(f"measurement {clean!r} is not a pair")
        if expected_kind == "line" and is_pair:
            raise ValueError(f"measurement {clean!r} is not a single line")
        self._measurements.pop(clean)
        self._measurement_callbacks.pop(clean, None)
        keep_shapes: list[dict[str, Any]] = []
        keep_refs: list[_ShapeRef] = []
        for shape, ref in zip(self._shapes(), self._shape_refs, strict=True):
            if ref.name == clean:
                continue
            keep_shapes.append(shape)
            keep_refs.append(ref)
        self._figure["layout"]["shapes"] = keep_shapes
        self._shape_refs = keep_refs
        self._push_shapes()

    def _trace_to_plotly(self, data: PlotlyTraceData) -> dict[str, Any]:
        """Return a Plotly ``scattergl`` line trace dictionary."""
        hoverinfo = "all" if self._display_options.show_hover_info else "skip"
        return {
            "type": "scattergl",
            "mode": "lines",
            "name": data.name,
            "x": list(data.x),
            "y": list(data.y),
            "visible": True if data.visible else False,
            "hoverinfo": hoverinfo,
        }

    def _scatter_to_plotly(self, data: PlotlyScatterData) -> dict[str, Any]:
        """Return a Plotly ``scattergl`` marker trace dictionary."""
        hoverinfo = "all" if self._display_options.show_hover_info else "skip"
        return {
            "type": "scattergl",
            "mode": "markers",
            "name": data.name,
            "x": list(data.x),
            "y": list(data.y),
            "visible": True if data.visible else False,
            "hoverinfo": hoverinfo,
            "marker": {"size": 8},
        }

    def _append_measurement_shape(
        self,
        name: str,
        kind: _MeasurementKind,
        line_number: int,
        orientation: PlotlyLineOrientation,
        value: float,
        visible: bool,
    ) -> None:
        """Append one Plotly layout shape for a measurement line."""
        shape = self._line_shape(orientation=orientation, value=value, visible=visible)
        self._shapes().append(shape)
        self._shape_refs.append(_ShapeRef(name=name, kind=kind, line_number=line_number))

    def _line_shape(
        self,
        *,
        orientation: PlotlyLineOrientation,
        value: float,
        visible: bool,
    ) -> dict[str, Any]:
        """Build one editable Plotly line shape."""
        if orientation == "horizontal":
            return {
                "type": "line",
                "xref": "paper",
                "x0": 0,
                "x1": 1,
                "yref": "y",
                "y0": value,
                "y1": value,
                "visible": bool(visible),
                "editable": True,
                "line": {"width": 3, "dash": "dash"},
            }
        return {
            "type": "line",
            "xref": "x",
            "x0": value,
            "x1": value,
            "yref": "paper",
            "y0": 0,
            "y1": 1,
            "visible": bool(visible),
            "editable": True,
            "line": {"width": 3, "dash": "dash"},
        }

    def _shapes(self) -> list[dict[str, Any]]:
        """Return the mutable layout shape list."""
        layout = self._figure.setdefault("layout", {})
        shapes = layout.setdefault("shapes", [])
        if not isinstance(shapes, list):
            raise TypeError("Plotly layout.shapes must be a list")
        return shapes

    def _on_plotly_relayout(self, event: Any) -> None:
        """Handle Plotly relayout events from user zooms and shape drags."""
        if self._ignore_relayout:
            return
        args = getattr(event, "args", None)
        if not isinstance(args, dict):
            return
        self._sync_shape_edits(args)
        self._emit_x_range_if_needed(args)

    def _emit_x_range_if_needed(self, args: dict[str, Any]) -> None:
        """Emit x-range callback for user axis range changes."""
        parsed = self._parse_x_range_event(args)
        if parsed is None:
            return
        if self._is_x_range_echo(parsed):
            return
        xaxis = self._figure["layout"].setdefault("xaxis", {})
        x_min, x_max = parsed
        if x_min is None or x_max is None:
            xaxis.pop("range", None)
            xaxis["autorange"] = True
        else:
            xaxis["range"] = [x_min, x_max]
            xaxis["autorange"] = False
        if self._on_x_range_changed is not None:
            self._on_x_range_changed(x_min, x_max)
        self._last_applied_x_range = parsed

    def _is_x_range_echo(
        self, new_range: tuple[float | None, float | None]
    ) -> bool:
        """Return whether ``new_range`` echoes the last programmatic apply.

        Args:
            new_range: Candidate ``(x_min, x_max)`` from a relayout event.

        Returns:
            ``True`` when both values match the last applied pair within
            tolerance.
        """
        last = self._last_applied_x_range
        if last is None:
            return False
        return _x_range_equal(last, new_range)

    @staticmethod
    def _parse_x_range_event(args: dict[str, Any]) -> tuple[float | None, float | None] | None:
        """Parse a Plotly relayout payload for x-axis range changes.

        Args:
            args: Plotly relayout event payload.

        Returns:
            ``(x_min, x_max)``, ``(None, None)`` for autorange, or ``None``
            when the event does not describe an x-axis range change.
        """
        if args.get("xaxis.autorange") is True:
            return (None, None)
        if "xaxis.range" in args:
            value = args["xaxis.range"]
            if isinstance(value, Sequence) and len(value) == 2:
                return (float(value[0]), float(value[1]))
        if "xaxis.range[0]" in args and "xaxis.range[1]" in args:
            return (float(args["xaxis.range[0]"]), float(args["xaxis.range[1]"]))
        return None

    def _sync_shape_edits(self, args: dict[str, Any]) -> None:
        """Mirror user-dragged shape coordinates and emit measurement callbacks."""
        changed_indices = self._shape_indices_from_relayout(args)
        if not changed_indices:
            return
        shapes = self._shapes()
        for index in changed_indices:
            if index >= len(shapes) or index >= len(self._shape_refs):
                continue
            shape = shapes[index]
            self._apply_shape_args(shape, index, args)
            ref = self._shape_refs[index]
            measurement = self._measurements.get(ref.name)
            if measurement is None:
                continue
            position = self._shape_position(shape, measurement.orientation)
            if isinstance(measurement, MeasurementLine):
                measurement.position = position
                event = MeasurementChangeEvent(
                    name=measurement.name,
                    kind="line",
                    orientation=measurement.orientation,
                    position=position,
                )
            else:
                if ref.line_number == 1:
                    measurement.position1 = position
                else:
                    measurement.position2 = position
                event = MeasurementChangeEvent(
                    name=measurement.name,
                    kind="pair",
                    orientation=measurement.orientation,
                    position=position,
                    position1=measurement.position1,
                    position2=measurement.position2,
                    delta=measurement.delta,
                )
            self._emit_measurement_changed(event)

    @staticmethod
    def _shape_indices_from_relayout(args: dict[str, Any]) -> set[int]:
        """Return shape indices touched by a relayout payload."""
        indices: set[int] = set()
        for key in args:
            if key.startswith("shapes["):
                close = key.find("]")
                if close > len("shapes["):
                    try:
                        indices.add(int(key[len("shapes[") : close]))
                    except ValueError:
                        continue
        if not indices and isinstance(args.get("shapes"), list):
            indices.update(range(len(args["shapes"])))
        return indices

    @staticmethod
    def _apply_shape_args(shape: dict[str, Any], index: int, args: dict[str, Any]) -> None:
        """Apply relayout payload shape keys to one local shape dictionary."""
        full_shapes = args.get("shapes")
        if isinstance(full_shapes, list) and index < len(full_shapes) and isinstance(full_shapes[index], dict):
            shape.clear()
            shape.update(full_shapes[index])
            return
        prefix = f"shapes[{index}]."
        for key, value in args.items():
            if key.startswith(prefix):
                shape[key[len(prefix) :]] = value

    @staticmethod
    def _shape_position(shape: dict[str, Any], orientation: PlotlyLineOrientation) -> float:
        """Return the data-coordinate position for a Plotly line shape."""
        if orientation == "horizontal":
            return float(shape.get("y0", shape.get("y1")))
        return float(shape.get("x0", shape.get("x1")))

    def _emit_measurement_changed(self, event: MeasurementChangeEvent) -> None:
        """Invoke global and per-measurement callbacks for a measurement change."""
        callback = self._measurement_callbacks.get(event.name)
        if callback is not None:
            callback(event)
        if self._on_measurement_changed is not None:
            self._on_measurement_changed(event)

    def _js_plotly_graph_div(self) -> str:
        """Return JavaScript that resolves this NiceGUI Plotly graph div."""
        plot_id = self.container.id
        return f"""const host = getElement({plot_id}).$el;
if (!host) return;
const plotDiv = host.querySelector('.js-plotly-plot') || host;
if (!plotDiv || !plotDiv.data) return;
"""

    def _add_plotly_trace(self, trace: dict[str, Any]) -> None:
        """Push a newly added trace to the browser."""
        js = f"""
{self._js_plotly_graph_div()}
Plotly.addTraces(plotDiv, [{json.dumps(trace)}]);
"""
        self._run_plotly_javascript(js)

    def _restyle_plotly_trace(self, index: int, trace: dict[str, Any]) -> None:
        """Push trace replacement values to the browser with ``Plotly.restyle``."""
        restyle = {key: [value] for key, value in trace.items() if key != "type"}
        js = f"""
{self._js_plotly_graph_div()}
Plotly.restyle(plotDiv, {json.dumps(restyle)}, [{index}]);
"""
        self._run_plotly_javascript(js)

    def _delete_plotly_trace(self, index: int) -> None:
        """Remove one Plotly trace from the browser."""
        js = f"""
{self._js_plotly_graph_div()}
Plotly.deleteTraces(plotDiv, [{index}]);
"""
        self._run_plotly_javascript(js)

    def _relayout(self, payload: dict[str, Any]) -> None:
        """Push a Plotly relayout payload to the browser."""
        js = f"""
{self._js_plotly_graph_div()}
Plotly.relayout(plotDiv, {json.dumps(payload)});
"""
        self._run_plotly_javascript(js)

    def _push_shapes(self) -> None:
        """Push the current layout shapes to the browser."""
        self._relayout({"shapes": self._shapes()})

    def _sync_theme_to_plotly_dict(self) -> None:
        """Synchronize the selected light/dark theme into the local figure dict."""
        layout = self._figure.setdefault("layout", {})
        if not isinstance(layout, dict):
            layout = {}
            self._figure["layout"] = layout
        apply_plotly_theme_to_layout(layout, self._theme)

    def _sync_axis_labels_to_plotly_dict(self) -> None:
        """Synchronize axis decoration visibility into the local figure dict."""
        layout = self._figure.setdefault("layout", {})
        visible = bool(self._display_options.show_axis_labels)
        for axis_name, label_text in (("xaxis", self._x_label), ("yaxis", self._y_label)):
            axis = layout.setdefault(axis_name, {})
            if not isinstance(axis, dict):
                axis = {}
                layout[axis_name] = axis
            title = axis.setdefault("title", {})
            if not isinstance(title, dict):
                title = {}
                axis["title"] = title
            title["text"] = label_text if visible else ""
            axis["showticklabels"] = visible
            axis["ticks"] = "outside" if visible else ""
            axis["showline"] = visible
            axis["zeroline"] = False
            axis["showgrid"] = visible

    def _sync_margins_to_plotly_dict(self) -> None:
        """Synchronize layout margins with axis-label visibility."""
        layout = self._figure.setdefault("layout", {})
        margin = (
            dict(_PLOTLY_PLOT_MARGIN_WITH_AXIS_LABELS)
            if self._display_options.show_axis_labels
            else dict(_PLOTLY_PLOT_MARGIN_COMPACT)
        )
        layout["margin"] = margin

    def _sync_plotly_config_to_plotly_dict(self) -> None:
        """Synchronize Plotly config options into the local figure dict."""
        config = self._figure.setdefault("config", {})
        if not isinstance(config, dict):
            config = {}
            self._figure["config"] = config
        config["displayModeBar"] = bool(self._display_options.show_plotly_toolbar)
        config["editable"] = True
        config["edits"] = {
            "shapePosition": True,
            "titleText": False,
            "axisTitleText": False,
            "legendText": False,
            "legendPosition": False,
        }

    def _sync_hover_info_to_plotly_dict(self) -> None:
        """Synchronize hover-info visibility into all trace dictionaries."""
        hoverinfo = "all" if self._display_options.show_hover_info else "skip"
        for trace in self._figure.get("data", []):
            if isinstance(trace, dict):
                trace["hoverinfo"] = hoverinfo

    def _restyle_hover_info(self) -> None:
        """Push hover-info changes to the browser via ``Plotly.restyle``."""
        if not self._figure.get("data"):
            return
        hoverinfo = "all" if self._display_options.show_hover_info else "skip"
        indices = list(range(len(self._figure["data"])))
        js = f"""
{self._js_plotly_graph_div()}
Plotly.restyle(plotDiv, {{hoverinfo: {json.dumps(hoverinfo)}}}, {json.dumps(indices)});
"""
        self._run_plotly_javascript(js)

    def _react_plotly_config(self) -> None:
        """Push Plotly config changes to the browser."""
        config = self._figure.get("config", {})
        js = f"""
{self._js_plotly_graph_div()}
Plotly.react(plotDiv, plotDiv.data, plotDiv.layout, {json.dumps(config)});
"""
        self._run_plotly_javascript(js)

    def _relayout_axis_labels_and_margins(self) -> None:
        """Push axis-label and margin layout changes to the browser."""
        layout = self._figure.get("layout", {})
        relayout: dict[str, Any] = {"margin": layout.get("margin", {})}
        for axis_name in ("xaxis", "yaxis"):
            axis = layout.get(axis_name, {})
            if not isinstance(axis, dict):
                continue
            title = axis.get("title", {})
            if isinstance(title, dict):
                relayout[f"{axis_name}.title.text"] = title.get("text", "")
            relayout[f"{axis_name}.showticklabels"] = axis.get("showticklabels", False)
            relayout[f"{axis_name}.ticks"] = axis.get("ticks", "")
            relayout[f"{axis_name}.showline"] = axis.get("showline", False)
            relayout[f"{axis_name}.zeroline"] = axis.get("zeroline", False)
            relayout[f"{axis_name}.showgrid"] = axis.get("showgrid", False)
        self._relayout(relayout)

    def _relayout_theme(self) -> None:
        """Push light/dark theme layout properties to the browser."""
        layout = self._figure.setdefault("layout", {})
        if not isinstance(layout, dict):
            return
        theme = theme_for_name(self._theme)
        relayout: dict[str, Any] = {
            "paper_bgcolor": theme.paper_bgcolor,
            "plot_bgcolor": theme.plot_bgcolor,
            "font.color": theme.font_color,
        }
        for axis_name in ("xaxis", "yaxis"):
            axis = layout.get(axis_name, {})
            if not isinstance(axis, dict):
                continue
            relayout[f"{axis_name}.color"] = axis.get("color", theme.axis_color)
            relayout[f"{axis_name}.linecolor"] = axis.get("linecolor", theme.axis_color)
            relayout[f"{axis_name}.tickcolor"] = axis.get("tickcolor", theme.axis_color)
            relayout[f"{axis_name}.gridcolor"] = axis.get("gridcolor", theme.grid_color)
            relayout[f"{axis_name}.zerolinecolor"] = axis.get("zerolinecolor", theme.zero_line_color)
        self._relayout(relayout)

    def _push_series_data(self) -> None:
        """Push the full trace/scatter data array to the browser in one update."""
        data_json = json.dumps(self._figure["data"])
        js = f"""
{self._js_plotly_graph_div()}
const newData = {data_json};
const oldCount = plotDiv.data ? plotDiv.data.length : 0;
if (oldCount > 0) {{
  Plotly.deleteTraces(plotDiv, [...Array(oldCount).keys()]);
}}
if (newData.length > 0) {{
  Plotly.addTraces(plotDiv, newData);
}}
"""
        self._run_plotly_javascript(js)

    def _run_plotly_javascript(self, js: str) -> None:
        """Run Plotly JavaScript while suppressing programmatic relayout echo.

        NiceGUI cannot schedule browser JavaScript until its event loop exists.
        Demo scripts commonly populate widgets before ``ui.run()`` starts that
        loop, so the local figure dictionary remains the source of truth and the
        browser receives the complete state during initial rendering. Incremental
        JavaScript pushes are only needed after the client is live.

        Args:
            js: JavaScript source to execute in the owning browser client.
        """
        if core.loop is None and self.container.client.__class__.__module__.startswith("nicegui"):
            logger.debug("Skipping Plotly JavaScript update before NiceGUI loop starts.")
            return

        self._ignore_relayout = True
        try:
            self.container.client.run_javascript(js, timeout=2.0)
        except RuntimeError:
            logger.warning("Could not run Plotly JavaScript; browser client unavailable.")
        except AssertionError:
            logger.debug("Skipping Plotly JavaScript update before NiceGUI loop starts.")
        except Exception:
            logger.exception("Failed to run Plotly JavaScript update.")
        finally:
            self._ignore_relayout = False
