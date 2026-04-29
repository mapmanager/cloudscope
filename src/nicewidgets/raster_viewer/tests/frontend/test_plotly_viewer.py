"""Tests for the thin Plotly viewer adapter."""

from __future__ import annotations

import numpy as np
import pytest

import raster_viewer.frontend.plotly_viewer as plotly_viewer_module
from raster_viewer.backend.image_model import RasterGridSpec, RowColBounds
from raster_viewer.frontend.plotly_coord_transform import PlotlyCoordTransform
from raster_viewer.frontend.plotly_protocol import PlotlyViewportPayload
from raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer

_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='', y_unit='')


@pytest.mark.asyncio
async def test_set_data_initializes_backend_state() -> None:
    """Setting data should initialize backend state and bounds."""
    viewer = PlotlyRasterViewer()
    data = np.arange(32, dtype=np.float32).reshape(4, 8)

    response = await viewer.set_data(data, grid=_GRID)

    assert viewer.has_data is True
    b = viewer.current_bounds
    assert (b.row_min, b.row_max, b.col_min, b.col_max) == (0.0, 4.0, 0.0, 8.0)
    assert response.mode == 'image_png'


def test_build_before_set_data_returns_empty_figure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Building before data is set should create an empty plot."""
    captured: dict[str, object] = {}

    class DummyElement:
        def on(self, *_args, **_kwargs) -> 'DummyElement':
            return self

    class DummyUI:
        @staticmethod
        def plotly(figure):
            captured['figure'] = figure
            return DummyElement()

    import types

    monkeypatch.setattr(plotly_viewer_module, 'ui', types.SimpleNamespace(plotly=DummyUI.plotly))

    viewer = PlotlyRasterViewer()
    viewer.build()

    figure = captured['figure']
    assert isinstance(figure, dict)
    assert figure['data'] == []


@pytest.mark.asyncio
async def test_set_x_axis_range_preserves_y_row_col_extent(monkeypatch: pytest.MonkeyPatch) -> None:
    """set_x_axis_range should update row span only; column span unchanged."""
    async def _noop_js(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(plotly_viewer_module.ui, 'run_javascript', _noop_js)

    class _DummyPlot:
        id = 99

    viewer = PlotlyRasterViewer()
    viewer._plot = _DummyPlot()
    viewer._transform = PlotlyCoordTransform(nrows=4, ncols=8, grid=_GRID)
    viewer._current_bounds = RowColBounds(
        row_min=0.0,
        row_max=4.0,
        col_min=0.0,
        col_max=8.0,
    )

    await viewer.set_x_axis_range(x_min=1.0, x_max=3.0)

    b = viewer.current_bounds
    assert (b.row_min, b.row_max) == (1.0, 3.0)
    assert (b.col_min, b.col_max) == (0.0, 8.0)


@pytest.mark.asyncio
async def test_request_before_set_data_raises() -> None:
    """Relayout requests should fail before any dataset is set."""
    viewer = PlotlyRasterViewer()
    payload = PlotlyViewportPayload(relayout={}, width_px=100, height_px=100)
    with pytest.raises(RuntimeError, match='No data set'):
        viewer.request_from_plotly(payload=payload)
