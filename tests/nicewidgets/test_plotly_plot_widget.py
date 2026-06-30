"""Tests for the reusable PlotlyPlotWidget public API helpers."""

from __future__ import annotations

from typing import Any

import pytest

from nicewidgets.plotly_plot.models import (
    MeasurementChangeEvent,
    PlotlyAxisRange,
    PlotlyScatterData,
    PlotlySeriesMenuItem,
    PlotlyTraceData,
)
from nicewidgets.plotly_plot.event_overlay import PlotlyEventOverlay
from nicewidgets.plotly_plot.widget import (
    PlotlyPlotWidget,
    build_plotly_figure_dict,
    extract_rect_selection_x_range_from_relayout,
    resolve_plot_layout_margins,
)


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

    def classes(self, *_args: str, **_kwargs: Any) -> _FakePlotlyElement:
        """Return self for chaining."""
        return self

    def on(self, event_name: str, handler: Any) -> None:
        """Record event handlers registered by the widget.

        Args:
            event_name: NiceGUI event name.
            handler: Callback registered for the event.
        """
        self.handlers[event_name] = handler


class _FakeUiElement:
    """Small stand-in for generic NiceGUI container elements."""

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.visible = True

    def classes(self, *_args: str, **_kwargs: Any) -> _FakeUiElement:
        """Return self for chaining."""
        return self

    def set_visibility(self, visible: bool) -> None:
        """Record visibility changes."""
        self.visible = bool(visible)

    def __enter__(self) -> _FakeUiElement:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None


class _FakeUiLabel:
    """Small stand-in for NiceGUI labels."""

    def __init__(self, text: str = "") -> None:
        self.text = text

    def classes(self, *_args: str, **_kwargs: Any) -> _FakeUiLabel:
        """Return self for chaining."""
        return self


@pytest.fixture
def fake_plotly(monkeypatch: pytest.MonkeyPatch) -> list[_FakePlotlyElement]:
    """Patch NiceGUI UI factories and return created fake Plotly elements."""
    created: list[_FakePlotlyElement] = []

    def plotly_factory(figure: dict[str, Any]) -> _FakePlotlyElement:
        element = _FakePlotlyElement(figure)
        created.append(element)
        return element

    monkeypatch.setattr("nicewidgets.plotly_plot.widget.ui.plotly", plotly_factory)
    monkeypatch.setattr("nicewidgets.plotly_plot.widget.ui.element", _FakeUiElement)
    monkeypatch.setattr("nicewidgets.plotly_plot.widget.ui.label", _FakeUiLabel)
    return created


class _RelayoutEvent:
    """Fake NiceGUI event object with Plotly relayout args."""

    def __init__(self, args: dict[str, Any]) -> None:
        """Create a fake relayout event.

        Args:
            args: Plotly relayout payload.
        """
        self.args = args


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
        x_label="time",
        y_label="df/f0",
        x_range=PlotlyAxisRange(0.0, 1.0),
        shapes=[{"type": "line"}],
    )

    assert "title" not in figure["layout"]
    assert figure["layout"]["xaxis"]["range"] == [0.0, 1.0]
    assert figure["layout"]["xaxis"]["autorange"] is False
    assert figure["layout"]["shapes"] == [{"type": "line"}]
    assert figure["layout"]["legend"]["orientation"] == "h"
    assert figure["layout"]["margin"]["b"] == 40
    assert figure["layout"]["paper_bgcolor"] == "white"
    assert figure["config"]["editable"] is True
    assert figure["config"]["scrollZoom"] is True
    assert figure["config"]["edits"]["titleText"] is False


def test_resolve_plot_layout_margins_bottom_by_axis_and_legend() -> None:
    """Bottom margin should follow axis-label and legend visibility."""
    assert resolve_plot_layout_margins(
        show_axis_labels=False,
        show_legend=False,
    )["b"] == 8
    assert resolve_plot_layout_margins(
        show_axis_labels=False,
        show_legend=True,
    )["b"] == 40
    assert resolve_plot_layout_margins(
        show_axis_labels=True,
        show_legend=False,
    )["b"] == 40
    assert resolve_plot_layout_margins(
        show_axis_labels=True,
        show_legend=True,
    )["b"] == 72


def test_build_plotly_figure_dict_applies_dark_theme() -> None:
    """Dark theme should set Plotly layout colors."""
    figure = build_plotly_figure_dict(theme="dark")

    assert figure["layout"]["paper_bgcolor"] == "#111827"
    assert figure["layout"]["font"]["color"] == "#f9fafb"


def test_widget_add_update_remove_trace(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Named continuous trace API should keep the figure dict synchronized."""
    widget = PlotlyPlotWidget()

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
    widget = PlotlyPlotWidget()

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


def test_widget_suppresses_relayout_echo_after_programmatic_set_x_limits(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Programmatic x limits should not re-fire ``on_x_range_changed`` on relayout echo."""
    ranges: list[tuple[float | None, float | None]] = []
    widget = PlotlyPlotWidget(on_x_range_changed=lambda x0, x1: ranges.append((x0, x1)))

    widget.set_x_axis_limits(2.0, 8.0)
    widget._on_plotly_relayout(_RelayoutEvent({"xaxis.range[0]": 2.0, "xaxis.range[1]": 8.0}))
    widget._on_plotly_relayout(
        _RelayoutEvent({"xaxis.range[0]": 2.0 + 1e-12, "xaxis.range[1]": 8.0 - 1e-12})
    )

    assert ranges == []


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


def test_widget_set_series_replaces_data_in_one_update(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Batch series replacement should use one browser update."""
    widget = PlotlyPlotWidget()
    widget.add_trace(name="old", x=[0.0], y=[1.0])

    traces = [
        PlotlyTraceData.from_sequences(name="df/f0", x=[0.0, 1.0], y=[2.0, 3.0]),
        PlotlyTraceData.from_sequences(name="derivative", x=[0.0, 1.0], y=[0.1, 0.2]),
    ]
    scatters = [
        PlotlyScatterData.from_sequences(name="peaks", x=[0.5], y=[1.5]),
    ]
    calls_before = len(fake_plotly[0].client.calls)
    widget.set_series(traces=traces, scatters=scatters)

    assert [trace["name"] for trace in widget.figure["data"]] == ["df/f0", "derivative", "peaks"]
    assert len(fake_plotly[0].client.calls) - calls_before == 1
    assert "Plotly.deleteTraces" in fake_plotly[0].client.calls[-1]
    assert "Plotly.addTraces" in fake_plotly[0].client.calls[-1]


def test_extract_rect_selection_parses_flat_keys() -> None:
    """Box-select relayout should parse flat selections[0].x0/x1 keys."""
    args = {"selections[0].x0": 1.5, "selections[0].x1": 3.5}
    assert extract_rect_selection_x_range_from_relayout(args) == (1.5, 3.5)


def test_extract_rect_selection_parses_list_form() -> None:
    """Box-select relayout should parse selections list payloads."""
    args = {
        "selections": [{"type": "rect", "x0": 2.0, "x1": 4.0, "y0": 0, "y1": 1}],
    }
    assert extract_rect_selection_x_range_from_relayout(args) == (2.0, 4.0)


def test_begin_select_x_range_echo_does_not_emit_x_range_changed(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Dragmode relayout echo after arming should not fire on_x_range_changed."""
    ranges: list[tuple[float | None, float | None]] = []
    widget = PlotlyPlotWidget(on_x_range_changed=lambda x0, x1: ranges.append((x0, x1)))

    widget.begin_select_x_range()
    widget._on_plotly_relayout(_RelayoutEvent({"dragmode": "select"}))

    assert ranges == []
    assert widget.figure["layout"]["dragmode"] == "select"


def test_box_select_emits_on_x_range_selected_once(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """A completed box-select should call on_x_range_selected and disarm."""
    selected: list[tuple[float, float]] = []
    widget = PlotlyPlotWidget(on_x_range_selected=lambda x0, x1: selected.append((x0, x1)))

    widget.begin_select_x_range()
    widget._on_plotly_relayout(
        _RelayoutEvent({"selections[0].x0": 1.0, "selections[0].x1": 2.5})
    )

    assert selected == [(1.0, 2.5)]
    assert widget.figure["layout"]["dragmode"] == "zoom"
    assert widget.figure["layout"]["selections"] == []


def test_doubleclick_resets_x_range_and_emits_auto(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Double-click should reset x-axis and emit (None, None)."""
    ranges: list[tuple[float | None, float | None]] = []
    widget = PlotlyPlotWidget(on_x_range_changed=lambda x0, x1: ranges.append((x0, x1)))

    widget.set_x_axis_limits(1.0, 5.0)
    widget._on_plotly_doubleclick(_RelayoutEvent({}))

    assert widget.figure["layout"]["xaxis"]["autorange"] is True
    assert ranges == [(None, None)]


def test_set_legend_visible_updates_bottom_margin(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Legend toggle should shrink or restore bottom margin."""
    widget = PlotlyPlotWidget()

    assert widget.figure["layout"]["margin"]["b"] == 40

    widget.set_legend_visible(False)
    assert widget.figure["layout"]["showlegend"] is False
    assert widget.figure["layout"]["margin"]["b"] == 8

    widget.set_legend_visible(True)
    assert widget.figure["layout"]["showlegend"] is True
    assert widget.figure["layout"]["margin"]["b"] == 40


def test_set_legend_visible_preserves_bottom_horizontal_layout(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Legend toggle should preserve bottom-centered horizontal legend layout."""
    widget = PlotlyPlotWidget()

    widget.set_legend_visible(False)
    assert widget.figure["layout"]["showlegend"] is False

    widget.set_legend_visible(True)
    legend = widget.figure["layout"]["legend"]
    assert widget.figure["layout"]["showlegend"] is True
    assert legend["orientation"] == "h"
    assert legend["x"] == 0.5
    assert legend["y"] == -0.15


def test_event_overlays_render_as_non_editable_rects(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Event overlays should append rect shapes below measurement shapes."""
    widget = PlotlyPlotWidget()
    widget.add_measurement_line(name="m", orientation="horizontal", value=1.0)
    widget.events.set_events(
        [PlotlyEventOverlay(id="7", x0=1.0, x1=2.0, event_type="user")]
    )

    shapes = widget.figure["layout"]["shapes"]
    assert len(shapes) == 2
    assert shapes[1]["type"] == "rect"
    assert shapes[1]["name"] == "event:7"
    assert shapes[1]["editable"] is False
    assert shapes[1]["yref"] == "paper"


def test_event_overlays_survive_set_series(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Replacing series should keep event overlay shapes."""
    widget = PlotlyPlotWidget()
    widget.add_trace(name="old", x=[0.0], y=[1.0])
    widget.events.set_events([PlotlyEventOverlay(id="1", x0=0.5, x1=1.5)])
    widget.set_series(traces=[PlotlyTraceData.from_sequences(name="new", x=[0.0, 1.0], y=[1.0, 2.0])])

    event_shapes = [s for s in widget.figure["layout"]["shapes"] if s.get("name", "").startswith("event:")]
    assert len(event_shapes) == 1


def test_select_event_updates_highlight_style(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Selected event should use the selected highlight style."""
    widget = PlotlyPlotWidget()
    widget.events.set_events([PlotlyEventOverlay(id="a", x0=1.0, x1=2.0, event_type="user")])
    widget.events.select_event("a")

    shape = widget.figure["layout"]["shapes"][0]
    assert shape["line"]["width"] == 4


def test_widget_set_series_preserves_measurement_shapes(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Replacing series data should not remove measurement layout shapes."""
    widget = PlotlyPlotWidget()
    widget.add_measurement_line(name="f0", orientation="horizontal", value=1.0)
    widget.set_series(
        traces=[PlotlyTraceData.from_sequences(name="signal", x=[0.0, 1.0], y=[1.0, 2.0])],
    )

    assert len(widget.figure["layout"]["shapes"]) == 1
    assert widget.figure["data"][0]["name"] == "signal"


def test_widget_set_dark_mode_updates_layout_and_relayouts(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Dark-mode toggles should update layout colors and relayout once."""
    widget = PlotlyPlotWidget(theme="light")

    widget.set_dark_mode(True)

    assert widget.figure["layout"]["paper_bgcolor"] == "#111827"
    assert "Plotly.relayout" in fake_plotly[0].client.calls[-1]
    assert '"paper_bgcolor": "#111827"' in fake_plotly[0].client.calls[-1]


def test_register_series_menu_items_preserves_visibility_across_refresh(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Registered series visibility should persist until page reload."""
    widget = PlotlyPlotWidget()
    widget.register_series_menu_items(
        [
            PlotlySeriesMenuItem("Derivative of df/f0", "Derivative of df/f0", default_visible=False),
            PlotlySeriesMenuItem("Peak width 50", "Peak width 50", default_visible=True),
        ]
    )
    traces = [
        PlotlyTraceData.from_sequences(name="df/f0 signal", x=[0.0, 1.0], y=[1.0, 2.0]),
        PlotlyTraceData.from_sequences(name="Derivative of df/f0", x=[0.0, 1.0], y=[0.1, 0.2]),
        PlotlyTraceData.from_sequences(name="Peak width 50", x=[0.5, 1.0], y=[0.3, 0.3]),
    ]
    widget.set_series(traces=traces)
    assert widget.figure["data"][1]["visible"] is False
    assert widget.figure["data"][2]["visible"] is True

    widget.toggle_series_visible("Derivative of df/f0")
    widget.set_series(traces=traces)
    assert widget.is_series_visible("Derivative of df/f0") is True
    assert widget.figure["data"][1]["visible"] is True


def test_toggle_series_visible_updates_existing_scatter(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Scatter menu toggles should restyle an existing overlay trace."""
    widget = PlotlyPlotWidget()
    widget.register_series_menu_items(
        [PlotlySeriesMenuItem("Onsets", "Onsets", default_visible=True, kind="scatter")]
    )
    widget.set_series(
        scatters=[PlotlyScatterData.from_sequences(name="Onsets", x=[0.5], y=[1.0])],
    )

    widget.toggle_series_visible("Onsets")

    assert widget.is_series_visible("Onsets") is False
    assert widget.figure["data"][0]["visible"] is False
    assert "Plotly.restyle" in fake_plotly[0].client.calls[-1]


def test_right_axis_trace_creates_yaxis2(fake_plotly: list[_FakePlotlyElement]) -> None:
    """A right-axis trace should create ``layout.yaxis2`` and bind the trace."""
    widget = PlotlyPlotWidget(y2_label="rate (1/s)")

    widget.add_trace(name="signal", x=[0.0, 1.0], y=[1.0, 2.0])
    assert "yaxis2" not in widget.figure["layout"]

    widget.add_trace(name="derivative", x=[0.0, 1.0], y=[0.1, 0.2], y_axis="right")

    assert widget.figure["layout"]["yaxis2"]["overlaying"] == "y"
    assert widget.figure["layout"]["yaxis2"]["side"] == "right"
    assert widget.figure["data"][1]["yaxis"] == "y2"


def test_remove_last_right_axis_trace_removes_yaxis2(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Removing the last right-axis trace should remove ``layout.yaxis2``."""
    widget = PlotlyPlotWidget()
    widget.add_trace(name="derivative", x=[0.0, 1.0], y=[0.1, 0.2], y_axis="right")
    assert "yaxis2" in widget.figure["layout"]

    widget.remove_trace("derivative")

    assert "yaxis2" not in widget.figure["layout"]


def test_set_series_with_mixed_axes(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Batch series replacement should configure mixed-axis traces and yaxis2."""
    widget = PlotlyPlotWidget(y2_label="d/dt")
    traces = [
        PlotlyTraceData.from_sequences(name="df/f0", x=[0.0, 1.0], y=[1.0, 2.0]),
        PlotlyTraceData.from_sequences(
            name="derivative",
            x=[0.0, 1.0],
            y=[0.1, 0.2],
            y_axis="right",
        ),
    ]

    widget.set_series(traces=traces)

    assert widget.figure["data"][1]["yaxis"] == "y2"
    assert widget.figure["layout"]["yaxis2"]["title"]["text"] == ""


def test_right_axis_scatter_creates_yaxis2(fake_plotly: list[_FakePlotlyElement]) -> None:
    """A right-axis scatter should create ``layout.yaxis2``."""
    widget = PlotlyPlotWidget()
    widget.plot_scatter(name="markers", x=[0.5], y=[1.0], y_axis="right")

    assert widget.figure["data"][0]["yaxis"] == "y2"
    assert "yaxis2" in widget.figure["layout"]


def test_right_axis_measurement_requires_existing_yaxis2(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Right-axis measurements should fail before a right-axis trace exists."""
    widget = PlotlyPlotWidget()

    with pytest.raises(ValueError, match="right-axis trace or scatter"):
        widget.add_measurement_line(
            name="threshold",
            orientation="horizontal",
            value=1.0,
            y_axis="right",
        )


def test_right_axis_measurement_uses_y2_and_reports_axis_on_drag(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Right-axis horizontal measurements should bind to ``y2`` and report axis."""
    events: list[MeasurementChangeEvent] = []
    widget = PlotlyPlotWidget(on_measurement_changed=events.append)
    widget.add_trace(name="derivative", x=[0.0, 1.0], y=[0.1, 0.2], y_axis="right")
    widget.add_measurement_line(
        name="threshold",
        orientation="horizontal",
        value=1.0,
        y_axis="right",
    )

    assert widget.figure["layout"]["shapes"][0]["yref"] == "y2"
    widget._on_plotly_relayout(_RelayoutEvent({"shapes[0].y0": 1.5, "shapes[0].y1": 1.5}))

    assert events[-1].position == 1.5
    assert events[-1].y_axis == "right"


def test_axis_labels_toggle_updates_bottom_margin(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Axis-label toggle should adjust bottom margin when legend is visible."""
    widget = PlotlyPlotWidget()

    assert widget.figure["layout"]["margin"]["b"] == 40

    widget.set_axis_labels_visible(True)
    assert widget.figure["layout"]["margin"]["b"] == 72

    widget.set_axis_labels_visible(False)
    assert widget.figure["layout"]["margin"]["b"] == 40


def test_axis_labels_on_keeps_plot_grid_lines_off(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Axis labels should not enable internal horizontal/vertical grid lines."""
    widget = PlotlyPlotWidget()

    widget.set_axis_labels_visible(True)

    assert widget.figure["layout"]["xaxis"]["showgrid"] is False
    assert widget.figure["layout"]["yaxis"]["showgrid"] is False


def test_axis_labels_toggle_updates_yaxis2_and_dual_margin(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Axis-label toggle should decorate ``yaxis2`` and widen the right margin."""
    widget = PlotlyPlotWidget(y2_label="rate (1/s)")
    widget.add_trace(name="derivative", x=[0.0, 1.0], y=[0.1, 0.2], y_axis="right")

    widget.set_axis_labels_visible(True)

    assert widget.figure["layout"]["yaxis2"]["title"]["text"] == "rate (1/s)"
    assert widget.figure["layout"]["margin"]["r"] == 60


def test_hidden_right_axis_trace_hides_yaxis2_decorations(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Invisible right-axis traces should not show y2 decorations or dual margin."""
    widget = PlotlyPlotWidget(y2_label="rate (1/s)")
    widget.register_series_menu_items(
        [PlotlySeriesMenuItem("derivative", "derivative", default_visible=False)]
    )
    traces = [
        PlotlyTraceData.from_sequences(name="df/f0", x=[0.0, 1.0], y=[1.0, 2.0]),
        PlotlyTraceData.from_sequences(
            name="derivative",
            x=[0.0, 1.0],
            y=[0.1, 0.2],
            y_axis="right",
            visible=False,
        ),
    ]

    widget.set_series(traces=traces)
    widget.set_axis_labels_visible(True)

    assert widget.figure["layout"]["yaxis2"]["title"]["text"] == ""
    assert widget.figure["layout"]["yaxis2"]["showticklabels"] is False
    assert widget.figure["layout"]["margin"]["r"] == 24


def test_toggle_right_axis_visibility_updates_yaxis2_decorations(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Toggling a right-axis trace should show and hide y2 decorations."""
    widget = PlotlyPlotWidget(y2_label="rate (1/s)")
    widget.register_series_menu_items(
        [PlotlySeriesMenuItem("derivative", "derivative", default_visible=False)]
    )
    widget.set_series(
        traces=[
            PlotlyTraceData.from_sequences(name="df/f0", x=[0.0, 1.0], y=[1.0, 2.0]),
            PlotlyTraceData.from_sequences(
                name="derivative",
                x=[0.0, 1.0],
                y=[0.1, 0.2],
                y_axis="right",
            ),
        ]
    )
    widget.set_axis_labels_visible(True)

    assert widget.figure["layout"]["yaxis2"]["title"]["text"] == ""
    assert widget.figure["layout"]["margin"]["r"] == 24

    widget.toggle_series_visible("derivative")

    assert widget.figure["layout"]["yaxis2"]["title"]["text"] == "rate (1/s)"
    assert widget.figure["layout"]["margin"]["r"] == 60


def test_init_show_legend_false_builds_without_legend(fake_plotly: list[_FakePlotlyElement]) -> None:
    """Initial legend visibility should come from the constructor kwarg."""
    widget = PlotlyPlotWidget(show_legend=False)

    assert widget.display_options.show_legend is False
    assert widget.figure["layout"]["showlegend"] is False
    assert widget.figure["layout"]["margin"]["b"] == 8


def test_set_placeholder_text_shows_and_hides_overlay(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Placeholder text should toggle the centered overlay."""
    widget = PlotlyPlotWidget()

    widget.set_placeholder_text("No data")
    assert widget.placeholder_text == "No data"
    assert widget._placeholder_container.visible is True

    widget.set_placeholder_text(None)
    assert widget.placeholder_text is None
    assert widget._placeholder_container.visible is False


def test_set_series_with_data_clears_placeholder(
    fake_plotly: list[_FakePlotlyElement],
) -> None:
    """Replacing series with data should hide any visible placeholder."""
    widget = PlotlyPlotWidget()
    widget.set_placeholder_text("No data")

    widget.set_series(
        traces=[PlotlyTraceData.from_sequences(name="trace", x=[0.0], y=[1.0])]
    )

    assert widget.placeholder_text is None
    assert widget._placeholder_container.visible is False
