"""Display options for the reusable Plotly plot widget."""

from __future__ import annotations

from dataclasses import dataclass

from nicewidgets.plotly_theme import PlotlyThemeName


@dataclass(slots=True)
class PlotlyPlotDisplayOptions:
    """User-facing display toggles for :class:`PlotlyPlotWidget`.

    Args:
        show_axis_labels: Whether axis title text, tick labels, ticks, axis
            lines, and grid lines are visible.
        show_plotly_toolbar: Whether Plotly's modebar is visible.
        show_hover_info: Whether Plotly emits hover labels for plot traces.
        theme: Plotly layout color theme.
    """

    show_axis_labels: bool = False
    show_plotly_toolbar: bool = False
    show_hover_info: bool = False
    theme: PlotlyThemeName = "light"
