"""Tests for Plotly raster viewer context-menu display state."""

from __future__ import annotations

import asyncio
import sys
import types

import numpy as np

if 'nicegui' not in sys.modules:
    fake_nicegui = types.ModuleType('nicegui')
    fake_nicegui.ui = types.SimpleNamespace()
    sys.modules['nicegui'] = fake_nicegui

from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec
from nicewidgets.raster_viewer.frontend.plotly_context_menu import (
    PlotlyRasterViewerContextMenu,
)
from nicewidgets.raster_viewer.frontend.plotly_display_options import (
    PlotlyRasterViewerDisplayOptions,
)
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer
from nicewidgets.raster_viewer.frontend.roi_overlay import RectRoiOverlay
from nicewidgets.raster_viewer.frontend.trace_overlay import PlotlyTraceOverlay


def _viewer_with_data(
    *,
    display_options: PlotlyRasterViewerDisplayOptions | None = None,
) -> PlotlyRasterViewer:
    """Return a headless viewer with a small raster dataset loaded."""
    viewer = PlotlyRasterViewer(display_options=display_options)
    data = np.arange(100, dtype=np.float32).reshape(10, 10)
    grid = RasterGridSpec(dx=1.0, dy=2.0, x_unit='s', y_unit='um')
    asyncio.run(viewer.set_data(data, grid=grid))
    return viewer


def test_display_options_defaults_match_context_menu_requirements() -> None:
    """Display options should default to toolbar off, overlays on, labels off."""
    options = PlotlyRasterViewerDisplayOptions()

    assert options.show_plotly_toolbar is False
    assert options.show_rois is True
    assert options.show_trace_overlays is True
    assert options.show_axis_labels is False


def test_viewer_accepts_caller_supplied_display_options() -> None:
    """Callers should be able to provide initial display options."""
    options = PlotlyRasterViewerDisplayOptions(
        show_plotly_toolbar=True,
        show_rois=False,
        show_trace_overlays=False,
        show_axis_labels=True,
    )

    viewer = _viewer_with_data(display_options=options)
    layout = viewer.figure['layout']

    assert viewer.display_options is options
    assert viewer.figure['config']['displayModeBar'] is True
    assert layout['xaxis']['title']['text'] == 's'
    assert layout['yaxis']['title']['text'] == 'um'


def test_axis_labels_are_hidden_by_default_but_preserved_for_toggle() -> None:
    """Axis labels should be blank by default and restored when enabled."""
    viewer = _viewer_with_data()
    layout = viewer.figure['layout']

    assert layout['xaxis']['title']['text'] == ''
    assert layout['yaxis']['title']['text'] == ''

    viewer.set_axis_labels_visible(True)

    assert viewer.figure['layout']['xaxis']['title']['text'] == 's'
    assert viewer.figure['layout']['yaxis']['title']['text'] == 'um'


def test_roi_visibility_toggle_sets_plotly_shape_visible_only() -> None:
    """ROI toggles should use Plotly shape visibility instead of deleting ROIs."""
    viewer = _viewer_with_data()
    viewer.set_rois([RectRoiOverlay(roi_id=1, x0=0, x1=1, y0=2, y1=3)])

    roi_shape = viewer.figure['layout']['shapes'][0]
    assert roi_shape['name'] == 'roi:1'
    assert roi_shape['visible'] is True

    viewer.set_roi_overlays_visible(False)

    roi_shape = viewer.figure['layout']['shapes'][0]
    assert roi_shape['name'] == 'roi:1'
    assert roi_shape['visible'] is False


def test_trace_visibility_toggle_preserves_trace_and_respects_overlay_visible() -> None:
    """Trace toggles should use Plotly trace visibility without deleting traces."""
    viewer = _viewer_with_data()
    viewer.set_trace_overlays([
        PlotlyTraceOverlay(trace_id='visible-trace', x=[1], y=[2], visible=True),
        PlotlyTraceOverlay(trace_id='hidden-trace', x=[3], y=[4], visible=False),
    ])

    traces = {trace['meta']['trace_id']: trace for trace in viewer.figure['data'][1:]}
    assert traces['visible-trace']['visible'] is True
    assert traces['hidden-trace']['visible'] is False

    viewer.set_trace_overlays_visible(False)
    traces = {trace['meta']['trace_id']: trace for trace in viewer.figure['data'][1:]}
    assert traces['visible-trace']['visible'] is False
    assert traces['hidden-trace']['visible'] is False

    viewer.set_trace_overlays_visible(True)
    traces = {trace['meta']['trace_id']: trace for trace in viewer.figure['data'][1:]}
    assert traces['visible-trace']['visible'] is True
    assert traces['hidden-trace']['visible'] is False


def test_context_menu_toggle_label_uses_check_prefix() -> None:
    """Context menu labels should show a check mark only when enabled."""
    assert PlotlyRasterViewerContextMenu._toggle_label('ROIs', True) == '✓ ROIs'
    assert PlotlyRasterViewerContextMenu._toggle_label('ROIs', False) == 'ROIs'
