"""Tests for NicePool plot error helpers."""

from __future__ import annotations

import pandas as pd
import pytest

from nicewidgets.nicepool.plot_errors import (
    PlotConfigurationError,
    PlotDataError,
    empty_plotly_figure,
    require_categorical_group_col,
    require_histogram_x_values,
)
from nicewidgets.nicepool.plot_state import PlotType


def test_require_categorical_group_col_rejects_high_cardinality_numeric_column() -> None:
    """Continuous numeric columns should be rejected for swarm plots."""
    df = pd.DataFrame({"velocity_mean": [float(i) for i in range(30)]})

    with pytest.raises(PlotConfigurationError, match="categorical"):
        require_categorical_group_col(df, "velocity_mean", plot_type=PlotType.SWARM)


def test_require_histogram_x_values_rejects_empty_series() -> None:
    """Histogram helpers should fail when no numeric x values remain."""
    with pytest.raises(PlotDataError, match="no valid values"):
        require_histogram_x_values(pd.Series(dtype=float), xcol="diameter", plot_type=PlotType.HISTOGRAM)


def test_empty_plotly_figure_includes_message_annotation() -> None:
    """Empty figure helper should surface the user-facing error text."""
    fig = empty_plotly_figure("Choose another Group column.")

    assert fig["data"] == []
    assert fig["layout"]["annotations"][0]["text"] == "Choose another Group column."
