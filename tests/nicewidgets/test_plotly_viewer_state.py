"""Headless state/math tests for PlotlyRasterViewer.

These tests avoid building the NiceGUI element (``ui.plotly``) and focus on
state transitions, helpers, and Plotly-dict mutations that can be exercised
without a live browser session.
"""

from __future__ import annotations

import asyncio
import sys
import types

import numpy as np
import pytest


if 'nicegui' not in sys.modules:
    fake_nicegui = types.ModuleType('nicegui')
    fake_nicegui.ui = types.SimpleNamespace()
    sys.modules['nicegui'] = fake_nicegui

from nicewidgets.raster_viewer.backend.image_model import (
    RasterGridSpec,
    RowColBounds,
)
from nicewidgets.raster_viewer.frontend.plotly_coord_transform import (
    PlotlyCoordTransform,
    merge_partial_relayout,
)
from nicewidgets.raster_viewer.frontend.plotly_protocol import (
    DEFAULT_HEATMAP_COLORSCALE,
    PlotlyViewportPayload,
    build_plotly_figure,
    parse_relayout_payload,
)
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer
from nicewidgets.raster_viewer.frontend.roi_overlay import RectRoiOverlay
from nicewidgets.raster_viewer.frontend.trace_overlay import PlotlyTraceOverlay


def _grid() -> RasterGridSpec:
    return RasterGridSpec(dx=2.0, dy=4.0, x_unit='s', y_unit='um')


def _viewer_with_data(shape: tuple[int, int] = (10, 8)) -> PlotlyRasterViewer:
    """Build a viewer with data set (no NiceGUI element)."""
    viewer = PlotlyRasterViewer()
    data = np.arange(int(np.prod(shape)), dtype=np.float32).reshape(shape)
    asyncio.run(viewer.set_data(data, grid=_grid()))
    return viewer


# ---------- PlotlyCoordTransform pure math ----------


def test_plot_xy_ranges_to_row_col_round_trip() -> None:
    """Plot coords should round-trip through ``plot_xy_ranges_to_row_col``."""
    grid = _grid()
    t = PlotlyCoordTransform(nrows=10, ncols=8, grid=grid)
    bounds = RowColBounds(row_min=2.0, row_max=8.0, col_min=1.0, col_max=6.0)
    x_lo, x_hi = t.row_col_to_plot_x_range(bounds)
    y_lo, y_hi = t.row_col_to_plot_y_range(bounds)

    back = t.plot_xy_ranges_to_row_col(x_lo, x_hi, y_lo, y_hi)

    assert back.row_min == pytest.approx(2.0)
    assert back.row_max == pytest.approx(8.0)
    assert back.col_min == pytest.approx(1.0)
    assert back.col_max == pytest.approx(6.0)


def test_row_col_to_plot_y_range_is_bottom_up() -> None:
    """Y-axis layout ranges should be ordered low to high for bottom-left origin."""
    grid = _grid()
    t = PlotlyCoordTransform(nrows=10, ncols=8, grid=grid)
    bounds = RowColBounds(row_min=0.0, row_max=10.0, col_min=1.0, col_max=6.0)

    assert t.row_col_to_plot_y_range(bounds) == (4.0, 24.0)


def test_plot_xy_ranges_to_row_col_clips_to_shape() -> None:
    """Out-of-range plot coords should be clipped to the source shape."""
    t = PlotlyCoordTransform(nrows=4, ncols=4, grid=_grid())
    back = t.plot_xy_ranges_to_row_col(-100.0, 100.0, -100.0, 100.0)

    assert back.row_min == 0.0
    assert back.row_max == 4.0
    assert back.col_min == 0.0
    assert back.col_max == 4.0


def test_full_row_col_bounds_returns_full_array() -> None:
    """``full_row_col_bounds`` should span the entire source array."""
    t = PlotlyCoordTransform(nrows=12, ncols=5, grid=_grid())
    b = t.full_row_col_bounds()

    assert b.row_min == 0.0
    assert b.row_max == 12.0
    assert b.col_min == 0.0
    assert b.col_max == 5.0


# ---------- merge_partial_relayout ----------


def test_merge_partial_relayout_fills_missing_y() -> None:
    """Missing y range should be filled from fallback bounds."""
    t = PlotlyCoordTransform(nrows=10, ncols=8, grid=_grid())
    fallback = RowColBounds(row_min=0, row_max=10, col_min=0, col_max=8)
    relayout = {'xaxis.range': [0.0, 5.0]}

    merged = merge_partial_relayout(relayout, t, fallback)

    assert 'xaxis.range' in merged
    assert 'yaxis.range' in merged


def test_merge_partial_relayout_fills_missing_x() -> None:
    """Missing x range should be filled from fallback bounds."""
    t = PlotlyCoordTransform(nrows=10, ncols=8, grid=_grid())
    fallback = RowColBounds(row_min=0, row_max=10, col_min=0, col_max=8)
    relayout = {'yaxis.range': [0.0, 10.0]}

    merged = merge_partial_relayout(relayout, t, fallback)

    assert 'xaxis.range' in merged
    assert 'yaxis.range' in merged


def test_merge_partial_relayout_keeps_existing_ranges() -> None:
    """Existing range keys should be preserved verbatim."""
    t = PlotlyCoordTransform(nrows=10, ncols=8, grid=_grid())
    fallback = RowColBounds(row_min=0, row_max=10, col_min=0, col_max=8)
    relayout = {
        'xaxis.range': [1.0, 2.0],
        'yaxis.range': [3.0, 4.0],
    }

    merged = merge_partial_relayout(relayout, t, fallback)

    assert merged['xaxis.range'] == [1.0, 2.0]
    assert merged['yaxis.range'] == [3.0, 4.0]


def test_merge_partial_relayout_accepts_bracket_keys() -> None:
    """Bracketed range keys (e.g. ``xaxis.range[0]``) should satisfy ``has_x``."""
    t = PlotlyCoordTransform(nrows=10, ncols=8, grid=_grid())
    fallback = RowColBounds(row_min=0, row_max=10, col_min=0, col_max=8)
    relayout = {'xaxis.range[0]': 0.5, 'xaxis.range[1]': 1.5}

    merged = merge_partial_relayout(relayout, t, fallback)

    assert 'xaxis.range[0]' in merged
    assert 'xaxis.range[1]' in merged
    assert 'yaxis.range' in merged
    assert 'xaxis.range' not in merged


# ---------- plotly_protocol helpers ----------


def test_parse_relayout_payload_returns_view_request() -> None:
    """Parsing a relayout payload should return a ViewRequest with bounds and viewport."""
    t = PlotlyCoordTransform(nrows=10, ncols=8, grid=_grid())
    fallback = RowColBounds(row_min=0, row_max=10, col_min=0, col_max=8)
    payload = PlotlyViewportPayload(
        relayout={'xaxis.range': [0.0, 20.0], 'yaxis.range': [0.0, 32.0]},
        width_px=300,
        height_px=200,
    )

    req = parse_relayout_payload(payload, t, fallback)

    assert req.viewport.width_px == 300
    assert req.viewport.height_px == 200
    assert req.bounds.row_min == pytest.approx(0.0)
    assert req.bounds.row_max == pytest.approx(10.0)


def test_parse_relayout_payload_uses_fallback_for_missing_axis() -> None:
    """Missing axis keys should fall back to ``fallback_bounds``."""
    t = PlotlyCoordTransform(nrows=10, ncols=8, grid=_grid())
    fallback = RowColBounds(row_min=0, row_max=10, col_min=0, col_max=8)
    payload = PlotlyViewportPayload(
        relayout={},
        width_px=200,
        height_px=100,
    )

    req = parse_relayout_payload(payload, t, fallback)

    assert req.bounds.row_min == pytest.approx(0.0)
    assert req.bounds.row_max == pytest.approx(10.0)
    assert req.bounds.col_min == pytest.approx(0.0)
    assert req.bounds.col_max == pytest.approx(8.0)


def test_parse_relayout_payload_reads_bracket_keys() -> None:
    """``xaxis.range[0]`` / ``[1]`` keys should be honored when list key absent."""
    t = PlotlyCoordTransform(nrows=10, ncols=8, grid=_grid())
    fallback = RowColBounds(row_min=0, row_max=10, col_min=0, col_max=8)
    payload = PlotlyViewportPayload(
        relayout={
            'xaxis.range[0]': 0.0,
            'xaxis.range[1]': 4.0,
            'yaxis.range[0]': 0.0,
            'yaxis.range[1]': 16.0,
        },
        width_px=100,
        height_px=100,
    )

    req = parse_relayout_payload(payload, t, fallback)

    assert req.bounds.row_min == pytest.approx(0.0)
    assert req.bounds.row_max == pytest.approx(2.0)


def test_build_plotly_figure_image_mode() -> None:
    """``image_png`` mode should produce a Plotly image trace."""
    from nicewidgets.raster_viewer.backend.image_model import RenderResponse

    response = RenderResponse(
        mode='image_png',
        level=0,
        bounds=RowColBounds(row_min=0, row_max=4, col_min=0, col_max=4),
        shape=(4, 4),
        grid=_grid(),
        x0=0.0,
        y0=0.0,
        dx=2.0,
        dy=4.0,
        png_data_uri='data:image/png;base64,AAA',
    )

    fig = build_plotly_figure(response, uirevision='ui-1')

    assert fig['data'][0]['type'] == 'image'
    assert fig['data'][0]['source'] == 'data:image/png;base64,AAA'
    assert fig['layout']['yaxis']['range'] == [0.0, 16.0]
    assert fig['layout']['uirevision'] == 'ui-1'


def test_build_plotly_figure_heatmap_mode() -> None:
    """``heatmap_z`` mode should produce a Plotly heatmap trace with z data."""
    from nicewidgets.raster_viewer.backend.image_model import RenderResponse

    z = np.array([[1.0, 2.0], [3.0, 4.0]])
    response = RenderResponse(
        mode='heatmap_z',
        level=0,
        bounds=RowColBounds(row_min=0, row_max=2, col_min=0, col_max=2),
        shape=(2, 2),
        grid=_grid(),
        x0=0.0,
        y0=0.0,
        dx=2.0,
        dy=4.0,
        z=z,
        zmin=1.0,
        zmax=4.0,
    )

    fig = build_plotly_figure(response, heatmap_colorscale='Viridis')

    assert fig['data'][0]['type'] == 'heatmap'
    assert fig['data'][0]['colorscale'] == 'Viridis'
    assert fig['data'][0]['z'] == [[1.0, 2.0], [3.0, 4.0]]


def test_build_plotly_figure_heatmap_requires_z() -> None:
    """Heatmap mode without z data should raise ``ValueError``."""
    from nicewidgets.raster_viewer.backend.image_model import RenderResponse

    response = RenderResponse(
        mode='heatmap_z',
        level=0,
        bounds=RowColBounds(row_min=0, row_max=2, col_min=0, col_max=2),
        shape=(2, 2),
        grid=_grid(),
        x0=0.0,
        y0=0.0,
        dx=2.0,
        dy=4.0,
    )

    with pytest.raises(ValueError, match='numeric z data'):
        build_plotly_figure(response)


# ---------- PlotlyRasterViewer initial state ----------


def test_viewer_initial_state() -> None:
    """A freshly-constructed viewer should have no data, plot, or transform."""
    viewer = PlotlyRasterViewer()

    assert viewer.has_data is False
    assert viewer.plot is None
    assert isinstance(viewer.figure, dict)
    assert isinstance(viewer.current_bounds, RowColBounds)


def test_new_uirevision_returns_unique_strings() -> None:
    """``_new_uirevision`` should produce unique non-empty strings."""
    a = PlotlyRasterViewer._new_uirevision()
    b = PlotlyRasterViewer._new_uirevision()

    assert isinstance(a, str) and a
    assert isinstance(b, str) and b
    assert a != b


def test_build_initial_figure_no_data_returns_scaffold() -> None:
    """Without data, ``_build_initial_figure`` should return an empty scaffold."""
    viewer = PlotlyRasterViewer()
    fig = viewer._build_initial_figure()

    assert fig['data'] == []
    assert 'layout' in fig
    assert fig['layout']['autosize'] is True
    assert 'config' in fig


def test_display_style_uses_defaults() -> None:
    """``_display_style`` should reflect default colorscale and unset contrast."""
    viewer = PlotlyRasterViewer()
    style = viewer._display_style()

    assert style.colorscale == DEFAULT_HEATMAP_COLORSCALE
    assert style.zmin is None
    assert style.zmax is None


def test_js_plotly_graph_div_returns_early_without_plot() -> None:
    """Without a built plot element, the JS snippet should short-circuit."""
    viewer = PlotlyRasterViewer()

    assert viewer._js_plotly_graph_div() == 'return;'


def test_layout_pin_xy_ranges_writes_axis_ranges() -> None:
    """``_layout_pin_xy_ranges`` should pin axes in the plotly dict."""
    viewer = PlotlyRasterViewer()
    viewer._layout_pin_xy_ranges(x_lo=1.0, x_hi=5.0, y_lo=2.0, y_hi=10.0)

    layout = viewer._plotly_dict['layout']
    assert layout['xaxis']['range'] == [1.0, 5.0]
    assert layout['xaxis']['autorange'] is False
    assert layout['yaxis']['range'] == [2.0, 10.0]
    assert layout['yaxis']['autorange'] is False


def test_heatmap_and_image_trace_active_return_false_when_no_plot() -> None:
    """Both trace detection helpers should return False without a built plot."""
    viewer = PlotlyRasterViewer()

    assert viewer._heatmap_trace_active() is False
    assert viewer._image_trace_active() is False


# ---------- set_data side effects ----------


def test_set_data_populates_service_transform_and_bounds() -> None:
    """``set_data`` should configure service, transform, bounds, and revision."""
    viewer = _viewer_with_data(shape=(10, 8))

    assert viewer.has_data is True
    assert viewer._service is not None
    assert viewer._transform is not None
    assert viewer.current_bounds.row_min == 0.0
    assert viewer.current_bounds.row_max == 10.0
    assert viewer.current_bounds.col_min == 0.0
    assert viewer.current_bounds.col_max == 8.0


def test_set_data_resets_contrast_and_colorscale() -> None:
    """``set_data`` should reset contrast window and colorscale to defaults."""
    viewer = PlotlyRasterViewer()
    viewer._contrast_zmin = 0.1
    viewer._contrast_zmax = 0.9
    viewer._heatmap_colorscale = 'Viridis'

    asyncio.run(viewer.set_data(np.zeros((4, 4), dtype=np.float32), grid=_grid()))

    assert viewer._contrast_zmin is None
    assert viewer._contrast_zmax is None
    assert viewer._heatmap_colorscale == DEFAULT_HEATMAP_COLORSCALE


def test_set_data_clears_existing_trace_overlays() -> None:
    """``set_data`` should clear previously-added trace overlays."""
    viewer = PlotlyRasterViewer()
    viewer.add_trace_overlay(PlotlyTraceOverlay(trace_id='t', x=[0.0], y=[0.0]))

    asyncio.run(viewer.set_data(np.zeros((4, 4), dtype=np.float32), grid=_grid()))

    figure_data = viewer.figure.get('data', [])
    assert isinstance(figure_data, list)
    assert len(figure_data) == 1  # only the raster trace remains


def test_set_data_then_build_initial_figure_returns_full_figure() -> None:
    """After ``set_data``, ``_build_initial_figure`` should include a raster trace."""
    viewer = _viewer_with_data(shape=(4, 4))

    fig = viewer._build_initial_figure()

    assert isinstance(fig['data'], list)
    assert len(fig['data']) == 1
    assert fig['data'][0]['type'] in {'image', 'heatmap'}


# ---------- ROI overlay state (no plot element) ----------


def test_set_rois_syncs_layout_shapes() -> None:
    """``set_rois`` should sync overlay rectangles into ``layout.shapes``."""
    viewer = PlotlyRasterViewer()
    roi = RectRoiOverlay(roi_id=1, x0=0.0, x1=2.0, y0=0.0, y1=4.0, label='r1')
    viewer.set_rois([roi])

    shapes = viewer._plotly_dict['layout']['shapes']
    assert len(shapes) == 1
    assert shapes[0]['name'] == 'roi:1'


def test_add_roi_appends_shape() -> None:
    """``add_roi`` should append a new shape into the plotly dict."""
    viewer = PlotlyRasterViewer()
    viewer.add_roi(RectRoiOverlay(roi_id=2, x0=0.0, x1=1.0, y0=0.0, y1=1.0))

    shapes = viewer._plotly_dict['layout']['shapes']
    assert any(s.get('name') == 'roi:2' for s in shapes)


def test_delete_roi_removes_shape() -> None:
    """``delete_roi`` should remove the matching shape from the plotly dict."""
    viewer = PlotlyRasterViewer()
    viewer.add_roi(RectRoiOverlay(roi_id=2, x0=0.0, x1=1.0, y0=0.0, y1=1.0))
    viewer.add_roi(RectRoiOverlay(roi_id=3, x0=0.0, x1=1.0, y0=0.0, y1=1.0))

    viewer.delete_roi(2)

    shapes = viewer._plotly_dict['layout']['shapes']
    names = {s.get('name') for s in shapes}
    assert 'roi:2' not in names
    assert 'roi:3' in names


def test_select_roi_marks_selection() -> None:
    """``select_roi`` should update the ROI layer's selection state."""
    viewer = PlotlyRasterViewer()
    viewer.add_roi(RectRoiOverlay(roi_id=7, x0=0.0, x1=1.0, y0=0.0, y1=1.0))

    viewer.select_roi(7)

    assert viewer._plotly_rois.selected_roi_id == 7


def test_sync_roi_shapes_handles_non_list_existing_shapes() -> None:
    """``_sync_roi_shapes_to_plotly_dict`` should tolerate a non-list ``shapes``."""
    viewer = PlotlyRasterViewer()
    viewer._plotly_dict['layout'] = {'shapes': 'not a list'}
    viewer.add_roi(RectRoiOverlay(roi_id=1, x0=0.0, x1=1.0, y0=0.0, y1=1.0))

    shapes = viewer._plotly_dict['layout']['shapes']
    assert isinstance(shapes, list)
    assert any(s.get('name') == 'roi:1' for s in shapes)


# ---------- Trace overlay state (no plot element) ----------


def test_set_trace_overlays_syncs_data_traces() -> None:
    """``set_trace_overlays`` should merge overlay traces into ``data``."""
    viewer = PlotlyRasterViewer()
    overlay = PlotlyTraceOverlay(trace_id='left', x=[0.0, 1.0], y=[2.0, 3.0])

    viewer.set_trace_overlays([overlay])

    data = viewer._plotly_dict.get('data', [])
    assert isinstance(data, list)
    assert len(data) >= 1


def test_delete_trace_overlay_removes_trace() -> None:
    """``delete_trace_overlay`` should remove the matching overlay."""
    viewer = PlotlyRasterViewer()
    viewer.add_trace_overlay(PlotlyTraceOverlay(trace_id='a', x=[0.0], y=[0.0]))
    viewer.add_trace_overlay(PlotlyTraceOverlay(trace_id='b', x=[0.0], y=[0.0]))

    viewer.delete_trace_overlay('a')

    overlays = viewer._plotly_trace_overlays
    ids = {o.trace_id for o in overlays.overlays}
    assert 'a' not in ids
    assert 'b' in ids


def test_clear_trace_overlays_removes_all() -> None:
    """``clear_trace_overlays`` should drop every overlay."""
    viewer = PlotlyRasterViewer()
    viewer.add_trace_overlay(PlotlyTraceOverlay(trace_id='a', x=[0.0], y=[0.0]))
    viewer.add_trace_overlay(PlotlyTraceOverlay(trace_id='b', x=[0.0], y=[0.0]))

    viewer.clear_trace_overlays()

    assert list(viewer._plotly_trace_overlays.overlays) == []


def test_sync_trace_overlays_handles_non_list_data() -> None:
    """``_sync_trace_overlays_to_plotly_dict`` should tolerate non-list ``data``."""
    viewer = PlotlyRasterViewer()
    viewer._plotly_dict['data'] = 'not a list'

    viewer.add_trace_overlay(PlotlyTraceOverlay(trace_id='x', x=[0.0], y=[0.0]))

    data = viewer._plotly_dict['data']
    assert isinstance(data, list)


# ---------- request_from_plotly / apply_response / async error paths ----------


def test_request_from_plotly_raises_without_data() -> None:
    """``request_from_plotly`` should raise before ``set_data``."""
    viewer = PlotlyRasterViewer()
    payload = PlotlyViewportPayload(relayout={}, width_px=10, height_px=10)

    with pytest.raises(RuntimeError, match='No data set'):
        viewer.request_from_plotly(payload)


def test_request_from_plotly_returns_view_request_after_set_data() -> None:
    """After ``set_data``, ``request_from_plotly`` should return a ViewRequest."""
    viewer = _viewer_with_data(shape=(8, 4))
    payload = PlotlyViewportPayload(
        relayout={'xaxis.range': [0.0, 16.0], 'yaxis.range': [0.0, 16.0]},
        width_px=200,
        height_px=100,
    )

    req = viewer.request_from_plotly(payload)

    assert req.viewport.width_px == 200
    assert req.viewport.height_px == 100


def test_apply_response_raises_when_plot_not_built() -> None:
    """``apply_response`` should raise if the viewer was never built."""
    from nicewidgets.raster_viewer.backend.image_model import RenderResponse

    viewer = PlotlyRasterViewer()
    response = RenderResponse(
        mode='image_png',
        level=0,
        bounds=RowColBounds(row_min=0, row_max=1, col_min=0, col_max=1),
        shape=(1, 1),
        grid=_grid(),
        x0=0.0,
        y0=0.0,
        dx=1.0,
        dy=1.0,
        png_data_uri='data:image/png;base64,AAA',
    )

    with pytest.raises(RuntimeError, match='Viewer must be built'):
        asyncio.run(viewer.apply_response(response))


def test_set_axis_ranges_raises_when_not_built() -> None:
    """``set_axis_ranges`` should raise without a built plot."""
    viewer = PlotlyRasterViewer()

    with pytest.raises(RuntimeError, match='must be built'):
        asyncio.run(viewer.set_axis_ranges(x_min=0.0, x_max=1.0, y_min=0.0, y_max=1.0))


def test_set_x_axis_range_raises_when_not_built() -> None:
    """``set_x_axis_range`` should raise without a built plot."""
    viewer = PlotlyRasterViewer()

    with pytest.raises(RuntimeError, match='must be built'):
        asyncio.run(viewer.set_x_axis_range(x_min=0.0, x_max=1.0))


def test_set_heatmap_contrast_raises_when_no_trace_active() -> None:
    """``set_heatmap_contrast`` should raise when there is no raster trace."""
    viewer = PlotlyRasterViewer()

    with pytest.raises(RuntimeError, match='No raster trace'):
        asyncio.run(viewer.set_heatmap_contrast(zmin=0.0, zmax=1.0))


def test_set_heatmap_colorscale_raises_when_no_trace_active() -> None:
    """``set_heatmap_colorscale`` should raise when there is no raster trace."""
    viewer = PlotlyRasterViewer()

    with pytest.raises(RuntimeError, match='No raster trace'):
        asyncio.run(viewer.set_heatmap_colorscale('Viridis'))


# ---------- async event handlers (early-return paths) ----------


def test_on_plotly_doubleclick_no_op_without_service() -> None:
    """Doubleclick should be a no-op when no data is loaded."""
    viewer = PlotlyRasterViewer()

    asyncio.run(viewer._on_plotly_doubleclick(types.SimpleNamespace(args={})))


def test_on_plotly_autosize_returns_none() -> None:
    """Autosize handler is a no-op returning None."""
    viewer = PlotlyRasterViewer()

    result = asyncio.run(viewer._on_plotly_autosize(types.SimpleNamespace(args={})))
    assert result is None


def test_on_plotly_relayout_no_op_without_service() -> None:
    """Relayout should early-return when no data is loaded."""
    viewer = PlotlyRasterViewer()

    asyncio.run(viewer._on_plotly_relayout(types.SimpleNamespace(args={'xaxis.range': [0, 1]})))


def test_on_plotly_relayout_ignores_unrelated_args() -> None:
    """Relayout should early-return when args don't contain axis range keys."""
    viewer = _viewer_with_data(shape=(4, 4))
    viewer._plot = types.SimpleNamespace(id='p')

    asyncio.run(viewer._on_plotly_relayout(types.SimpleNamespace(args={'dragmode': 'pan'})))
