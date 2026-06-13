"""Display options for the Plotly raster viewer."""

from __future__ import annotations

from dataclasses import dataclass

from nicewidgets.raster_viewer.frontend.plotly_theme import PlotlyRasterViewerThemeName


@dataclass(slots=True)
class PlotlyRasterViewerDisplayOptions:
    """User-facing display toggles for :class:`PlotlyRasterViewer`.

    Args:
        show_plotly_toolbar: Whether Plotly's modebar is visible.
        show_rois: Whether rectangular ROI overlays are visible.
        show_roi_labels: Whether rectangular ROI overlay labels are visible.
        show_trace_overlays: Whether managed x/y trace overlays are visible.
        show_axis_labels: Whether axis title text, tick labels, ticks, axis
            lines, and grid lines are visible.
        show_hover_info: Whether Plotly emits hover labels for the raster trace.
            Defaults to False to avoid clutter and reduce browser event traffic.
        square_plot: Whether Plotly should constrain the visible raster plot to
            a square plot area.
        theme: Plotly raster viewer color theme.
    """

    show_plotly_toolbar: bool = False
    show_rois: bool = True
    show_roi_labels: bool = True
    show_trace_overlays: bool = True
    show_axis_labels: bool = False
    show_hover_info: bool = False
    square_plot: bool = False
    theme: PlotlyRasterViewerThemeName = 'light'
