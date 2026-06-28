"""Tests for the reusable PlotlyPlotWidget public API helpers."""

from __future__ import annotations

from typing import Any

import pytest

from nicewidgets.plotly_plot.models import (
    MeasurementChangeEvent,
    PlotlyAxisRange,
    PlotlyScatterData,
    PlotlyTraceData,
)
from nicewidgets.plotly_plot.widget import PlotlyPlotWidget, build_plotly_figure_dict


class _FakeClient:
    """Capture JavaScript pushed by the widget during tests."""

    def __init__(self) -> None:
        """Create an empty JavaScript call recorder."""
        self.calls: list[str] = []

    def run_javascript(self, js: str, *, timeout: float | None = None) -> None:
        """Record JavaScript instead of sending it to a browser.

        Args:
            js: JavaScript source.
            timeout: Optional NiceGUI timeout argument.
        """
        self.calls.append(js)


class _FakePlotlyElement:
    """Small stand-in for NiceGUI's Plotly element."""

    def __init__(self, figure: dict[str, Any]) -> None:
        """Create a fake element.

        Args:
            figure: Figure dictionary passed to ``ui.plotly``.
        """
        self.figure = figure
        self.id = 123
        self.client = _FakeClient()
        self.handlers: dict[str, Any] = {}

    def on(self, event_name: str, handler: Any) -> None:
        """Record event handlers registered by the widget.

        Args:
            event_name: NiceGUI event name.
            handler: Callback registered for the event.
        """
        self.handlers[event_name] = handler


class _RelayoutEvent:
    """Fake NiceGUI event object with Plotly relayout args."""

    def __init__(self, args: dict[str, Any]) -> None:
        """Create a fake relayout event.

        Args:
            args: Plotly relayout payload.
        """
        self.args = args


@pytest.fixture
def fake_plotly(monkeypatch: pytest.MonkeyPatch) -> list[_FakePlotlyElement]:
    """Patch ``ui.plotly`` and return created fake elements."""
    created: list[_FakePlotlyElement] = []

    def factory(figure: dict[str, Any]) -> _FakePlotlyElement:
        element = _FakePlotlyElement(figure)
        created.append(element)
        return element

    monkeypatch.setattr("nicewidgets.plotly_plot.widget.ui.plotly", factory)
    return created


def test_trace_data_validates_lengths() -> None:
    """Continuous traces should reject mismatched x/y lengths."""
    with pytest.raises(ValueError):
        PlotlyTraceData.from_sequences(name="trace", x=[0.0, 1.0], y=[1.0])


def test_scatter_data_validates_lengths() -> None:
    """Scatter overlays should reject mismatched x/y lengths."""
    with pytest.raises(ValueError):
        PlotlyScatterData.from_sequences(name="peaks", x=[0.0], y=[1.0, 2.0])


def test_axis_range_validates_bounds() -> None:
    """Axis ranges should reject partial or inverted bounds."""
    with pytest.raises(ValueError):
        PlotlyAxisRange(x_min=2.0, x_max=1.0)
    with pytest.raises(ValueError):
        PlotlyAxisRange(x_min=2.0, x_max=None)


def test_build_plotly_figure_dict_includes_config_and_shapes() -> None:
    """Figure dict should include NiceGUI-compatible Plotly config."""
    figure = build_plotly_figure_dict(
        title="demo",
        x_label="time",
        y_label="df/f0",
        x_range=PlotlyAxisRange(0.0, 1.0),
        shapes=[{"type": "line"}],
    )

    assert figure["layout"]["title"]["text"] == "demo"
    assert figure["layout"]["xaxis"]["range"] == [0.0, 1.0]
    assert figure["layout"]["xaxis"]["autorange"] is False
    assert figure["layout"]["shapes"] == [{"type": "line"}]
    assert figure["config"]["editable"] is True
    assert figure["config"]["scrollZoom"] is True


def test_widget_add_update_remove_trace(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Named continuous trace API should keep the figure dict synchronized."""
    widget = PlotlyPlotWidget(title="Trace test")

    widget.add_trace(name="df/f0", x=[0.0, 1.0], y=[2.0, 3.0])
    assert widget.figure["data"][0]["name"] == "df/f0"
    assert widget.figure["data"][0]["mode"] == "lines"

    widget.update_trace(name="df/f0", x=[0.0, 2.0], y=[4.0, 5.0])
    assert widget.figure["data"][0]["x"] == [0.0, 2.0]
    assert "Plotly.restyle" in fake_plotly[0].client.calls[-1]

    widget.remove_trace("df/f0")
    assert widget.figure["data"] == []
    assert "Plotly.deleteTraces" in fake_plotly[0].client.calls[-1]


def test_widget_add_update_remove_scatter(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Named scatter overlay API should keep the figure dict synchronized."""
    widget = PlotlyPlotWidget(title="Scatter test")

    widget.plot_scatter(name="peaks", x=[0.5], y=[1.5])
    assert widget.figure["data"][0]["name"] == "peaks"
    assert widget.figure["data"][0]["mode"] == "markers"

    widget.update_scatter(name="peaks", x=[0.25, 0.75], y=[1.0, 2.0])
    assert widget.figure["data"][0]["x"] == [0.25, 0.75]
    assert "Plotly.restyle" in fake_plotly[0].client.calls[-1]

    widget.remove_scatter("peaks")
    assert widget.figure["data"] == []
    assert "Plotly.deleteTraces" in fake_plotly[0].client.calls[-1]


def test_widget_set_and_reset_x_axis_limits(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Programmatic x-axis range API should update layout and use relayout."""
    widget = PlotlyPlotWidget()

    widget.set_x_axis_limits(1.0, 2.0)
    assert widget.figure["layout"]["xaxis"]["range"] == [1.0, 2.0]
    assert widget.figure["layout"]["xaxis"]["autorange"] is False
    assert "Plotly.relayout" in fake_plotly[0].client.calls[-1]

    widget.reset_x_axis_limits()
    assert "range" not in widget.figure["layout"]["xaxis"]
    assert widget.figure["layout"]["xaxis"]["autorange"] is True


def test_widget_emits_user_x_range_callback(fake_plotly: list[_FakePlotlyElement]) -> None:
    """User relayout x-range events should notify the parent callback."""
    ranges: list[tuple[float | None, float | None]] = []
    widget = PlotlyPlotWidget(on_x_range_changed=lambda x0, x1: ranges.append((x0, x1)))

    widget._on_plotly_relayout(_RelayoutEvent({"xaxis.range[0]": 2.0, "xaxis.range[1]": 5.0}))
    widget._on_plotly_relayout(_RelayoutEvent({"xaxis.autorange": True}))

    assert ranges == [(2.0, 5.0), (None, None)]
    assert widget.figure["layout"]["xaxis"]["autorange"] is True


def test_measurement_line_drag_updates_state_and_callbacks(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Dragged single measurement lines should update position and emit payloads."""
    events: list[MeasurementChangeEvent] = []
    widget = PlotlyPlotWidget(on_measurement_changed=events.append)
    line = widget.add_measurement_line(name="manual-f0", orientation="horizontal", value=10.0)

    widget._on_plotly_relayout(_RelayoutEvent({"shapes[0].y0": 12.5, "shapes[0].y1": 12.5}))

    assert line.position == 12.5
    assert events[-1].name == "manual-f0"
    assert events[-1].kind == "line"
    assert events[-1].orientation == "horizontal"
    assert events[-1].position == 12.5


def test_measurement_pair_drag_updates_delta(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Dragged pair lines should update positions and report absolute delta."""
    events: list[MeasurementChangeEvent] = []
    widget = PlotlyPlotWidget(on_measurement_changed=events.append)
    pair = widget.add_measurement_pair(
        name="window",
        orientation="vertical",
        value1=1.0,
        value2=4.0,
    )

    widget._on_plotly_relayout(_RelayoutEvent({"shapes[1].x0": 6.0, "shapes[1].x1": 6.0}))

    assert pair.position1 == 1.0
    assert pair.position2 == 6.0
    assert pair.delta == 5.0
    assert events[-1].kind == "pair"
    assert events[-1].position1 == 1.0
    assert events[-1].position2 == 6.0
    assert events[-1].delta == 5.0
