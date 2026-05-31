"""Display options for the Plotly raster viewer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PlotlyRasterViewerDisplayOptions:
    """User-facing display toggles for :class:`PlotlyRasterViewer`.

    Args:
        show_plotly_toolbar: Whether Plotly's modebar is visible.
        show_rois: Whether rectangular ROI overlays are visible.
        show_trace_overlays: Whether managed x/y trace overlays are visible.
        show_axis_labels: Whether x/y axis label text is visible.
    """

    show_plotly_toolbar: bool = False
    show_rois: bool = True
    show_trace_overlays: bool = True
    show_axis_labels: bool = False
