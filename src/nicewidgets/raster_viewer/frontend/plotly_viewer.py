"""Thin NiceGUI Plotly adapter for raster viewing."""

from __future__ import annotations

import asyncio
import json
import math
from pprint import pprint
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING
from uuid import uuid4

import numpy as np
from nicegui import ui

from nicewidgets.raster_viewer.backend.image_model import (
    BackendImage,
    RasterDisplayStyle,
    RasterGridSpec,
    RenderResponse,
    RowColBounds,
)
from nicewidgets.raster_viewer.backend.pyramid import ImagePyramid
from nicewidgets.raster_viewer.backend.raster_service import RasterViewService
from nicewidgets.raster_viewer.frontend.plotly_coord_transform import (
    PlotlyCoordTransform,
    merge_partial_relayout,
)
from nicewidgets.raster_viewer.frontend.plotly_clipboard import (
    copy_plotly_png_to_browser_clipboard,
    copy_png_bytes_to_native_clipboard,
    get_plotly_png_bytes,
)
from nicewidgets.utils.clipboard import is_pywebview_desktop
from nicewidgets.raster_viewer.frontend.plotly_context_menu import (
    PlotlyRasterViewerContextMenu,
)
from nicewidgets.raster_viewer.frontend.plotly_display_options import (
    PlotlyRasterViewerDisplayOptions,
)
from nicewidgets.plotly_theme import (
    PlotlyThemeName,
    apply_plotly_theme_to_layout,
    normalize_plotly_theme,
)
from nicewidgets.raster_viewer.frontend.roi_overlay import (
    PlotlyRoiOverlayLayer,
    RectRoiOverlay,
)
from nicewidgets.raster_viewer.frontend.trace_overlay import (
    PlotlyTraceOverlay,
    PlotlyTraceOverlayLayer,
)
from nicewidgets.raster_viewer.frontend.plotly_protocol import (
    DEFAULT_HEATMAP_COLORSCALE,
    RASTER_VIEWER_PLOTLY_CONFIG,
    PlotlyViewportPayload,
    build_plotly_figure,
    parse_relayout_payload,
)

from nicewidgets.utils.logging import get_logger

if TYPE_CHECKING:
    from nicegui.element import Element

logger = get_logger(__name__)

# Plotly accepts a colorscale either as a built-in name (e.g. ``'Greys'``) or as
# a list of ``[stop, color]`` pairs (e.g. ``[[0, 'rgb(255,255,255)'], [1, 'rgb(0,0,0)']]``).
# Both heatmap traces and the PNG encoder via ``plotly.colors.sample_colorscale``
# accept either form, so we surface the union through the public API.
PlotlyColorscale = str | list[list[float | str]]

# Callback for user-driven x-axis range changes (relayout / double-click reset).
# ``(None, None)`` means "auto / reset to full extent".
OnPlotlyXRangeChanged = Callable[[float | None, float | None], None]
OnRoiBoundsPreview = Callable[[int, float, float, float, float], None]

_X_RANGE_ECHO_EPS = 1e-9
_RELAYOUT_RENDER_DEBOUNCE_SECONDS = 0.12



def _summarize_plotly_event_args(obj: object) -> object:
    """Return Plotly event args with large raster payloads summarized for logs."""
    if isinstance(obj, dict):
        return {key: _summarize_plotly_event_args(value) for key, value in obj.items()}
    if isinstance(obj, list):
        # Plotly restyle wraps trace attributes in one-element lists, e.g.
        # {'z': [[[...]]]} or {'source': ['data:image/png;base64,...']}.
        if len(obj) == 1 and isinstance(obj[0], list):
            inner = obj[0]
            if inner and all(isinstance(row, list) for row in inner):
                rows = len(inner)
                cols = len(inner[0]) if rows else 0
                return f'<2D array shape=({rows}, {cols})>'
        if len(obj) == 1 and isinstance(obj[0], str) and obj[0].startswith('data:image'):
            return f'<image source len={len(obj[0])}>'
        if len(obj) > 20:
            return f'<list len={len(obj)}>'
    return obj

def _range_pair_equal(
    a: tuple[float | None, float | None],
    b: tuple[float | None, float | None],
) -> bool:
    """Compare two numeric range pairs with float tolerance and ``None`` support."""
    for av, bv in zip(a, b, strict=True):
        if av is None or bv is None:
            if av is not bv:
                return False
            continue
        if not (math.isfinite(av) and math.isfinite(bv)):
            return False
        if abs(av - bv) > _X_RANGE_ECHO_EPS:
            return False
    return True


def _x_range_equal(
    a: tuple[float | None, float | None],
    b: tuple[float | None, float | None],
) -> bool:
    """Compare two ``(x_min, x_max)`` pairs with float tolerance and ``None`` support."""
    return _range_pair_equal(a, b)


class PlotlyRasterViewer:
    """Small frontend adapter around :class:`RasterViewService`.

    Converts Plotly/NiceGUI events to the backend service API. Row/column
    bounds live in the backend; plot coordinates use :class:`PlotlyCoordTransform`.
    """

    def __init__(
        self,
        *,
        display_options: PlotlyRasterViewerDisplayOptions | None = None,
        on_x_range_changed: OnPlotlyXRangeChanged | None = None,
        on_roi_bounds_preview: OnRoiBoundsPreview | None = None,
    ) -> None:
        self._plot: Element | None = None
        self._service: RasterViewService | None = None
        self._plotly_dict: dict[str, object] = {}
        self._on_x_range_changed = on_x_range_changed
        self._on_roi_bounds_preview = on_roi_bounds_preview
        # Last x-range applied via set_x_axis_range / set_data / double-click
        # reset; used to suppress echo relayouts that Plotly fires whenever
        # the x-axis range changes (whether user- or programmatic).
        self._last_applied_x_range: tuple[float | None, float | None] | None = None
        self._current_bounds = RowColBounds(
            row_min=0.0,
            row_max=1.0,
            col_min=0.0,
            col_max=1.0,
        )
        self._transform: PlotlyCoordTransform | None = None
        self._uirevision = self._new_uirevision()
        self._heatmap_colorscale: PlotlyColorscale = DEFAULT_HEATMAP_COLORSCALE
        self._contrast_zmin: float | None = None
        self._contrast_zmax: float | None = None
        # Pixel budget for full-extent overview PNGs. ``None`` keeps the
        # service's conservative coarse overview; a value lets small images
        # render at full resolution. Set per dataset via ``set_data``.
        self._overview_max_pixels: int | None = None
        self._plotly_rois = PlotlyRoiOverlayLayer()
        self._plotly_trace_overlays = PlotlyTraceOverlayLayer()
        self._display_options = display_options or PlotlyRasterViewerDisplayOptions()
        self._axis_title_texts: dict[str, str] = {'xaxis': '', 'yaxis': ''}
        self._square_plot_scaleratio = 1.0
        self._ctx_menu: ui.context_menu | None = None
        self._context_menu_builder: PlotlyRasterViewerContextMenu | None = None
        self._pending_relayout_render: dict[str, object] | None = None
        # Relayout currently being rendered by the debounce task. Plotly can
        # emit a normalized relayout follow-up after the task has already moved
        # the pending viewport into this in-flight state; keep it here so that
        # follow-up cannot schedule a second render with stale/full y limits.
        self._active_relayout_render: dict[str, object] | None = None
        self._relayout_render_task: asyncio.Task[None] | None = None
        # Last successful browser plot size measurement. Relayout raster
        # refreshes may run from a debounced task without NiceGUI's implicit
        # callback context; this cache lets those refreshes continue when a
        # fresh browser measurement is temporarily unavailable.
        self._last_viewport_size_px: tuple[int, int] | None = None
        # Last axis ranges the browser should display, in Plotly coordinates.
        # User relayouts are source-of-truth for these ranges; backend render
        # bounds may be quantized/padded for pyramid rendering and should not
        # replace the displayed viewport.
        self._last_display_axis_ranges: tuple[tuple[float, float], tuple[float, float]] | None = None
        # Last display ranges pushed by this viewer. Plotly emits relayout
        # events after full figure updates; matching events are self-echoes,
        # not new user input, and should not schedule another raster refresh.
        self._last_applied_display_axis_ranges: tuple[tuple[float, float], tuple[float, float]] | None = None
        # Relayout-driven raster refreshes can trigger a follow-up Plotly
        # relayout after this viewer pushes trace data or a replacement
        # figure. This one-shot latch prevents that programmatic echo from
        # being treated as a new user wheel/drag gesture.
        self._ignore_next_programmatic_relayout = False

    def _js_plotly_graph_div(self) -> str:
        """Resolve the Plotly graph div from NiceGUI; bail out if missing (cf. ``el.data`` guard)."""
        if self._plot is None:
            return 'return;'
        plot_id = self._plot.id
        return f"""const host = getElement({plot_id}).$el;
if (!host) return;
const plotDiv = host.querySelector('.js-plotly-plot') || host;
if (!plotDiv || !plotDiv.data) return;
"""

    def _layout_pin_xy_ranges(self, *, x_lo: float, x_hi: float, y_lo: float, y_hi: float) -> None:
        """Mirror axis state in :attr:`_plotly_dict` for the next full figure push (like ``plot_dict`` sync)."""
        layout = self._plotly_dict.setdefault('layout', {})
        xaxis = layout.setdefault('xaxis', {})
        yaxis = layout.setdefault('yaxis', {})
        xaxis['autorange'] = False
        yaxis['autorange'] = False
        xaxis['range'] = [x_lo, x_hi]
        yaxis['range'] = [y_lo, y_hi]

    @property
    def current_bounds(self) -> RowColBounds:
        """Return the most recent backend row/column bounds."""
        return self._current_bounds

    @property
    def has_data(self) -> bool:
        """Return ``True`` when a dataset has been set."""
        return self._service is not None

    @property
    def plot(self) -> Element | None:
        """Return the NiceGUI Plotly element."""
        return self._plot

    @property
    def figure(self) -> dict[str, object]:
        """Return the current figure dictionary."""
        return self._plotly_dict

    @property
    def display_options(self) -> PlotlyRasterViewerDisplayOptions:
        """Return mutable display options used by context-menu actions."""
        return self._display_options

    def build(self) -> Element:
        """Create the NiceGUI Plotly element."""
        self._plotly_dict = self._build_initial_figure()

        self._plot = ui.plotly(self._plotly_dict)
        self._plot.on('plotly_relayout', self._on_plotly_relayout)
        self._plot.on('plotly_restyle', self._on_plotly_restyle)
        self._plot.on('plotly_autosize', self._on_plotly_autosize)
        self._plot.on('plotly_doubleclick', self._on_plotly_doubleclick)
        self._ctx_menu = ui.context_menu()
        self._context_menu_builder = PlotlyRasterViewerContextMenu(get_viewer=lambda: self)
        self._plot.on('contextmenu', self._on_context_menu_event)

        return self._plot

    async def set_data(
        self,
        data: np.ndarray,
        *,
        grid: RasterGridSpec,
        overview_max_pixels: int | None = None,
    ) -> RenderResponse:
        """Set a new 2D dataset and fully refresh the plot.

        Args:
            data: New full-resolution 2D array ``(rows, columns)``.
            grid: Physical spacing and axis labels (``dx``/``dy`` must be positive).
            overview_max_pixels: Optional pixel budget for full-extent overview
                PNGs (initial render and double-click reset). When ``None``, the
                service's conservative coarse overview is used. A value lets
                small images render the full extent at full resolution so the
                overview matches the zoomed-in heatmap.

        Returns:
            Initial full-image PNG response for the new dataset.
        """
        self._cancel_pending_relayout_render()
        source = BackendImage(data, grid=grid)
        self._display_options.square_plot = source.height == source.width
        self._square_plot_scaleratio = self._square_plot_scaleratio_for_source(source)
        pyramid = ImagePyramid(source)
        self._service = RasterViewService(
            source=source,
            pyramid=pyramid,
        )
        self._transform = PlotlyCoordTransform(
            nrows=source.height,
            ncols=source.width,
            grid=grid,
        )
        self._axis_title_texts = {'xaxis': grid.x_unit or '', 'yaxis': grid.y_unit or ''}
        self._current_bounds = self._transform.full_row_col_bounds()
        self._uirevision = self._new_uirevision()
        self._heatmap_colorscale = DEFAULT_HEATMAP_COLORSCALE
        self._contrast_zmin = None
        self._contrast_zmax = None
        self._overview_max_pixels = overview_max_pixels
        self._plotly_trace_overlays.clear_overlays()

        response = self._service.full_image_png(
            display_style=self._display_style(),
            max_pixels=self._overview_max_pixels,
        )
        self._current_bounds = response.bounds
        # Pin echo dedup to the new data extent so the follow-up
        # ``plotly_relayout`` Plotly fires after ``_uirevision`` rotation
        # (carrying the auto-ranged data extent) is suppressed by value, not by
        # a one-shot guard. ``_is_x_range_echo`` compares with float tolerance.
        x_lo_data, x_hi_data = self._transform.row_col_to_plot_x_range(self._current_bounds)
        y_lo_data, y_hi_data = self._transform.row_col_to_plot_y_range(self._current_bounds)
        display_axis_ranges = ((x_lo_data, x_hi_data), (y_lo_data, y_hi_data))
        self._last_applied_x_range = (x_lo_data, x_hi_data)
        self._last_display_axis_ranges = display_axis_ranges
        self._last_applied_display_axis_ranges = display_axis_ranges
        self._plotly_dict = build_plotly_figure(
            response=response,
            uirevision=self._uirevision,
            heatmap_colorscale=self._heatmap_colorscale,
        )
        self._sync_roi_shapes_to_plotly_dict()
        self._sync_trace_overlays_to_plotly_dict()
        self._apply_display_options_to_plotly_dict()

        if self._plot is not None:
            self._plot.figure = self._plotly_dict
            self._plot.update()
        return response

    async def clear_data(self) -> None:
        """Remove the current dataset and show an empty Plotly figure.

        Returns:
            None.
        """
        self._cancel_pending_relayout_render()
        self._service = None
        self._transform = None
        self._overview_max_pixels = None
        self._last_applied_x_range = None
        self._last_display_axis_ranges = None
        self._last_applied_display_axis_ranges = None
        self._ignore_next_programmatic_relayout = False
        self._last_viewport_size_px = None
        self._heatmap_colorscale = DEFAULT_HEATMAP_COLORSCALE
        self._contrast_zmin = None
        self._contrast_zmax = None
        self._axis_title_texts = {'xaxis': '', 'yaxis': ''}
        self._plotly_trace_overlays.clear_overlays()
        self._plotly_rois.set_rois([])
        self._uirevision = self._new_uirevision()
        self._plotly_dict = self._build_initial_figure()
        if self._plot is not None:
            self._plot.figure = self._plotly_dict
            self._plot.update()

    async def apply_response(
        self,
        response: RenderResponse,
        *,
        display_axis_ranges: tuple[tuple[float, float], tuple[float, float]] | None = None,
    ) -> None:
        """Apply a backend response to the browser-side Plotly plot.

        Args:
            response: Rendered raster data for the requested backend bounds.
            display_axis_ranges: Optional ``((x0, x1), (y0, y1))`` viewport
                chosen by Plotly before a relayout-driven raster refresh. When
                provided, preserve these axis ranges while swapping the raster
                trace/pyramid data from ``response``.
        """
        if self._plot is None:
            raise RuntimeError('Viewer must be built before applying responses.')

        previous_trace_type = self._raster_trace_type()
        next_plotly_dict = build_plotly_figure(
            response=response,
            uirevision=self._uirevision,
            heatmap_colorscale=self._heatmap_colorscale,
        )

        # Relayout-driven raster refreshes happen after Plotly has already
        # applied the user's pan/zoom in the browser. When the raster trace type
        # does not change, update trace 0 only with ``Plotly.restyle`` so the
        # client-owned x/y axis ranges are left untouched. Full figure rebuilds
        # remain the path for initial load, reset, ROI/layout changes, and
        # PNG<->heatmap trace-type switches.
        if display_axis_ranges is not None and self._can_restyle_raster_trace(response, previous_trace_type):
            self._current_bounds = response.bounds
            self._replace_local_raster_trace(next_plotly_dict)
            self._sync_hover_info_to_plotly_dict()
            self._last_display_axis_ranges = display_axis_ranges
            self._last_applied_display_axis_ranges = display_axis_ranges
            self._last_applied_x_range = display_axis_ranges[0]
            logger.info('TRACE UPDATE START === calling Plotly.restyle for raster trace 0')
            await self._restyle_raster_trace0_from_plotly_dict()
            logger.info('TRACE UPDATE END === calling Plotly.restyle for raster trace 0')
            return

        self._current_bounds = response.bounds
        self._plotly_dict = next_plotly_dict
        self._sync_roi_shapes_to_plotly_dict()
        self._sync_trace_overlays_to_plotly_dict()
        self._apply_display_options_to_plotly_dict()

        if display_axis_ranges is None:
            if self._transform is not None:
                x_range = self._transform.row_col_to_plot_x_range(response.bounds)
                y_range = self._transform.row_col_to_plot_y_range(response.bounds)
                display_axis_ranges = (x_range, y_range)
        else:
            (x_lo, x_hi), (y_lo, y_hi) = display_axis_ranges
            self._layout_pin_xy_ranges(x_lo=x_lo, x_hi=x_hi, y_lo=y_lo, y_hi=y_hi)

        if display_axis_ranges is not None:
            self._last_display_axis_ranges = display_axis_ranges
            self._last_applied_display_axis_ranges = display_axis_ranges
            self._last_applied_x_range = display_axis_ranges[0]
            logger.info('TRACE UPDATE START === full self._plot.figure replacement for relayout raster refresh')
            self._ignore_next_programmatic_relayout = True
        else:
            logger.info('TRACE UPDATE START === full self._plot.figure replacement')

        self._plot.figure = self._plotly_dict
        self._plot.update()
        if display_axis_ranges is not None:
            logger.info('TRACE UPDATE END === full self._plot.figure replacement for relayout raster refresh')
        else:
            logger.info('TRACE UPDATE END === full self._plot.figure replacement')

    def _raster_trace_type(self) -> str | None:
        """Return the current raster trace type for trace 0, if present."""
        data = self._plotly_dict.get('data', [])
        if not isinstance(data, list) or not data:
            return None
        trace0 = data[0]
        if not isinstance(trace0, dict):
            return None
        trace_type = trace0.get('type')
        return str(trace_type) if trace_type is not None else None

    def _can_restyle_raster_trace(self, response: RenderResponse, previous_trace_type: str | None) -> bool:
        """Return whether a relayout refresh can update trace 0 without layout changes."""
        if self._plot is None:
            return False
        expected_type = 'image' if response.mode == 'image_png' else 'heatmap' if response.mode == 'heatmap_z' else None
        return expected_type is not None and previous_trace_type == expected_type

    def _replace_local_raster_trace(self, next_plotly_dict: dict[str, object]) -> None:
        """Replace only local trace 0 with the newly rendered raster trace."""
        next_data = next_plotly_dict.get('data', [])
        if not isinstance(next_data, list) or not next_data or not isinstance(next_data[0], dict):
            raise RuntimeError('Rendered Plotly figure did not contain a raster trace.')

        data = self._plotly_dict.setdefault('data', [])
        if not isinstance(data, list):
            data = []
            self._plotly_dict['data'] = data
        if data:
            data[0] = dict(next_data[0])
        else:
            data.append(dict(next_data[0]))
        self._set_trace_overlay_visibility(data)

    async def _restyle_raster_trace0_from_plotly_dict(self) -> None:
        """Push only trace-0 raster data/style with ``Plotly.restyle``.

        This is used after a user relayout. Plotly already owns the visible
        viewport at that point, so this method intentionally sends no layout
        keys and does not call ``self._plot.update()``.
        """
        if self._plot is None:
            return
        data = self._plotly_dict.get('data', [])
        if not isinstance(data, list) or not data or not isinstance(data[0], dict):
            return
        trace0 = data[0]
        restyle = {key: [value] for key, value in trace0.items() if key != 'type'}
        logger.info('TRACE UPDATE PAYLOAD === Plotly.restyle keys are:')
        pprint(sorted(restyle.keys()))
        js = f"""
{self._js_plotly_graph_div()}
Plotly.restyle(plotDiv, {json.dumps(restyle)}, [0]);
"""
        try:
            await self._plot.client.run_javascript(js, timeout=10.0)
        except TimeoutError:
            logger.warning('Timed out while restyling Plotly raster trace.')
        except RuntimeError:
            logger.warning('Could not restyle Plotly raster trace; browser client unavailable.')
        except Exception:
            logger.exception('Failed to restyle Plotly raster trace.')

    def set_rois(self, rois: Sequence[RectRoiOverlay]) -> None:
        """Replace all rectangular ROI overlays without pushing raster data.

        Args:
            rois: ROI overlays in Plotly physical coordinates.

        Returns:
            None.
        """
        self._plotly_rois.set_rois(rois)
        self._sync_roi_shapes_to_plotly_dict()
        self._relayout_shapes()

    def select_roi(self, roi_id: int | None) -> None:
        """Select one ROI overlay and update rectangle styling only.

        Args:
            roi_id: ROI identifier to select, or None to clear selection.

        Returns:
            None.
        """
        self._plotly_rois.select_roi(roi_id)
        self._sync_roi_shapes_to_plotly_dict()
        self._relayout_shapes()

    def add_roi(self, roi: RectRoiOverlay) -> None:
        """Add or replace one ROI overlay without pushing raster data.

        Args:
            roi: ROI overlay in Plotly physical coordinates.

        Returns:
            None.
        """
        self._plotly_rois.add_roi(roi)
        self._sync_roi_shapes_to_plotly_dict()
        self._relayout_shapes()

    def delete_roi(self, roi_id: int) -> None:
        """Delete one ROI overlay without pushing raster data.

        Args:
            roi_id: ROI identifier to remove.

        Returns:
            None.
        """
        self._plotly_rois.delete_roi(roi_id)
        self._sync_roi_shapes_to_plotly_dict()
        self._relayout_shapes()

    def set_roi_editing(self, enabled: bool, roi_id: int | None = None) -> None:
        """Enable or disable direct editing for one ROI shape.

        Args:
            enabled: Whether ROI shape editing should be active.
            roi_id: ROI id to make editable when ``enabled`` is True.

        Returns:
            None.
        """
        self._plotly_rois.set_roi_editing(roi_id if enabled else None)
        self._sync_plotly_config_to_plotly_dict()
        self._sync_roi_shapes_to_plotly_dict()
        self._react_plotly_config()
        self._relayout_shapes()

    def set_trace_overlays(self, overlays: Sequence[PlotlyTraceOverlay]) -> None:
        """Replace all trace overlays without pushing raster data.

        Args:
            overlays: Trace overlays in Plotly physical coordinates.

        Returns:
            None.
        """
        self._plotly_trace_overlays.set_overlays(overlays)
        self._sync_trace_overlays_to_plotly_dict()
        self._redraw_trace_overlays()

    def add_trace_overlay(self, overlay: PlotlyTraceOverlay) -> None:
        """Add or replace one trace overlay without pushing raster data.

        Args:
            overlay: Trace overlay in Plotly physical coordinates.

        Returns:
            None.
        """
        self._plotly_trace_overlays.add_overlay(overlay)
        self._sync_trace_overlays_to_plotly_dict()
        self._redraw_trace_overlays()

    def delete_trace_overlay(self, trace_id: str) -> None:
        """Delete one trace overlay without pushing raster data.

        Args:
            trace_id: Trace overlay identifier to remove.

        Returns:
            None.
        """
        self._plotly_trace_overlays.delete_overlay(trace_id)
        self._sync_trace_overlays_to_plotly_dict()
        self._redraw_trace_overlays()

    def clear_trace_overlays(self) -> None:
        """Delete all trace overlays without pushing raster data.

        Returns:
            None.
        """
        self._plotly_trace_overlays.clear_overlays()
        self._sync_trace_overlays_to_plotly_dict()
        self._redraw_trace_overlays()

    def _sync_trace_overlays_to_plotly_dict(self) -> None:
        """Synchronize current trace overlay state into ``data``.

        Returns:
            None.
        """
        data = self._plotly_dict.setdefault('data', [])
        if not isinstance(data, list):
            data = []
        self._plotly_dict['data'] = self._plotly_trace_overlays.merge_traces(data)
        self._set_trace_overlay_visibility(self._plotly_dict['data'])

    def _redraw_trace_overlays(self) -> None:
        """Replace managed browser-side trace overlays without pushing raster data.

        Returns:
            None.
        """
        if self._plot is None:
            return
        overlay_traces = self._plotly_trace_overlays.to_traces()
        self._set_trace_overlay_visibility(overlay_traces)
        js = f"""
{self._js_plotly_graph_div()}
const baseTraceCount = 1;
const deleteCount = Math.max(0, plotDiv.data.length - baseTraceCount);
const deleteIndices = Array.from(
  {{length: deleteCount}},
  (_, i) => baseTraceCount + i,
);
const overlayTraces = {json.dumps(overlay_traces)};
let overlayPromise = Promise.resolve();
if (deleteIndices.length > 0) {{
  overlayPromise = Plotly.deleteTraces(plotDiv, deleteIndices);
}}
return overlayPromise.then(() => {{
  if (overlayTraces.length > 0) {{
    return Plotly.addTraces(plotDiv, overlayTraces);
  }}
  return null;
}});
"""
        try:
            self._plot.client.run_javascript(js, timeout=10.0)
        except TimeoutError:
            logger.warning('Timed out while refreshing Plotly trace overlays.')
        except Exception:
            logger.exception('Failed to refresh Plotly trace overlays.')

    def _sync_roi_shapes_to_plotly_dict(self) -> None:
        """Synchronize current ROI overlay state into ``layout.shapes``.

        Returns:
            None.
        """
        layout = self._plotly_dict.setdefault('layout', {})
        existing_shapes = layout.get('shapes', [])
        if not isinstance(existing_shapes, list):
            existing_shapes = []
        layout['shapes'] = self._plotly_rois.merge_shapes(existing_shapes)
        self._set_roi_shape_visibility(layout['shapes'])
        self._set_roi_label_visibility(layout['shapes'])

    def _relayout_shapes(self) -> None:
        """Push only ``layout.shapes`` to the browser with ``Plotly.relayout``.

        Returns:
            None.
        """
        if self._plot is None:
            return
        layout = self._plotly_dict.setdefault('layout', {})
        shapes = layout.get('shapes', [])
        js = f"""
{self._js_plotly_graph_div()}
Plotly.relayout(plotDiv, {{
  shapes: {json.dumps(shapes)}
}});
"""
        self._plot.client.run_javascript(js, timeout=2.0)

    def set_roi_overlays_visible(self, visible: bool) -> None:
        """Set ROI overlay visibility without changing ROI state.

        Args:
            visible: Whether ROI shapes should be visible.

        Returns:
            None.
        """
        self._display_options.show_rois = bool(visible)
        self._sync_roi_shapes_to_plotly_dict()
        self._relayout_shapes()

    def set_roi_labels_visible(self, visible: bool) -> None:
        """Set ROI overlay label visibility without changing ROI state.

        Args:
            visible: Whether ROI shape labels should be visible.

        Returns:
            None.
        """
        self._display_options.show_roi_labels = bool(visible)
        self._sync_roi_shapes_to_plotly_dict()
        self._relayout_shapes()

    def set_trace_overlays_visible(self, visible: bool) -> None:
        """Set managed trace overlay visibility without changing overlay state.

        Args:
            visible: Whether managed trace overlays should be visible.

        Returns:
            None.
        """
        self._display_options.show_trace_overlays = bool(visible)
        self._sync_trace_overlays_to_plotly_dict()
        self._restyle_trace_overlay_visibility()

    def set_axis_labels_visible(self, visible: bool) -> None:
        """Set x/y axis decoration visibility without rebuilding the plot.

        The public method keeps its original name for API compatibility, but it
        now controls the full axis decoration set: title text, numeric tick
        labels, tick marks, axis line, zero line, and grid lines.

        Args:
            visible: Whether axis decorations should be visible.

        Returns:
            None.
        """
        self._display_options.show_axis_labels = bool(visible)
        self._sync_axis_labels_to_plotly_dict()
        self._relayout_axis_labels()

    def set_square_plot(self, enabled: bool) -> None:
        """Set whether Plotly constrains the raster plot to a square plot area.

        Args:
            enabled: Whether the raster plot should be square inside its
                enclosing Plotly container.

        Returns:
            None.
        """
        self._display_options.square_plot = bool(enabled)
        self._sync_square_plot_to_plotly_dict()
        self._relayout_square_plot()

    def set_theme(self, theme: PlotlyThemeName) -> None:
        """Set the Plotly raster viewer color theme.

        Args:
            theme: Theme name, either ``'light'`` or ``'dark'``.

        Returns:
            None.
        """
        self._display_options.theme = normalize_plotly_theme(theme)
        self._sync_theme_to_plotly_dict()
        self._relayout_theme()

    def set_dark_mode(self, enabled: bool) -> None:
        """Set the Plotly raster viewer theme from a dark-mode flag.

        Args:
            enabled: Whether dark mode is enabled.

        Returns:
            None.
        """
        self.set_theme('dark' if enabled else 'light')

    def set_plotly_toolbar_visible(self, visible: bool) -> None:
        """Set Plotly modebar visibility.

        Args:
            visible: Whether Plotly's modebar should be visible.

        Returns:
            None.
        """
        self._display_options.show_plotly_toolbar = bool(visible)
        self._sync_plotly_config_to_plotly_dict()
        self._react_plotly_config()

    def set_hover_info_visible(self, visible: bool) -> None:
        """Set Plotly hover-info visibility for the raster trace.

        When disabled (``visible=False``, the default), ``hoverinfo='skip'`` is
        applied to the raster trace so Plotly does not display tooltips and
        does not emit hover events.

        Args:
            visible: Whether hover info should be visible.

        Returns:
            None.
        """
        self._display_options.show_hover_info = bool(visible)
        self._sync_hover_info_to_plotly_dict()
        self._restyle_hover_info()

    def _restyle_hover_info(self) -> None:
        """Push ``hoverinfo`` change to the browser via ``Plotly.restyle``."""
        if self._plot is None:
            return
        value = 'all' if self._display_options.show_hover_info else 'skip'
        js = f"""
{self._js_plotly_graph_div()}
Plotly.restyle(plotDiv, {{
  hoverinfo: [{json.dumps(value)}]
}}, [0]);
"""
        self._plot.client.run_javascript(js, timeout=2.0)

    async def copy_plot_to_clipboard(self) -> None:
        """Copy the current Plotly plot image to the native clipboard when available.

        Browser/cloud mode currently reports a warning because robust image
        clipboard support is browser-permission dependent. Native mode uses the
        optional ``pyperclipimg`` stack.
        """
        if self._plot is None:
            ui.notify('No plot to copy.', type='warning')
            return

        try:
            if is_pywebview_desktop():
                png_bytes = await get_plotly_png_bytes(self._plot)
                copy_png_bytes_to_native_clipboard(png_bytes)
            else:
                await copy_plotly_png_to_browser_clipboard(self._plot)
            ui.notify('Plot copied to clipboard.', type='positive')
        except Exception as exc:
            logger.exception('Failed to copy Plotly plot to clipboard.')
            ui.notify(f'Copy failed: {exc}', type='negative')

    def _on_context_menu_event(self, _event) -> None:
        """Rebuild and open the Plotly raster viewer context menu."""
        if self._ctx_menu is None or self._context_menu_builder is None:
            return
        with self._ctx_menu.clear():
            self._context_menu_builder.build()
        self._ctx_menu.open()

    def _apply_display_options_to_plotly_dict(self) -> None:
        """Synchronize all display options into the local Plotly dictionary."""
        self._sync_plotly_config_to_plotly_dict()
        self._sync_theme_to_plotly_dict()
        self._sync_axis_labels_to_plotly_dict()
        self._sync_square_plot_to_plotly_dict()
        self._sync_hover_info_to_plotly_dict()
        layout = self._plotly_dict.setdefault('layout', {})
        shapes = layout.get('shapes', [])
        if isinstance(shapes, list):
            self._set_roi_shape_visibility(shapes)
            self._set_roi_label_visibility(shapes)
        data = self._plotly_dict.get('data', [])
        if isinstance(data, list):
            self._set_trace_overlay_visibility(data)

    def _sync_hover_info_to_plotly_dict(self) -> None:
        """Synchronize hover-info visibility into the raster trace dict.

        Uses ``hoverinfo='skip'`` when disabled (suppresses Plotly's hover
        events entirely) so the browser does not emit hover traffic when the
        user toggles this off.
        """
        data = self._plotly_dict.get('data', [])
        if not isinstance(data, list) or not data:
            return
        trace0 = data[0]
        if not isinstance(trace0, dict):
            return
        trace0['hoverinfo'] = 'all' if self._display_options.show_hover_info else 'skip'

    def _sync_plotly_config_to_plotly_dict(self) -> None:
        """Synchronize Plotly config options into the local figure dict."""
        config = dict(RASTER_VIEWER_PLOTLY_CONFIG)
        config['displayModeBar'] = bool(self._display_options.show_plotly_toolbar)
        config['edits'] = {
            'shapePosition': self._plotly_rois.editing_roi_id is not None,
            'titleText': False,
            'axisTitleText': False,
            'legendText': False,
            'legendPosition': False,
        }
        self._plotly_dict['config'] = config

    def _sync_axis_labels_to_plotly_dict(self) -> None:
        """Synchronize axis decoration visibility into the local figure dict."""
        layout = self._plotly_dict.setdefault('layout', {})
        visible = bool(self._display_options.show_axis_labels)
        for axis_name in ('xaxis', 'yaxis'):
            axis = layout.setdefault(axis_name, {})
            if not isinstance(axis, dict):
                axis = {}
                layout[axis_name] = axis
            title = axis.setdefault('title', {})
            if not isinstance(title, dict):
                title = {}
                axis['title'] = title
            title['text'] = self._axis_title_texts.get(axis_name, '') if visible else ''
            axis['showticklabels'] = visible
            axis['ticks'] = 'outside' if visible else ''
            axis['showline'] = visible
            axis['zeroline'] = False
            axis['showgrid'] = visible

    def _sync_theme_to_plotly_dict(self) -> None:
        """Synchronize the selected light/dark theme into the local figure dict."""
        layout = self._plotly_dict.setdefault('layout', {})
        if not isinstance(layout, dict):
            layout = {}
            self._plotly_dict['layout'] = layout
        apply_plotly_theme_to_layout(layout, self._display_options.theme)

    def _sync_square_plot_to_plotly_dict(self) -> None:
        """Synchronize square-plot layout constraints into the local figure dict."""
        layout = self._plotly_dict.setdefault('layout', {})
        xaxis = layout.setdefault('xaxis', {})
        yaxis = layout.setdefault('yaxis', {})
        if not isinstance(xaxis, dict):
            xaxis = {}
            layout['xaxis'] = xaxis
        if not isinstance(yaxis, dict):
            yaxis = {}
            layout['yaxis'] = yaxis

        if self._display_options.square_plot:
            xaxis['constrain'] = 'domain'
            yaxis['constrain'] = 'domain'
            yaxis['scaleanchor'] = 'x'
            yaxis['scaleratio'] = self._square_plot_scaleratio
            return

        xaxis.pop('constrain', None)
        yaxis.pop('constrain', None)
        yaxis['scaleanchor'] = False
        yaxis.pop('scaleratio', None)

    def _set_roi_shape_visibility(self, shapes: list[object]) -> None:
        """Apply global ROI visibility to managed ROI shapes.

        Args:
            shapes: Mutable Plotly layout shape list.

        Returns:
            None.
        """
        for shape in shapes:
            if PlotlyRoiOverlayLayer.is_roi_shape(shape):
                shape['visible'] = bool(self._display_options.show_rois)

    def _set_roi_label_visibility(self, shapes: list[object]) -> None:
        """Blank managed ROI shape labels when label display is disabled.

        The ROI overlay layer always emits the full label text. When
        ``show_roi_labels`` is disabled, the label text is cleared so Plotly
        renders the rectangle without its annotation. When enabled, the freshly
        merged shapes already carry their label text, so this is a no-op.

        Args:
            shapes: Mutable Plotly layout shape list.

        Returns:
            None.
        """
        if self._display_options.show_roi_labels:
            return
        for shape in shapes:
            if not PlotlyRoiOverlayLayer.is_roi_shape(shape) or not isinstance(shape, dict):
                continue
            label = shape.get('label')
            if isinstance(label, dict):
                label['text'] = ''

    def _set_trace_overlay_visibility(self, traces: list[object]) -> None:
        """Apply global trace-overlay visibility to managed overlay traces.

        Args:
            traces: Mutable Plotly data list.

        Returns:
            None.
        """
        for trace in traces:
            if PlotlyTraceOverlayLayer.is_trace_overlay(trace):
                trace['visible'] = bool(
                    trace.get('visible', True) and self._display_options.show_trace_overlays
                )

    def _relayout_axis_labels(self) -> None:
        """Push x/y axis decoration visibility to the browser."""
        if self._plot is None:
            return
        layout = self._plotly_dict.setdefault('layout', {})
        relayout: dict[str, object] = {}
        for axis_name in ('xaxis', 'yaxis'):
            axis = layout.get(axis_name, {})
            if not isinstance(axis, dict):
                continue
            title = axis.get('title', {})
            title_text = title.get('text', '') if isinstance(title, dict) else ''
            relayout[f'{axis_name}.title.text'] = title_text
            relayout[f'{axis_name}.showticklabels'] = axis.get('showticklabels', True)
            relayout[f'{axis_name}.ticks'] = axis.get('ticks', '')
            relayout[f'{axis_name}.showline'] = axis.get('showline', False)
            relayout[f'{axis_name}.zeroline'] = axis.get('zeroline', False)
            relayout[f'{axis_name}.showgrid'] = axis.get('showgrid', True)
        js = f"""
{self._js_plotly_graph_div()}
Plotly.relayout(plotDiv, {json.dumps(relayout)});
"""
        self._plot.client.run_javascript(js, timeout=2.0)

    def _relayout_theme(self) -> None:
        """Push light/dark theme layout properties to the browser."""
        if self._plot is None:
            return
        layout = self._plotly_dict.setdefault('layout', {})
        relayout: dict[str, object] = {
            'paper_bgcolor': layout.get('paper_bgcolor', 'white'),
            'plot_bgcolor': layout.get('plot_bgcolor', 'white'),
        }
        font = layout.get('font', {})
        if isinstance(font, dict):
            relayout['font.color'] = font.get('color', '#111827')
        for axis_name in ('xaxis', 'yaxis'):
            axis = layout.get(axis_name, {})
            if not isinstance(axis, dict):
                continue
            relayout[f'{axis_name}.color'] = axis.get('color')
            relayout[f'{axis_name}.linecolor'] = axis.get('linecolor')
            relayout[f'{axis_name}.tickcolor'] = axis.get('tickcolor')
            relayout[f'{axis_name}.gridcolor'] = axis.get('gridcolor')
            relayout[f'{axis_name}.zerolinecolor'] = axis.get('zerolinecolor')
        js = f"""
{self._js_plotly_graph_div()}
Plotly.relayout(plotDiv, {json.dumps(relayout)});
"""
        self._plot.client.run_javascript(js, timeout=2.0)

    def _relayout_square_plot(self) -> None:
        """Push square-plot layout constraints to the browser."""
        if self._plot is None:
            return
        relayout: dict[str, object] = {}
        if self._display_options.square_plot:
            relayout = {
                'xaxis.constrain': 'domain',
                'yaxis.constrain': 'domain',
                'yaxis.scaleanchor': 'x',
                'yaxis.scaleratio': self._square_plot_scaleratio,
            }
        else:
            relayout = {
                'xaxis.constrain': None,
                'yaxis.constrain': None,
                'yaxis.scaleanchor': False,
                'yaxis.scaleratio': None,
            }
        js = f"""
{self._js_plotly_graph_div()}
Plotly.relayout(plotDiv, {json.dumps(relayout)});
"""
        self._plot.client.run_javascript(js, timeout=2.0)

    def _restyle_trace_overlay_visibility(self) -> None:
        """Push only managed trace-overlay ``visible`` values to the browser."""
        if self._plot is None:
            return
        data = self._plotly_dict.get('data', [])
        visibility_by_trace_id: dict[str, bool] = {}
        if isinstance(data, list):
            for trace in data:
                trace_id = PlotlyTraceOverlayLayer.trace_id_from_trace(trace)
                if trace_id is not None and isinstance(trace, dict):
                    visibility_by_trace_id[str(trace_id)] = bool(trace.get('visible', True))

        js = f"""
{self._js_plotly_graph_div()}
const visibilityByTraceId = {json.dumps(visibility_by_trace_id)};
const indices = [];
const visibleValues = [];
plotDiv.data.forEach((trace, index) => {{
  const traceId = trace?.meta?.trace_id;
  if (trace?.meta?.nicewidgets_overlay_type === 'trace' && traceId in visibilityByTraceId) {{
    indices.push(index);
    visibleValues.push(visibilityByTraceId[traceId]);
  }}
}});
if (indices.length > 0) {{
  Plotly.restyle(plotDiv, {{visible: visibleValues}}, indices);
}}
"""
        self._plot.client.run_javascript(js, timeout=2.0)

    def _react_plotly_config(self) -> None:
        """Push Plotly config changes without creating a new NiceGUI plot."""
        if self._plot is None:
            return
        config = self._plotly_dict.get('config', {})
        js = f"""
{self._js_plotly_graph_div()}
Plotly.react(plotDiv, plotDiv.data, plotDiv.layout, {json.dumps(config)});
"""
        self._plot.client.run_javascript(js, timeout=2.0)

    def request_from_plotly(self, payload: PlotlyViewportPayload):
        """Build a backend request from a browser relayout payload (merged axes)."""
        if self._service is None:
            raise RuntimeError('No data set. Call set_data() before requesting renders.')
        if self._transform is None:
            raise RuntimeError('Coordinate transform missing; call set_data() first.')
        merged = merge_partial_relayout(
            payload.relayout,
            self._transform,
            self._current_bounds,
        )
        merged_payload = PlotlyViewportPayload(
            relayout=merged,
            width_px=payload.width_px,
            height_px=payload.height_px,
        )
        return parse_relayout_payload(merged_payload, self._transform, self._current_bounds)

    async def rerender_from_plotly(
        self,
        payload: PlotlyViewportPayload,
        *,
        display_axis_ranges: tuple[tuple[float, float], tuple[float, float]] | None = None,
    ) -> RenderResponse:
        """Render and apply an updated view from a relayout payload.

        Args:
            payload: Browser viewport payload used to request raster data.
            display_axis_ranges: Optional Plotly viewport to preserve while
                applying the new raster data. Relayout-driven renders pass this
                so a PNG/heatmap or pyramid-level swap does not reset the
                user-visible zoom that Plotly already applied.
        """
        if self._service is None:
            raise RuntimeError('No data set. Call set_data() before requesting renders.')
        request = self.request_from_plotly(payload)
        response = self._service.render(request, display_style=self._display_style())
        await self.apply_response(response, display_axis_ranges=display_axis_ranges)
        return response

    async def set_axis_ranges(
        self,
        *,
        x_min: float,
        x_max: float,
        y_min: float,
        y_max: float,
    ) -> None:
        """Set visible axis ranges in **plot physical** coordinates (Plotly space)."""
        if self._plot is None or self._transform is None:
            raise RuntimeError('Viewer must be built and data set before setting axis ranges.')

        self._current_bounds = self._transform.plot_xy_ranges_to_row_col(
            x_min,
            x_max,
            y_min,
            y_max,
        )

        x_lo = float(min(x_min, x_max))
        x_hi = float(max(x_min, x_max))
        y_lo = float(min(y_min, y_max))
        y_hi = float(max(y_min, y_max))
        self._layout_pin_xy_ranges(x_lo=x_lo, x_hi=x_hi, y_lo=y_lo, y_hi=y_hi)
        display_axis_ranges = ((x_lo, x_hi), (y_lo, y_hi))
        self._last_display_axis_ranges = display_axis_ranges
        self._last_applied_display_axis_ranges = display_axis_ranges

        js = f"""
{self._js_plotly_graph_div()}
Plotly.relayout(plotDiv, {{
  'xaxis.range': [{json.dumps(x_lo)}, {json.dumps(x_hi)}],
  'xaxis.autorange': false,
  'yaxis.range': [{json.dumps(y_lo)}, {json.dumps(y_hi)}],
  'yaxis.autorange': false
}});
"""
        self._plot.client.run_javascript(js, timeout=2.0)

    async def set_x_axis_range(self, *, x_min: float, x_max: float) -> None:
        """Set visible **x** (plot row / physical-x) axis range; y extent unchanged.

        Args:
            x_min: Minimum plot x value.
            x_max: Maximum plot x value.

        Records the applied value so a follow-up Plotly relayout echo (which
        Plotly emits whenever ranges change, including programmatic changes)
        does not re-fire ``on_x_range_changed``.
        """
        if self._plot is None or self._transform is None:
            raise RuntimeError('Viewer must be built and data set before setting axis ranges.')

        fy_lo, fy_hi = self._transform.row_col_to_plot_y_range(self._current_bounds)
        x_lo = float(min(x_min, x_max))
        x_hi = float(max(x_min, x_max))
        self._current_bounds = self._transform.plot_xy_ranges_to_row_col(
            x_lo,
            x_hi,
            fy_lo,
            fy_hi,
        )

        self._layout_pin_xy_ranges(x_lo=x_lo, x_hi=x_hi, y_lo=fy_lo, y_hi=fy_hi)
        display_axis_ranges = ((x_lo, x_hi), (fy_lo, fy_hi))
        self._last_applied_x_range = (x_lo, x_hi)
        self._last_display_axis_ranges = display_axis_ranges
        self._last_applied_display_axis_ranges = display_axis_ranges

        js = f"""
{self._js_plotly_graph_div()}
Plotly.relayout(plotDiv, {{
  'xaxis.range': [{json.dumps(x_lo)}, {json.dumps(x_hi)}],
  'xaxis.autorange': false,
  'yaxis.range': [{json.dumps(fy_lo)}, {json.dumps(fy_hi)}],
  'yaxis.autorange': false
}});
"""
        self._plot.client.run_javascript(js, timeout=2.0)

    def reset_x_axis_range(self) -> None:
        """Record that the next user x-range should be treated as auto.

        Callers use this when the consumer-side state event arrives with
        ``(None, None)``. The actual reset of Plotly's view happens on the next
        full render (or via the existing double-click handler); recording
        ``None`` here is enough to clear echo suppression.
        """
        self._last_applied_x_range = (None, None)

    async def set_heatmap_contrast(self, *, zmin: float, zmax: float) -> None:
        """Pin intensity window for heatmap (``Plotly.restyle``) and PNG overview (re-encode)."""
        z_lo, z_hi = (float(min(zmin, zmax)), float(max(zmin, zmax)))
        self._contrast_zmin = z_lo
        self._contrast_zmax = z_hi

        if self._heatmap_trace_active():
            data = self._plotly_dict.get('data', [])
            skip_restyle = False
            if isinstance(data, list) and data and isinstance(data[0], dict):
                trace0 = data[0]
                if trace0.get('zmin') == z_lo and trace0.get('zmax') == z_hi:
                    skip_restyle = True
                else:
                    trace0['zmin'] = z_lo
                    trace0['zmax'] = z_hi
            if not skip_restyle:
                js = f"""
{self._js_plotly_graph_div()}
Plotly.restyle(plotDiv, {{
  zmin: [{json.dumps(z_lo)}],
  zmax: [{json.dumps(z_hi)}]
}}, [0]);
"""
                self._plot.client.run_javascript(js, timeout=2.0)
        elif self._image_trace_active():
            await self._refresh_full_png()
        else:
            raise RuntimeError('No raster trace to style. Load data and show a heatmap or overview image first.')

    async def set_heatmap_colorscale(self, colorscale: PlotlyColorscale) -> None:
        """Set Plotly colorscale for heatmap and PNG overview LUT encoding.

        Accepts either a built-in name (``'Greys'``, ``'Viridis'``, ...) or a
        list of ``[stop, color]`` pairs for custom 2-stop scales such as the
        contrast widget's ``inverted_grays``.

        Args:
            colorscale: Plotly colorscale name or stop list.
        """
        self._heatmap_colorscale = colorscale

        if self._heatmap_trace_active():
            data = self._plotly_dict.get('data', [])
            skip_restyle = False
            if isinstance(data, list) and data and isinstance(data[0], dict):
                trace0 = data[0]
                if trace0.get('colorscale') == self._heatmap_colorscale:
                    skip_restyle = True
                else:
                    trace0['colorscale'] = self._heatmap_colorscale
            if not skip_restyle:
                js = f"""
{self._js_plotly_graph_div()}
Plotly.restyle(plotDiv, {{
  colorscale: [{json.dumps(self._heatmap_colorscale)}]
}}, [0]);
"""
                self._plot.client.run_javascript(js, timeout=2.0)
        elif self._image_trace_active():
            await self._refresh_full_png()
        else:
            raise RuntimeError('No raster trace to style. Load data and show a heatmap or overview image first.')

    async def set_heatmap_style(
        self,
        *,
        colorscale: PlotlyColorscale,
        zmin: float,
        zmax: float,
    ) -> None:
        """Apply colorscale and intensity window in a single browser round trip.

        Equivalent to calling :meth:`set_heatmap_colorscale` and
        :meth:`set_heatmap_contrast` back-to-back, but issues exactly one
        ``Plotly.restyle`` (when a heatmap trace is active) or one PNG overview
        re-encode (when an image trace is active). Use this when both the LUT
        and the intensity window change together (e.g. ``ImageContrast``
        applied for the current channel).

        Args:
            colorscale: Plotly colorscale name or stop list.
            zmin: Minimum intensity for the colorscale mapping.
            zmax: Maximum intensity for the colorscale mapping.
        """
        z_lo, z_hi = (float(min(zmin, zmax)), float(max(zmin, zmax)))
        self._heatmap_colorscale = colorscale
        self._contrast_zmin = z_lo
        self._contrast_zmax = z_hi

        if self._heatmap_trace_active():
            data = self._plotly_dict.get('data', [])
            skip_restyle = False
            if isinstance(data, list) and data and isinstance(data[0], dict):
                trace0 = data[0]
                if (
                    trace0.get('colorscale') == self._heatmap_colorscale
                    and trace0.get('zmin') == z_lo
                    and trace0.get('zmax') == z_hi
                ):
                    skip_restyle = True
                else:
                    trace0['colorscale'] = self._heatmap_colorscale
                    trace0['zmin'] = z_lo
                    trace0['zmax'] = z_hi
            if not skip_restyle:
                js = f"""
{self._js_plotly_graph_div()}
Plotly.restyle(plotDiv, {{
  colorscale: [{json.dumps(self._heatmap_colorscale)}],
  zmin: [{json.dumps(z_lo)}],
  zmax: [{json.dumps(z_hi)}]
}}, [0]);
"""
                self._plot.client.run_javascript(js, timeout=2.0)
        elif self._image_trace_active():
            await self._refresh_full_png()
        else:
            raise RuntimeError(
                'No raster trace to style. Load data and show a heatmap or overview image first.'
            )

    async def _on_plotly_doubleclick(self, event) -> None:
        """Reset to full overview PNG (same path as initial load) and emit auto x-range."""
        if self._service is None or self._plot is None:
            return

        logger.info('')

        self._cancel_pending_relayout_render()
        self._uirevision = self._new_uirevision()
        response = self._service.full_image_png(
            display_style=self._display_style(),
            max_pixels=self._overview_max_pixels,
        )
        await self.apply_response(response)
        # Pin echo dedup to the freshly reset data extent so the follow-up
        # relayout Plotly fires after ``_uirevision`` rotation does not leak
        # into ``on_x_range_changed`` and overwrite the ``(None, None)`` state
        # we emit below.
        if self._transform is not None:
            x_lo_data, x_hi_data = self._transform.row_col_to_plot_x_range(self._current_bounds)
            y_lo_data, y_hi_data = self._transform.row_col_to_plot_y_range(self._current_bounds)
            display_axis_ranges = ((x_lo_data, x_hi_data), (y_lo_data, y_hi_data))
            self._last_applied_x_range = (x_lo_data, x_hi_data)
            self._last_display_axis_ranges = display_axis_ranges
            self._last_applied_display_axis_ranges = display_axis_ranges
        if self._on_x_range_changed is not None:
            self._on_x_range_changed(None, None)

    async def _on_plotly_autosize(self, event) -> None:
        """Handle NiceGUI Plotly autosize events (diagnostic no-op)."""
        raw_args = getattr(event, 'args', {}) or {}
        args = dict(raw_args) if isinstance(raw_args, dict) else {'raw_args': raw_args}
        logger.info('=== === === AUTOSIZE ENTER args is:')
        pprint(args)
        return

    async def _on_plotly_restyle(self, event) -> None:
        """Log Plotly restyle events forwarded by NiceGUI for raster diagnostics."""
        raw_args = getattr(event, 'args', {}) or {}
        args = dict(raw_args) if isinstance(raw_args, dict) else {'raw_args': raw_args}
        logger.info('=== === === RESTYLE ENTER args is:')
        pprint(_summarize_plotly_event_args(args))
        return

    async def _on_plotly_relayout(self, event) -> None:
        """Handle Plotly relayout events from pan, wheel zoom, axis zoom, and ROI edits.

        Plotly has already updated the browser-side view when this callback
        runs. The raster viewer uses the callback to decide which Python-side
        state must follow the browser event. ROI shape edits stay immediate.
        Axis-range changes emit their x-range callback immediately, but the
        expensive backend raster render is debounced so rapid mouse-wheel
        events do not queue many full ``ui.plotly`` figure replacements.
        """
        if self._service is None or self._plot is None or self._transform is None:
            return

        raw_args = getattr(event, 'args', {}) or {}
        args = dict(raw_args) if isinstance(raw_args, dict) else {'raw_args': raw_args}

        logger.info('=== === === RELAYOUT ENTER args is:')
        pprint(args)

        # Plotly shape-drag relayout payloads are also delivered here. These
        # are ROI editing events, not viewport updates, and must remain
        # immediate so the edited ROI state and preview callback stay current.
        if self._handle_roi_shape_relayout(args):
            return

        # return


        if self._ignore_next_programmatic_relayout:
            if self._looks_like_programmatic_relayout_echo(args):
                self._ignore_next_programmatic_relayout = False
                logger.info('=== === === RELAYOUT IGNORED === programmatic raster update echo args is:')
                pprint(args)
                return
            self._ignore_next_programmatic_relayout = False
            logger.info('=== === === RELAYOUT LATCH CLEARED === next event looked user-driven args is:')
            pprint(args)

        # Ignore relayout payloads that do not carry axis ranges. Context-menu
        # display changes, shape redraws, autosize, and double-click reset
        # payloads should not ask the backend raster service for a new viewport
        # image unless a dedicated reset path handles them.
        if not any(k.startswith('xaxis.range') or k.startswith('yaxis.range') for k in args):
            return

        if self._is_tracked_normalized_relayout_followup(args):
            logger.info('=== === === RELAYOUT IGNORED === normalized follow-up while bracket-key render is pending or active args is:')
            pprint(args)
            logger.info('=== === === RELAYOUT PENDING KEPT relayout is:')
            pprint(self._pending_relayout_render)
            logger.info('=== === === RELAYOUT ACTIVE KEPT relayout is:')
            pprint(self._active_relayout_render)
            return

        # Plotly has already zoomed/panned the browser-side view by the time
        # this callback runs. Snapshot that user-chosen viewport now. Missing
        # axes are filled from the last known displayed viewport, not from
        # backend render bounds, because pyramid renders may be padded or
        # quantized and are not the visual source of truth.
        display_axis_ranges = self._display_axis_ranges_from_relayout(args)
        if display_axis_ranges is None:
            return

        logger.info(f'=== === === RELAYOUT ACCEPTED display_axis_ranges:{display_axis_ranges}')
        relayout = self._relayout_from_display_axis_ranges(display_axis_ranges)

        # Keep this synchronous and immediate: external CloudScope state uses
        # x-range callbacks to track the visible row/time range. Only the
        # expensive raster rerender below is debounced.
        self._emit_x_range_from_relayout(relayout)

        # Plotly has already zoomed/panned the current browser plot. This
        # scheduled refresh only swaps in raster data/pyramid level appropriate
        # for the final viewport and then reapplies this same display viewport.
        self._schedule_debounced_relayout_render(relayout)

    def _schedule_debounced_relayout_render(self, relayout: dict[str, object]) -> None:
        """Schedule one coalesced backend raster refresh for axis relayouts.

        Args:
            relayout: Merged Plotly relayout payload for the latest viewport.

        Returns:
            None.
        """
        logger.info('=== === === RELAYOUT SCHEDULED relayout is:')
        pprint(relayout)
        self._pending_relayout_render = dict(relayout)
        task = self._relayout_render_task
        if task is not None and not task.done():
            return
        self._relayout_render_task = asyncio.create_task(self._debounced_relayout_render_loop())

    async def _debounced_relayout_render_loop(self) -> None:
        """Coalesce rapid axis relayouts and render only the newest viewport.

        Mouse-wheel zoom can emit many Plotly relayout events while the browser
        view is already changing smoothly. Rendering every intermediate
        viewport through Python causes repeated full Plotly figure updates and
        visible flicker. This loop waits briefly for a burst to settle, renders
        the newest pending relayout, and repeats only if another relayout
        arrived while the previous render was in flight.
        """
        try:
            while True:
                await asyncio.sleep(_RELAYOUT_RENDER_DEBOUNCE_SECONDS)

                relayout = self._pending_relayout_render
                self._pending_relayout_render = None
                if relayout is None:
                    return

                self._active_relayout_render = dict(relayout)
                logger.info('=== === === DEBOUNCED RENDER START relayout is:')
                pprint(relayout)
                try:
                    viewport = await self._build_viewport_payload(relayout=relayout)
                    if viewport is not None:
                        display_axis_ranges = self._display_axis_ranges_from_relayout(relayout)
                        logger.info(f'=== === === DEBOUNCED RENDER display_axis_ranges:{display_axis_ranges}')
                        await self.rerender_from_plotly(
                            viewport,
                            display_axis_ranges=display_axis_ranges,
                        )
                        logger.info('=== === === DEBOUNCED RENDER END')
                finally:
                    if self._active_relayout_render == relayout:
                        self._active_relayout_render = None

                if self._pending_relayout_render is None:
                    return
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception('Failed during debounced Plotly relayout render.')
        finally:
            if asyncio.current_task() is self._relayout_render_task:
                self._relayout_render_task = None

    def _cancel_pending_relayout_render(self) -> None:
        """Cancel any scheduled relayout render before replacing/resetting data.

        Returns:
            None.
        """
        self._pending_relayout_render = None
        self._active_relayout_render = None
        task = self._relayout_render_task
        if task is not None and not task.done():
            task.cancel()
        self._relayout_render_task = None

    def _looks_like_programmatic_relayout_echo(self, args: dict[str, object]) -> bool:
        """Return whether a relayout payload looks like our Plotly update echo.

        User wheel/drag events observed in CloudScope usually arrive with
        bracket keys such as ``xaxis.range[0]`` and ``yaxis.range[1]``.
        Programmatic full figure updates may arrive later as normalized
        full-range keys plus ``*.autorange: False``. Use that structural
        shape to consume the one-shot programmatic-update latch without
        comparing floating point ranges.
        """
        return self._is_normalized_autorange_false_relayout(args)

    def _is_normalized_autorange_false_relayout(self, args: dict[str, object]) -> bool:
        """Return whether Plotly reported normalized full-range relayout keys.

        A single mouse-wheel in CloudScope has been observed to emit two
        relayout events before any raster restyle happens:

        1. bracket keys from the actual wheel viewport, for example
           ``xaxis.range[0]`` and ``yaxis.range[1]``;
        2. normalized keys, for example ``xaxis.range`` plus
           ``xaxis.autorange: False``.

        The normalized follow-up may carry a stale or full-height y range. It
        must not overwrite the pending bracket-key viewport captured from the
        user gesture.
        """
        has_normalized_range = 'xaxis.range' in args or 'yaxis.range' in args
        has_autorange_false = args.get('xaxis.autorange') is False or args.get('yaxis.autorange') is False
        has_bracket_range = any('[0]' in key or '[1]' in key for key in args)
        return has_normalized_range and has_autorange_false and not has_bracket_range

    def _is_tracked_normalized_relayout_followup(self, args: dict[str, object]) -> bool:
        """Return whether ``args`` is a normalized follow-up to a tracked viewport.

        A single wheel gesture can emit a bracket-key relayout followed by a
        normalized ``xaxis.range``/``yaxis.range`` payload with
        ``*.autorange: False``. The normalized payload often carries stale or
        full-height y limits. Ignore it if it corresponds to either the
        viewport still pending debounce or the viewport currently being
        rendered. This prevents one user wheel from becoming two raster
        refreshes.
        """
        if not self._is_normalized_autorange_false_relayout(args):
            return False

        incoming_x = self._axis_range_from_relayout(args, axis='xaxis')
        incoming_y = self._axis_range_from_relayout(args, axis='yaxis')
        tracked_relayouts = [
            relayout
            for relayout in (self._pending_relayout_render, self._active_relayout_render)
            if relayout is not None
        ]

        for relayout in tracked_relayouts:
            tracked_x = self._axis_range_from_relayout(relayout, axis='xaxis')
            tracked_y = self._axis_range_from_relayout(relayout, axis='yaxis')
            x_matches = tracked_x is not None and incoming_x is not None and _range_pair_equal(tracked_x, incoming_x)
            y_matches = tracked_y is not None and incoming_y is not None and _range_pair_equal(tracked_y, incoming_y)
            if x_matches or y_matches:
                return True
        return False

    def _handle_roi_shape_relayout(self, args: dict[str, object]) -> bool:
        """Handle Plotly shape drag relayout while ROI editing is active.

        Args:
            args: Raw Plotly relayout payload.

        Returns:
            True when the payload was an ROI edit payload and should not be
            processed as an axis range update.
        """
        editing_roi_id = self._plotly_rois.editing_roi_id
        if editing_roi_id is None:
            return False
        if not any(key.startswith('shapes[') for key in args):
            return False

        layout = self._plotly_dict.setdefault('layout', {})
        shapes = layout.get('shapes', [])
        if not isinstance(shapes, list):
            return True

        pending: dict[int, dict[str, float]] = {}
        snapback = False
        for key, value in args.items():
            parsed = self._parse_shape_coord_relayout_key(key)
            if parsed is None:
                continue
            shape_index, coord = parsed
            if not (0 <= shape_index < len(shapes)):
                snapback = True
                break
            shape = shapes[shape_index]
            if not isinstance(shape, dict):
                snapback = True
                break
            roi_id = PlotlyRoiOverlayLayer.roi_id_from_shape(shape)
            if roi_id != editing_roi_id:
                snapback = True
                break
            try:
                fval = float(value)
            except (TypeError, ValueError):
                continue
            pending.setdefault(roi_id, {})[coord] = fval

        if snapback:
            self._sync_roi_shapes_to_plotly_dict()
            self._relayout_shapes()
            return True

        edited = False
        for roi_id, coords in pending.items():
            roi = self._plotly_roi_by_id(roi_id)
            if roi is None:
                continue
            x0 = coords.get('x0', roi.x0)
            x1 = coords.get('x1', roi.x1)
            y0 = coords.get('y0', roi.y0)
            y1 = coords.get('y1', roi.y1)
            updated = self._plotly_rois.update_roi_bounds(
                roi_id,
                x0=x0,
                x1=x1,
                y0=y0,
                y1=y1,
            )
            if updated is None:
                continue
            edited = True
            if self._on_roi_bounds_preview is not None:
                self._on_roi_bounds_preview(roi_id, updated.x0, updated.x1, updated.y0, updated.y1)

        if edited:
            self._sync_roi_shapes_to_plotly_dict()
            self._relayout_shapes()
        return True

    @staticmethod
    def _parse_shape_coord_relayout_key(key: str) -> tuple[int, str] | None:
        """Parse ``shapes[N].x0`` style relayout keys.

        Args:
            key: Plotly relayout key.

        Returns:
            Tuple of shape index and coordinate name, or None for non-ROI
            shape coordinate keys.
        """
        if not key.startswith('shapes['):
            return None
        try:
            prefix, coord = key.split('].', 1)
            index = int(prefix[len('shapes['):])
        except (ValueError, IndexError):
            return None
        if coord not in {'x0', 'x1', 'y0', 'y1'}:
            return None
        return index, coord

    def _plotly_roi_by_id(self, roi_id: int) -> RectRoiOverlay | None:
        """Return a managed ROI overlay by id.

        Args:
            roi_id: ROI identifier.

        Returns:
            Matching ROI overlay, or None.
        """
        for roi in self._plotly_rois.rois:
            if roi.roi_id == roi_id:
                return roi
        return None

    def _axis_range_from_relayout(
        self,
        relayout: dict[str, object],
        *,
        axis: str,
    ) -> tuple[float, float] | None:
        """Return one Plotly axis range from list or bracket relayout keys.

        Args:
            relayout: Raw or canonical Plotly relayout payload.
            axis: Axis key prefix, for example ``'xaxis'`` or ``'yaxis'``.

        Returns:
            ``(lo, hi)`` when the relayout payload contains both values,
            otherwise ``None``.
        """
        raw = relayout.get(f'{axis}.range')
        if isinstance(raw, (list, tuple)) and len(raw) == 2:
            try:
                return float(raw[0]), float(raw[1])
            except (TypeError, ValueError):
                return None

        lo = relayout.get(f'{axis}.range[0]')
        hi = relayout.get(f'{axis}.range[1]')
        if lo is None or hi is None:
            return None
        try:
            return float(lo), float(hi)
        except (TypeError, ValueError):
            return None

    def _display_axis_ranges_from_relayout(
        self,
        relayout: dict[str, object],
    ) -> tuple[tuple[float, float], tuple[float, float]] | None:
        """Snapshot the Plotly display viewport represented by a relayout.

        Plotly often reports only the axis that changed during an axis-drag
        gesture. For display preservation, fill any missing axis from the last
        displayed viewport. Only fall back to current backend bounds when no
        display cache exists yet.
        """
        if self._transform is None:
            return None

        x_range = self._axis_range_from_relayout(relayout, axis='xaxis')
        y_range = self._axis_range_from_relayout(relayout, axis='yaxis')
        if x_range is None and y_range is None:
            return None

        cached = self._last_display_axis_ranges
        if x_range is None:
            if cached is not None:
                x_range = cached[0]
            else:
                x_range = self._transform.row_col_to_plot_x_range(self._current_bounds)
        if y_range is None:
            if cached is not None:
                y_range = cached[1]
            else:
                y_range = self._transform.row_col_to_plot_y_range(self._current_bounds)

        return x_range, y_range

    def _relayout_from_display_axis_ranges(
        self,
        display_axis_ranges: tuple[tuple[float, float], tuple[float, float]],
    ) -> dict[str, object]:
        """Return canonical bracket-key relayout payload for preserved ranges."""
        (x_lo, x_hi), (y_lo, y_hi) = display_axis_ranges
        return {
            'xaxis.range[0]': x_lo,
            'xaxis.range[1]': x_hi,
            'yaxis.range[0]': y_lo,
            'yaxis.range[1]': y_hi,
        }

    def _is_display_axis_range_echo(
        self,
        display_axis_ranges: tuple[tuple[float, float], tuple[float, float]],
    ) -> bool:
        """Return whether display ranges echo the last full figure apply."""
        last = self._last_applied_display_axis_ranges
        if last is None:
            return False
        return _range_pair_equal(last[0], display_axis_ranges[0]) and _range_pair_equal(
            last[1],
            display_axis_ranges[1],
        )

    def _emit_x_range_from_relayout(self, merged: dict[str, object]) -> None:
        """Invoke ``on_x_range_changed`` from a merged relayout payload.

        Echo relayouts (whether driven by ``set_x_axis_range`` or by the
        follow-up Plotly emits when ``_uirevision`` rotates in ``set_data`` /
        ``_on_plotly_doubleclick``) are deduped by value against
        ``_last_applied_x_range``. Both call sites update that field before
        any browser-side relayout can race the python-side emit.

        Args:
            merged: Plotly relayout payload after partial-key merging.

        Returns:
            None.
        """
        if self._on_x_range_changed is None:
            return
        x_lo = merged.get('xaxis.range[0]')
        x_hi = merged.get('xaxis.range[1]')
        try:
            new_x_min = float(x_lo) if x_lo is not None else None
            new_x_max = float(x_hi) if x_hi is not None else None
        except (TypeError, ValueError):
            return
        if new_x_min is None or new_x_max is None:
            return
        new_range = (new_x_min, new_x_max)
        if self._is_x_range_echo(new_range):
            return
        self._last_applied_x_range = new_range
        self._on_x_range_changed(new_x_min, new_x_max)

    def _is_x_range_echo(
        self, new_range: tuple[float | None, float | None]
    ) -> bool:
        """Return whether ``new_range`` echoes the last programmatic apply.

        Args:
            new_range: Candidate ``(x_min, x_max)`` from a relayout event.

        Returns:
            ``True`` when both values match the last applied pair within
            tolerance.
        """
        last = self._last_applied_x_range
        if last is None:
            return False
        return _x_range_equal(last, new_range)

    async def _build_viewport_payload(
        self,
        *,
        relayout: dict[str, object],
    ) -> PlotlyViewportPayload | None:
        """Build relayout payload with current browser viewport size.

        The relayout callback can schedule this method from a debounced
        background task. In that task NiceGUI does not provide the implicit
        client/slot context required by ``ui.run_javascript``. Always execute
        JavaScript through the explicit Plotly element client and fall back to
        the last successful plot-size measurement when a fresh measurement is
        temporarily unavailable.
        """
        if self._plot is None:
            return None

        js = f"""
const host = getElement({self._plot.id}).$el;
if (!host) return null;
const plotDiv = host.querySelector('.js-plotly-plot') || host;
const rect = plotDiv.getBoundingClientRect();
return {{
  width_px: Math.max(1, Math.round(rect.width)),
  height_px: Math.max(1, Math.round(rect.height)),
}};
"""
        result: object | None = None
        try:
            result = await self._plot.client.run_javascript(js, timeout=2.0)
        except (TimeoutError, RuntimeError):
            # A timeout or disconnected/invalid client should not crash a
            # debounced relayout task. Use the cached size below if possible.
            result = None

        if isinstance(result, dict):
            width_px = int(result.get('width_px', 0) or 0)
            height_px = int(result.get('height_px', 0) or 0)
            if width_px > 0 and height_px > 0:
                self._last_viewport_size_px = (width_px, height_px)
                return PlotlyViewportPayload(
                    relayout=relayout,
                    width_px=width_px,
                    height_px=height_px,
                )

        if self._last_viewport_size_px is None:
            return None
        width_px, height_px = self._last_viewport_size_px
        return PlotlyViewportPayload(
            relayout=relayout,
            width_px=width_px,
            height_px=height_px,
        )

    def _build_initial_figure(self) -> dict:
        """Return the figure shown before or after data is set."""
        if self._service is None or self._transform is None:
            self._plotly_dict = {
                'data': [],
                'layout': {
                    # 'margin': {'l': 40, 'r': 20, 't': 20, 'b': 40},
                    'margin': {'l': 40, 'r': 10, 't': 10, 'b': 40},
                    'uirevision': self._uirevision,
                    'autosize': True,
                    'xaxis': {'range': [0.0, 1.0]},
                    'yaxis': {'range': [0.0, 1.0]},
                    'dragmode': 'zoom',
                },
                'config': dict(RASTER_VIEWER_PLOTLY_CONFIG),
            }
            self._apply_display_options_to_plotly_dict()
            return self._plotly_dict

        logger.info('making initial default png -->> never called?')

        response = self._service.full_image_png(
            display_style=self._display_style(),
            max_pixels=self._overview_max_pixels,
        )
        self._current_bounds = response.bounds
        figure = build_plotly_figure(
            response=response,
            uirevision=self._uirevision,
            heatmap_colorscale=self._heatmap_colorscale,
        )
        layout = figure.setdefault('layout', {})
        shapes = layout.get('shapes', [])
        if not isinstance(shapes, list):
            shapes = []
        layout['shapes'] = self._plotly_rois.merge_shapes(shapes)
        data = figure.get('data', [])
        if not isinstance(data, list):
            data = []
        figure['data'] = self._plotly_trace_overlays.merge_traces(data)
        self._plotly_dict = figure
        self._apply_display_options_to_plotly_dict()
        return self._plotly_dict

    def _display_style(self) -> RasterDisplayStyle:
        """Return backend PNG / heatmap styling derived from viewer state."""
        return RasterDisplayStyle(
            colorscale=self._heatmap_colorscale,
            zmin=self._contrast_zmin,
            zmax=self._contrast_zmax,
        )

    async def _refresh_full_png(self) -> None:
        """Re-run full-image PNG render with :meth:`_display_style` and push to the plot."""
        if self._service is None or self._plot is None:
            raise RuntimeError('Viewer must be built with data before refreshing the overview.')
        response = self._service.full_image_png(
            display_style=self._display_style(),
            max_pixels=self._overview_max_pixels,
        )
        await self.apply_response(response)

    def _heatmap_trace_active(self) -> bool:
        """Return ``True`` when the figure's first trace is a heatmap."""
        if self._plot is None:
            return False
        data = self._plotly_dict.get('data', [])
        if not isinstance(data, list) or not data:
            return False
        trace = data[0]
        return isinstance(trace, dict) and trace.get('type') == 'heatmap'

    def _image_trace_active(self) -> bool:
        """Return ``True`` when the figure's first trace is a raster ``image``."""
        if self._plot is None:
            return False
        data = self._plotly_dict.get('data', [])
        if not isinstance(data, list) or not data:
            return False
        trace = data[0]
        return isinstance(trace, dict) and trace.get('type') == 'image'

    @staticmethod
    def _new_uirevision() -> str:
        """Return a new Plotly UI revision token."""
        return uuid4().hex

    @staticmethod
    def _square_plot_scaleratio_for_source(source: BackendImage) -> float:
        """Return the Plotly y/x scale ratio that makes the full source square.

        Args:
            source: Current backend image.

        Returns:
            Plotly ``yaxis.scaleratio`` value for square display.
        """
        y_extent = float(source.width) * float(source.grid.dy)
        if y_extent <= 0:
            return 1.0
        x_extent = float(source.height) * float(source.grid.dx)
        return x_extent / y_extent
