"""Thin NiceGUI Plotly adapter for raster viewing."""

from __future__ import annotations

import json
from collections.abc import Sequence
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


class PlotlyRasterViewer:
    """Small frontend adapter around :class:`RasterViewService`.

    Converts Plotly/NiceGUI events to the backend service API. Row/column
    bounds live in the backend; plot coordinates use :class:`PlotlyCoordTransform`.
    """

    def __init__(self) -> None:
        self._plot: Element | None = None
        self._service: RasterViewService | None = None
        self._plotly_dict: dict[str, object] = {}
        self._current_bounds = RowColBounds(
            row_min=0.0,
            row_max=1.0,
            col_min=0.0,
            col_max=1.0,
        )
        self._transform: PlotlyCoordTransform | None = None
        self._uirevision = self._new_uirevision()
        self._heatmap_colorscale: str = DEFAULT_HEATMAP_COLORSCALE
        self._contrast_zmin: float | None = None
        self._contrast_zmax: float | None = None
        self._plotly_rois = PlotlyRoiOverlayLayer()
        self._plotly_trace_overlays = PlotlyTraceOverlayLayer()

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

    def build(self) -> Element:
        """Create the NiceGUI Plotly element."""
        self._plotly_dict = self._build_initial_figure()

        self._plot = ui.plotly(self._plotly_dict)
        self._plot.on('plotly_relayout', self._on_plotly_relayout)
        self._plot.on('plotly_autosize', self._on_plotly_autosize)
        self._plot.on('plotly_doubleclick', self._on_plotly_doubleclick)

        return self._plot

    async def set_data(self, data: np.ndarray, *, grid: RasterGridSpec) -> RenderResponse:
        """Set a new 2D dataset and fully refresh the plot.

        Args:
            data: New full-resolution 2D array ``(rows, columns)``.
            grid: Physical spacing and axis labels (``dx``/``dy`` must be positive).

        Returns:
            Initial full-image PNG response for the new dataset.
        """
        source = BackendImage(data, grid=grid)
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
        self._current_bounds = self._transform.full_row_col_bounds()
        self._uirevision = self._new_uirevision()
        self._heatmap_colorscale = DEFAULT_HEATMAP_COLORSCALE
        self._contrast_zmin = None
        self._contrast_zmax = None
        self._plotly_trace_overlays.clear_overlays()

        response = self._service.full_image_png(display_style=self._display_style())
        self._current_bounds = response.bounds
        self._plotly_dict = build_plotly_figure(
            response=response,
            uirevision=self._uirevision,
            heatmap_colorscale=self._heatmap_colorscale,
        )
        self._sync_roi_shapes_to_plotly_dict()
        self._sync_trace_overlays_to_plotly_dict()

        if self._plot is not None:
            self._plot.figure = self._plotly_dict
            self._plot.update()
        return response

    async def apply_response(self, response: RenderResponse) -> None:
        """Apply a backend response to the browser-side Plotly plot."""
        if self._plot is None:
            raise RuntimeError('Viewer must be built before applying responses.')

        self._current_bounds = response.bounds
        self._plotly_dict = build_plotly_figure(
            response=response,
            uirevision=self._uirevision,
            heatmap_colorscale=self._heatmap_colorscale,
        )
        self._sync_roi_shapes_to_plotly_dict()
        self._sync_trace_overlays_to_plotly_dict()

        self._plot.figure = self._plotly_dict
        self._plot.update()

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

    def _redraw_trace_overlays(self) -> None:
        """Replace managed browser-side trace overlays without pushing raster data.

        Returns:
            None.
        """
        if self._plot is None:
            return
        overlay_traces = self._plotly_trace_overlays.to_traces()
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

    async def rerender_from_plotly(self, payload: PlotlyViewportPayload) -> RenderResponse:
        """Render and apply an updated view from a relayout payload."""
        if self._service is None:
            raise RuntimeError('No data set. Call set_data() before requesting renders.')
        request = self.request_from_plotly(payload)
        response = self._service.render(request, display_style=self._display_style())
        await self.apply_response(response)
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
        """Set visible **x** (plot row / physical-x) axis range; y extent unchanged."""
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

    async def set_heatmap_colorscale(self, colorscale: str) -> None:
        """Set Plotly colorscale name for heatmap and for PNG overview LUT encoding."""
        self._heatmap_colorscale = str(colorscale)

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

    async def _on_plotly_doubleclick(self, event) -> None:
        """Reset to full overview PNG (same path as initial load)."""
        if self._service is None or self._plot is None:
            return

        logger.info('')

        self._uirevision = self._new_uirevision()
        response = self._service.full_image_png(display_style=self._display_style())
        await self.apply_response(response)

    async def _on_plotly_autosize(self, event) -> None:
        """Handle NiceGUI Plotly autosize events (no-op for now)."""
        return

    async def _on_plotly_relayout(self, event) -> None:
        """Handle Plotly relayout: pan, wheel, or axis zoom (partial keys merged)."""
        if self._service is None or self._plot is None or self._transform is None:
            return

        args = dict(getattr(event, 'args', {}) or {})

        logger.info('args is:')
        # pprint(args, indent=4, sort_dicts=False)
        # # number of shapes:
        # num_shapes = len(args.get('shapes', []))
        # logger.info(f'num_shapes: {num_shapes}')
        # pprint args, skipping 'shapes' key
        

        if not any(k.startswith('xaxis.range') or k.startswith('yaxis.range') for k in args):
            return

        merged = merge_partial_relayout(args, self._transform, self._current_bounds)
        viewport = await self._build_viewport_payload(relayout=merged)
        if viewport is None:
            return

        await self.rerender_from_plotly(viewport)

    async def _build_viewport_payload(
        self,
        *,
        relayout: dict[str, object],
    ) -> PlotlyViewportPayload | None:
        """Build relayout payload with current browser viewport size."""
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
        try:
            result = await ui.run_javascript(js, timeout=2.0)
        except TimeoutError:
            return None

        if not isinstance(result, dict):
            return None

        width_px = int(result.get('width_px', 0) or 0)
        height_px = int(result.get('height_px', 0) or 0)
        if width_px <= 0 or height_px <= 0:
            return None

        return PlotlyViewportPayload(
            relayout=relayout,
            width_px=width_px,
            height_px=height_px,
        )

    def _build_initial_figure(self) -> dict:
        """Return the figure shown before or after data is set."""
        if self._service is None or self._transform is None:
            return {
                'data': [],
                'layout': {
                    'margin': {'l': 40, 'r': 20, 't': 20, 'b': 40},
                    'uirevision': self._uirevision,
                    'autosize': True,
                    'xaxis': {'range': [0.0, 1.0]},
                    'yaxis': {'range': [0.0, 1.0]},
                    'dragmode': 'zoom',
                },
                'config': dict(RASTER_VIEWER_PLOTLY_CONFIG),
            }

        logger.info('making initial default png -->> never called?')

        response = self._service.full_image_png(display_style=self._display_style())
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
        return figure

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
        response = self._service.full_image_png(display_style=self._display_style())
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
