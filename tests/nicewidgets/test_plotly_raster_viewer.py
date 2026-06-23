"""Tests for PlotlyRasterViewer trace overlay state."""

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
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer
from nicewidgets.raster_viewer.frontend.trace_overlay import PlotlyTraceOverlay


def test_set_data_clears_trace_overlays() -> None:
    """Loading a new dataset should clear stale trace overlays."""
    viewer = PlotlyRasterViewer()
    viewer.add_trace_overlay(
        PlotlyTraceOverlay(trace_id='left', x=[0.0, 1.0], y=[2.0, 3.0])
    )

    data = np.arange(100, dtype=np.float32).reshape(10, 10)
    grid = RasterGridSpec(dx=1.0, dy=1.0, x_unit='s', y_unit='um')

    asyncio.run(viewer.set_data(data, grid=grid))

    figure_data = viewer.figure.get('data')
    assert isinstance(figure_data, list)
    assert len(figure_data) == 1


def test_set_data_from_pyramid_reuses_prebuilt_pyramid() -> None:
    """Prebuilt pyramids should bypass a second pyramid build in the viewer."""
    from nicewidgets.raster_viewer.backend.image_model import BackendImage
    from nicewidgets.raster_viewer.backend.pyramid import ImagePyramid

    viewer = PlotlyRasterViewer()
    data = np.arange(36, dtype=np.float32).reshape(6, 6)
    grid = RasterGridSpec(dx=0.5, dy=0.25, x_unit='s', y_unit='um')
    pyramid = ImagePyramid(BackendImage(data, grid=grid))

    asyncio.run(viewer.set_data_from_pyramid(data, grid=grid, pyramid=pyramid))

    assert viewer.has_data
    assert viewer.figure.get('data') is not None