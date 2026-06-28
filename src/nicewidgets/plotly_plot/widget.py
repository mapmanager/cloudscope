"""Reusable NiceGUI Plotly plotting widget."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from nicegui import core, ui

from nicewidgets.plotly_plot.models import (
    MeasurementChangeEvent,
    MeasurementLine,
    MeasurementPair,
    PlotlyAxisRange,
    PlotlyLineOrientation,
    PlotlyScatterData,
    PlotlyTraceData,
)
from nicewidgets.utils.logging import get_logger

logger = get_logger(__name__)

OnPlotlyXRangeChanged = Callable[[float | None, float | None], None]
OnMeasurementChanged = Callable[[MeasurementChangeEvent], None]

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


def build_plotly_figure_dict(
    *,
    data: list[dict[str, Any]] | None = None,
    title: str | None = None,
    x_label: str = "x",
    y_label: str = "y",
    x_range: PlotlyAxisRange | None = None,
    shapes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a NiceGUI-compatible Plotly figure dictionary.

    Args:
        data: Plotly trace dictionaries.
        title: Optional plot title.
        x_label: X-axis label.
        y_label: Y-axis label.
        x_range: Optional explicit x-axis range.
        shapes: Optional Plotly layout shapes.

    Returns:
        Dictionary with Plotly ``data``, ``layout``, and ``config`` keys.
    """
    range_model = x_range or PlotlyAxisRange()
    xaxis: dict[str, Any] = {"title": {"text": x_label}}
    if range_model.x_min is not None and range_model.x_max is not None:
        xaxis["range"] = [range_model.x_min, range_model.x_max]
        xaxis["autorange"] = False
    else:
        xaxis["autorange"] = True

    layout: dict[str, Any] = {
        "title": {"text": title or ""},
        "xaxis": xaxis,
        "yaxis": {"title": {"text": y_label}, "autorange": True},
        "shapes": list(shapes or []),
        "dragmode": "zoom",
        "margin": {"l": 60, "r": 24, "t": 48, "b": 52},
        "showlegend": True,
        "uirevision": "nicewidgets-plotly-plot",
    }
    return {
        "data": list(data or []),
        "layout": layout,
        "config": {
            "editable": True,
            "scrollZoom": True,
            "displaylogo": False,
            "responsive": True,
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
        title: str | None = None,
        x_label: str = "x",
        y_label: str = "y",
        on_x_range_changed: OnPlotlyXRangeChanged | None = None,
        on_measurement_changed: OnMeasurementChanged | None = None,
    ) -> None:
        """Create an empty Plotly widget.

        Args:
            title: Optional plot title.
            x_label: X-axis label.
            y_label: Y-axis label.
            on_x_range_changed: Optional callback invoked after the user changes
                the x-axis range by zooming, panning, or autoranging. ``(None,
                None)`` means Plotly returned to autorange.
            on_measurement_changed: Optional callback invoked after the user
                drags a measurement line.
        """
        self._title = title
        self._x_label = str(x_label)
        self._y_label = str(y_label)
        self._on_x_range_changed = on_x_range_changed
        self._on_measurement_changed = on_measurement_changed
        self._x_range = PlotlyAxisRange()
        self._figure = build_plotly_figure_dict(
            title=title,
            x_label=self._x_label,
            y_label=self._y_label,
            x_range=self._x_range,
        )
        self._series_order: list[_SeriesRef] = []
        self._traces: dict[str, PlotlyTraceData] = {}
        self._scatters: dict[str, PlotlyScatterData] = {}
        self._measurements: dict[str, MeasurementLine | MeasurementPair] = {}
        self._shape_refs: list[_ShapeRef] = []
        self._measurement_callbacks: dict[str, OnMeasurementChanged] = {}
        self._last_applied_x_range: tuple[float | None, float | None] | None = None
        self._ignore_relayout = False

        self.container = ui.plotly(self._figure)
        self.container.on("plotly_relayout", self._on_plotly_relayout)

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

    def set_x_axis_limits(self, x_min: float | None, x_max: float | None) -> None:
        """Set x-axis limits programmatically.

        Args:
            x_min: Minimum x-axis value, or ``None`` for automatic scaling.
            x_max: Maximum x-axis value, or ``None`` for automatic scaling.

        Raises:
            ValueError: If both bounds are set and ``x_min >= x_max``.
        """
        self._x_range = PlotlyAxisRange(x_min=x_min, x_max=x_max)
        self._last_applied_x_range = (x_min, x_max)
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
        return {
            "type": "scattergl",
            "mode": "lines",
            "name": data.name,
            "x": list(data.x),
            "y": list(data.y),
            "visible": True if data.visible else "legendonly",
        }

    def _scatter_to_plotly(self, data: PlotlyScatterData) -> dict[str, Any]:
        """Return a Plotly ``scattergl`` marker trace dictionary."""
        return {
            "type": "scattergl",
            "mode": "markers",
            "name": data.name,
            "x": list(data.x),
            "y": list(data.y),
            "visible": True if data.visible else "legendonly",
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
        if self._last_applied_x_range == parsed:
            self._last_applied_x_range = None
            return
        self._last_applied_x_range = None
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
