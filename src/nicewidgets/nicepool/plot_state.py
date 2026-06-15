"""Plot state models for NicePool."""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any

from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE


class PlotType(StrEnum):
    """Available NicePool plot types."""

    SCATTER = "scatter"
    SWARM = "swarm"
    BOX_PLOT = "box_plot"
    VIOLIN = "violin"
    HISTOGRAM = "histogram"
    CUMULATIVE_HISTOGRAM = "cumulative_histogram"
    GROUPED = "grouped"


@dataclass(slots=True)
class PlotState:
    """Configuration state for one NicePool plot.

    Args:
        pre_filter: Mapping from pre-filter columns to selected values.
        xcol: X-axis column.
        ycol: Y-axis column.
        plot_type: Plot type.
        group_col: Optional grouping/color column.
        color_grouping: Optional nested grouping column.
        ystat: Statistic used by grouped plots.
        cv_epsilon: Epsilon used when computing coefficient of variation.
        histogram_bins: Number of histogram bins.
        use_absolute_value: Whether numeric values are absolute-valued.
        swarm_jitter_amount: Swarm jitter amount.
        swarm_group_offset: Nested swarm group offset.
        use_remove_values: Whether values outside threshold are set to missing.
        remove_values_threshold: Symmetric threshold for value removal.
        show_mean: Whether mean overlays are shown where supported.
        show_std_sem: Whether error overlays are shown where supported.
        std_sem_type: Error overlay type, ``std`` or ``sem``.
        mean_line_width: Mean line width.
        error_line_width: Error line width.
        show_raw: Whether raw points are shown where supported.
        point_size: Marker size.
        show_legend: Whether Plotly legend is shown.
    """

    pre_filter: dict[str, Any]
    xcol: str
    ycol: str
    plot_type: PlotType = PlotType.SCATTER
    group_col: str | None = None
    color_grouping: str | None = None
    ystat: str = "mean"
    cv_epsilon: float = 0.01
    histogram_bins: int = 50
    use_absolute_value: bool = False
    swarm_jitter_amount: float = 0.35
    swarm_group_offset: float = 0.3
    use_remove_values: bool = False
    remove_values_threshold: float | None = None
    show_mean: bool = False
    show_std_sem: bool = False
    std_sem_type: str = "std"
    mean_line_width: int = 2
    error_line_width: int = 2
    show_raw: bool = True
    point_size: int = 6
    show_legend: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize state to a dictionary.

        Returns:
            Serializable state dictionary.
        """
        data = {field.name: getattr(self, field.name) for field in fields(self)}
        data["plot_type"] = self.plot_type.value
        return data
        
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlotState:
        """Create state from a dictionary.

        Args:
            data: Serialized plot state.

        Returns:
            Plot state instance.
        """
        values = dict(data)
        values["plot_type"] = PlotType(values.get("plot_type", PlotType.SCATTER.value))
        pre_filter = values.get("pre_filter")
        values["pre_filter"] = dict(pre_filter) if isinstance(pre_filter, dict) else {}
        return cls(**values)


def make_default_plot_state(df_columns: list[str], numeric_columns: list[str], pre_filter_columns: tuple[str, ...]) -> PlotState:
    """Create a reasonable default state for a DataFrame schema.

    Args:
        df_columns: DataFrame column names.
        numeric_columns: Numeric column names.
        pre_filter_columns: Pre-filter columns.

    Returns:
        Plot state with default columns.
    """
    if numeric_columns:
        xcol = numeric_columns[0]
        ycol = numeric_columns[1] if len(numeric_columns) > 1 else numeric_columns[0]
    else:
        first = df_columns[0] if df_columns else ""
        xcol = first
        ycol = first
    group_col = None
    for column in ("condition", "genotype", "channel", "roi_id", "accept"):
        if column in df_columns:
            group_col = column
            break
    return PlotState(
        pre_filter={column: PRE_FILTER_NONE for column in pre_filter_columns},
        xcol=xcol,
        ycol=ycol,
        group_col=group_col,
    )
