"""Plotly light/dark theme helpers for the raster viewer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PlotlyRasterViewerThemeName = Literal['light', 'dark']


@dataclass(frozen=True, slots=True)
class PlotlyRasterViewerTheme:
    """Colors used to render a Plotly raster viewer theme.

    Args:
        paper_bgcolor: Color for the Plotly paper/background area.
        plot_bgcolor: Color for the plotting area.
        font_color: Default text color.
        axis_color: Axis title, tick, and line color.
        grid_color: Axis grid color.
        zero_line_color: Axis zero-line color.
    """

    paper_bgcolor: str
    plot_bgcolor: str
    font_color: str
    axis_color: str
    grid_color: str
    zero_line_color: str


PLOTLY_RASTER_VIEWER_THEMES: dict[PlotlyRasterViewerThemeName, PlotlyRasterViewerTheme] = {
    'light': PlotlyRasterViewerTheme(
        paper_bgcolor='white',
        plot_bgcolor='white',
        font_color='#111827',
        axis_color='#374151',
        grid_color='#e5e7eb',
        zero_line_color='#d1d5db',
    ),
    'dark': PlotlyRasterViewerTheme(
        paper_bgcolor='#111827',
        plot_bgcolor='#111827',
        font_color='#f9fafb',
        axis_color='#d1d5db',
        grid_color='#374151',
        zero_line_color='#4b5563',
    ),
}


def normalize_plotly_raster_viewer_theme(value: str) -> PlotlyRasterViewerThemeName:
    """Return a supported Plotly raster-viewer theme name.

    Args:
        value: Candidate theme name.

    Returns:
        ``'dark'`` when ``value`` is dark; otherwise ``'light'``.
    """
    return 'dark' if str(value).lower() == 'dark' else 'light'


def theme_for_name(name: PlotlyRasterViewerThemeName) -> PlotlyRasterViewerTheme:
    """Return the color palette for a supported theme name.

    Args:
        name: Supported theme name.

    Returns:
        Theme color palette.
    """
    return PLOTLY_RASTER_VIEWER_THEMES[name]
