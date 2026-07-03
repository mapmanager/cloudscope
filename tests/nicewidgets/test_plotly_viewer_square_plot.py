"""Headless tests for PlotlyRasterViewer square layout, padding, and ROI edit mode."""

from __future__ import annotations

import asyncio
import sys
import types

import numpy as np
import pytest

if 'nicegui' not in sys.modules:
    fake_nicegui = types.ModuleType('nicegui')
    fake_nicegui.ui = types.SimpleNamespace()
    fake_nicegui.app = types.SimpleNamespace(native=types.SimpleNamespace(main_window=None))
    sys.modules['nicegui'] = fake_nicegui

from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec, RowColBounds
from nicewidgets.raster_viewer.frontend.plotly_coord_transform import PlotlyCoordTransform
from nicewidgets.raster_viewer.frontend.plotly_viewer import (
    PlotlyRasterViewer,
    _pad_axis_ranges_by_screen_px,
)
from nicewidgets.raster_viewer.frontend.roi_overlay import RectRoiOverlay

_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='', y_unit='')


def test_pad_axis_ranges_by_screen_px_expands_without_moving_center() -> None:
    """Visual ROI padding should expand display ranges in screen-pixel units."""
    padded = _pad_axis_ranges_by_screen_px(
        ((0.0, 100.0), (20.0, 220.0)),
        width_px=400,
        height_px=200,
        padding_px=20,
    )

    flat = tuple(value for pair in padded for value in pair)
    assert flat == pytest.approx((-5.0, 105.0, 0.0, 240.0))


def test_pad_axis_ranges_by_screen_px_preserves_reversed_axis_direction() -> None:
    """Visual padding should expand axes even when Plotly stores a reversed range."""
    padded = _pad_axis_ranges_by_screen_px(
        ((100.0, 0.0), (220.0, 20.0)),
        width_px=400,
        height_px=200,
        padding_px=20,
    )

    flat = tuple(value for pair in padded for value in pair)
    assert flat == pytest.approx((105.0, -5.0, 240.0, 0.0))


def test_clear_data_resets_viewer_to_empty_figure(monkeypatch: pytest.MonkeyPatch) -> None:
    """clear_data should drop backend state and restore an empty figure."""
    captured: dict[str, object] = {}

    class DummyElement:
        id = 1
        figure: dict[str, object] | None = None

        def on(self, *_args, **_kwargs) -> 'DummyElement':
            return self

        def update(self) -> None:
            return None

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

    from nicewidgets.raster_viewer.frontend import plotly_viewer as plotly_viewer_module

    monkeypatch.setattr(
        plotly_viewer_module,
        'ui',
        types.SimpleNamespace(plotly=DummyUI.plotly, context_menu=DummyUI.context_menu),
    )

    viewer = PlotlyRasterViewer()
    data = np.arange(16, dtype=np.float32).reshape(4, 4)
    asyncio.run(viewer.set_data(data, grid=_GRID))
    assert viewer.has_data is True

    asyncio.run(viewer.clear_data())

    assert viewer.has_data is False
    assert viewer.figure['data'] == []


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


def test_visual_padding_does_not_change_roi_shape_coordinates() -> None:
    """Visual axis padding must not alter ROI overlay geometry."""
    viewer = PlotlyRasterViewer()
    roi = RectRoiOverlay(roi_id=9, x0=1.0, x1=4.0, y0=2.0, y1=5.0)
    viewer.set_rois([roi])

    _pad_axis_ranges_by_screen_px(
        ((0.0, 10.0), (0.0, 10.0)),
        width_px=500,
        height_px=500,
        padding_px=16,
    )

    shape = viewer.figure['layout']['shapes'][0]
    assert (shape['x0'], shape['x1'], shape['y0'], shape['y1']) == (1.0, 4.0, 2.0, 5.0)


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
