"""Tests for the EChartWidget option builder."""

from __future__ import annotations

import pytest

from nicewidgets.echart_widget.models import EChartAxisRange, EChartLineData
from nicewidgets.echart_widget.widget import build_line_options


def test_echart_line_data_validates_lengths() -> None:
    """EChartLineData should reject mismatched x/y lengths."""
    with pytest.raises(ValueError):
        EChartLineData.from_sequences(
            x=[0.0, 1.0],
            y=[1.0],
            x_label="x",
            y_label="y",
        )


def test_build_line_options_uses_axis_labels_and_data_pairs() -> None:
    """Line options should contain value axes and paired data."""
    line = EChartLineData.from_sequences(
        x=[0.0, 1.0],
        y=[2.0, 3.0],
        x_label="Time (s)",
        y_label="Velocity",
        series_name="Radon velocity",
    )

    options = build_line_options(line, EChartAxisRange(x_min=0.0, x_max=2.0))

    assert options["xAxis"]["type"] == "value"
    assert options["xAxis"]["name"] == "Time (s)"
    assert options["xAxis"]["min"] == 0.0
    assert options["xAxis"]["max"] == 2.0
    assert options["yAxis"]["name"] == "Velocity"
    assert options["series"][0]["name"] == "Radon velocity"
    assert options["series"][0]["data"] == [[0.0, 2.0], [1.0, 3.0]]


def test_echart_axis_range_validates_bounds() -> None:
    """Axis range should reject inverted bounds."""
    with pytest.raises(ValueError):
        EChartAxisRange(x_min=2.0, x_max=1.0)
