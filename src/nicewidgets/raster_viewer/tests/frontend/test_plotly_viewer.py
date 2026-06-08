"""Tests for the thin Plotly viewer adapter."""

from __future__ import annotations

import asyncio

import numpy as np
import pytest

import nicewidgets.raster_viewer.frontend.plotly_viewer as plotly_viewer_module
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec, RowColBounds
from nicewidgets.raster_viewer.frontend.plotly_coord_transform import PlotlyCoordTransform
from nicewidgets.raster_viewer.frontend.plotly_protocol import PlotlyViewportPayload
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer
from nicewidgets.raster_viewer.frontend.roi_overlay import RectRoiOverlay

_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='', y_unit='')


def test_set_data_initializes_backend_state() -> None:
    """Setting data should initialize backend state and bounds."""
    viewer = PlotlyRasterViewer()
    data = np.arange(32, dtype=np.float32).reshape(4, 8)

    response = asyncio.run(viewer.set_data(data, grid=_GRID))

    assert viewer.has_data is True
    b = viewer.current_bounds
    assert (b.row_min, b.row_max, b.col_min, b.col_max) == (0.0, 4.0, 0.0, 8.0)
    assert response.mode == 'image_png'


def test_build_before_set_data_returns_empty_figure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Building before data is set should create an empty plot."""
    captured: dict[str, object] = {}

    class DummyElement:
        id = 1

        def on(self, *_args, **_kwargs) -> 'DummyElement':
            return self

    class DummyContextMenu:
        def clear(self) -> 'DummyContextMenu':
            return self

        def __enter__(self) -> 'DummyContextMenu':
            return self

        def __exit__(self, *_args) -> None:
            return None

        def open(self) -> None:
            return None

    class DummyUI:
        @staticmethod
        def plotly(figure):
            captured['figure'] = figure
            return DummyElement()

        @staticmethod
        def context_menu() -> DummyContextMenu:
            return DummyContextMenu()

    import types

    monkeypatch.setattr(
        plotly_viewer_module,
        'ui',
        types.SimpleNamespace(plotly=DummyUI.plotly, context_menu=DummyUI.context_menu),
    )

    viewer = PlotlyRasterViewer()
    viewer.build()

    figure = captured['figure']
    assert isinstance(figure, dict)
    assert figure['data'] == []


def test_set_data_auto_enables_square_plot_for_square_source() -> None:
    """Square source arrays should initialize with square Plotly constraints."""
    viewer = PlotlyRasterViewer()
    data = np.arange(16, dtype=np.float32).reshape(4, 4)

    asyncio.run(viewer.set_data(data, grid=_GRID))

    layout = viewer.figure['layout']
    assert viewer.display_options.square_plot is True
    assert layout['xaxis']['constrain'] == 'domain'
    assert layout['yaxis']['constrain'] == 'domain'
    assert layout['yaxis']['scaleanchor'] == 'x'
    assert layout['yaxis']['scaleratio'] == 1.0


def test_set_data_auto_disables_square_plot_for_non_square_source() -> None:
    """Non-square source arrays should initialize without square constraints."""
    viewer = PlotlyRasterViewer()
    data = np.arange(32, dtype=np.float32).reshape(4, 8)

    asyncio.run(viewer.set_data(data, grid=_GRID))

    layout = viewer.figure['layout']
    assert viewer.display_options.square_plot is False
    assert 'constrain' not in layout['xaxis']
    assert 'constrain' not in layout['yaxis']
    assert layout['yaxis']['scaleanchor'] is False
    assert 'scaleratio' not in layout['yaxis']


def test_set_square_plot_can_force_non_square_source_square() -> None:
    """The context-menu action can force square layout for any current source."""
    viewer = PlotlyRasterViewer()
    data = np.arange(32, dtype=np.float32).reshape(4, 8)
    asyncio.run(viewer.set_data(data, grid=_GRID))

    viewer.set_square_plot(True)

    layout = viewer.figure['layout']
    assert viewer.display_options.square_plot is True
    assert layout['xaxis']['constrain'] == 'domain'
    assert layout['yaxis']['constrain'] == 'domain'
    assert layout['yaxis']['scaleanchor'] == 'x'
    assert layout['yaxis']['scaleratio'] == 0.5


def test_set_data_reapplies_auto_square_plot_after_user_toggle() -> None:
    """Loading new data should re-auto-evaluate square layout state."""
    viewer = PlotlyRasterViewer()
    non_square = np.arange(32, dtype=np.float32).reshape(4, 8)
    asyncio.run(viewer.set_data(non_square, grid=_GRID))
    viewer.set_square_plot(True)

    asyncio.run(viewer.set_data(non_square, grid=_GRID))

    layout = viewer.figure['layout']
    assert viewer.display_options.square_plot is False
    assert layout['yaxis']['scaleanchor'] is False
    assert 'scaleratio' not in layout['yaxis']


def test_set_x_axis_range_preserves_y_row_col_extent() -> None:
    """set_x_axis_range should update row span only; column span unchanged."""
    class _DummyClient:
        def run_javascript(self, *_args, **_kwargs) -> None:
            return None

    class _DummyPlot:
        id = 99
        client = _DummyClient()

    viewer = PlotlyRasterViewer()
    viewer._plot = _DummyPlot()
    viewer._transform = PlotlyCoordTransform(nrows=4, ncols=8, grid=_GRID)
    viewer._current_bounds = RowColBounds(
        row_min=0.0,
        row_max=4.0,
        col_min=0.0,
        col_max=8.0,
    )

    asyncio.run(viewer.set_x_axis_range(x_min=1.0, x_max=3.0))

    b = viewer.current_bounds
    assert (b.row_min, b.row_max) == (1.0, 3.0)
    assert (b.col_min, b.col_max) == (0.0, 8.0)


def test_request_before_set_data_raises() -> None:
    """Relayout requests should fail before any dataset is set."""
    viewer = PlotlyRasterViewer()
    payload = PlotlyViewportPayload(relayout={}, width_px=100, height_px=100)
    with pytest.raises(RuntimeError, match='No data set'):
        viewer.request_from_plotly(payload=payload)


def test_set_roi_editing_marks_only_active_shape_editable() -> None:
    """ROI edit mode should make only the target shape editable."""
    viewer = PlotlyRasterViewer()
    viewer.set_rois(
        [
            RectRoiOverlay(roi_id=1, x0=0.0, x1=1.0, y0=0.0, y1=1.0),
            RectRoiOverlay(roi_id=2, x0=2.0, x1=3.0, y0=2.0, y1=3.0),
        ]
    )

    viewer.set_roi_editing(True, 2)

    shapes = viewer.figure['layout']['shapes']
    editable_by_name = {shape['name']: shape['editable'] for shape in shapes}
    assert editable_by_name == {'roi:1': False, 'roi:2': True}
    assert viewer.figure['config']['edits']['shapePosition'] is True


def test_roi_shape_relayout_updates_overlay_and_emits_preview() -> None:
    """Shape relayout during edit mode should update the active ROI preview."""
    previews: list[tuple[int, float, float, float, float]] = []
    viewer = PlotlyRasterViewer(on_roi_bounds_preview=lambda *args: previews.append(args))
    viewer.set_rois([RectRoiOverlay(roi_id=7, x0=1.0, x1=4.0, y0=2.0, y1=5.0)])
    viewer.set_roi_editing(True, 7)

    handled = viewer._handle_roi_shape_relayout(
        {
            'shapes[0].x0': 2.0,
            'shapes[0].x1': 6.0,
            'shapes[0].y0': 3.0,
            'shapes[0].y1': 8.0,
        }
    )

    assert handled is True
    assert previews == [(7, 2.0, 6.0, 3.0, 8.0)]
    shape = viewer.figure['layout']['shapes'][0]
    assert (shape['x0'], shape['x1'], shape['y0'], shape['y1']) == (2.0, 6.0, 3.0, 8.0)
