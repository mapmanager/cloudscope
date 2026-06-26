"""Plot configuration and data errors for NicePool figure generation."""

from __future__ import annotations

import pandas as pd

from nicewidgets.nicepool.plot_helpers import is_categorical_column
from nicewidgets.nicepool.plot_state import PlotType


class PlotConfigurationError(ValueError):
    """Raised when plot state is invalid for the current dataframe."""


class PlotDataError(ValueError):
    """Raised when filtered data cannot satisfy the requested plot."""


_PLOT_TYPE_LABELS: dict[PlotType, str] = {
    PlotType.SCATTER: "Scatter plot",
    PlotType.SWARM: "Swarm plot",
    PlotType.BOX_PLOT: "Box plot",
    PlotType.VIOLIN: "Violin plot",
    PlotType.GROUPED: "Grouped plot",
    PlotType.HISTOGRAM: "Histogram",
    PlotType.CUMULATIVE_HISTOGRAM: "Cumulative histogram",
}


def plot_type_label(plot_type: PlotType) -> str:
    """Return a user-facing label for a plot type.

    Args:
        plot_type: Plot type enum value.

    Returns:
        Short label suitable for notifications.
    """
    return _PLOT_TYPE_LABELS.get(plot_type, plot_type.value.replace("_", " ").title())


def require_group_col(group_col: str | None, *, plot_type: PlotType) -> None:
    """Require a group column for plot types that need categorical x-axis grouping.

    Args:
        group_col: Selected group column, if any.
        plot_type: Requested plot type.

    Raises:
        PlotConfigurationError: When ``group_col`` is missing.
    """
    if group_col:
        return
    label = plot_type_label(plot_type)
    raise PlotConfigurationError(
        f"{label} requires a Group column. Select a categorical column such as parent or roi_id "
        "in the control panel."
    )


def require_categorical_group_col(
    df: pd.DataFrame,
    group_col: str | None,
    *,
    plot_type: PlotType,
) -> None:
    """Require a categorical group column for box, violin, and swarm plots.

    Args:
        df: Filtered dataframe used for plotting.
        group_col: Selected group column, if any.
        plot_type: Requested plot type.

    Raises:
        PlotConfigurationError: When ``group_col`` is missing or not categorical.
    """
    require_group_col(group_col, plot_type=plot_type)
    assert group_col is not None
    if group_col not in df.columns:
        label = plot_type_label(plot_type)
        raise PlotConfigurationError(
            f"{label} group column {group_col!r} is not in the current data. "
            "Choose another Group column or refresh the pool data."
        )
    if is_categorical_column(df, group_col):
        return
    label = plot_type_label(plot_type)
    raise PlotConfigurationError(
        f"{label} requires a categorical Group column. {group_col!r} has too many unique values. "
        "Choose a low-cardinality column such as parent or roi_id, or switch to Scatter plot."
    )


def require_histogram_x_values(x: pd.Series, *, xcol: str, plot_type: PlotType) -> None:
    """Require non-empty numeric x values for histogram plot types.

    Args:
        x: Candidate x values after filtering and coercion.
        xcol: Column name shown in the error message.
        plot_type: Histogram or cumulative histogram plot type.

    Raises:
        PlotDataError: When no valid x values remain.
    """
    if len(x) > 0:
        return
    label = plot_type_label(plot_type)
    raise PlotDataError(
        f"{label} has no valid values for column {xcol!r} after filters. "
        "Widen pre-filters, choose another x column, or check remove-values settings."
    )


def empty_plotly_figure(message: str) -> dict:
    """Return a minimal Plotly figure dict that displays an error message.

    Args:
        message: User-facing text to show in the plot area.

    Returns:
        Plotly figure dictionary with no data traces.
    """
    return {
        "data": [],
        "layout": {
            "annotations": [
                {
                    "text": message,
                    "xref": "paper",
                    "yref": "paper",
                    "x": 0.5,
                    "y": 0.5,
                    "showarrow": False,
                    "align": "center",
                }
            ],
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "margin": {"l": 20, "r": 20, "t": 20, "b": 20},
        },
    }
