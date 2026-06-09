"""Primary raster image view: AcqStore slice + header calibration into ``PlotlyRasterViewer``.

``z`` / ``t`` are **not** raster-viewer concepts. They belong to
:meth:`BaseFileLoader.get_slice_data`, which defaults to ``z=0`` and ``t=0``
when omitted; CloudScope relies on those defaults for v1.

Pixel arrays are passed through from AcqStore without forced dtype conversion;
the raster pipeline casts where needed (e.g. PNG encoding uses ``float32``
internally).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import numpy as np
from nicegui import run, ui

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisOverlayTraceData
from acqstore.acq_image.roi import RectROI, RectRoiBounds
from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind
from cloudscope.events.contrast import ImageContrastChanged
from cloudscope.events.raster import PrimaryPlaneLoaded
from cloudscope.events.roi import RoiChanged, RoiEditModeChanged, RoiEditPreviewChanged
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.contrast_widget.colorscales import get_colorscale
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec
from nicewidgets.raster_viewer.frontend.plotly_display_options import (
    PlotlyRasterViewerDisplayOptions,
)
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer
from nicewidgets.raster_viewer.frontend.roi_overlay import RectRoiOverlay
from nicewidgets.raster_viewer.frontend.trace_overlay import PlotlyTraceOverlay

logger = get_logger(__name__)

_PLACEHOLDER_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='Pixels', y_unit='Pixels')


def raster_grid_spec_from_image_header(header: ImageHeader) -> RasterGridSpec:
    """Build :class:`RasterGridSpec` for a ``(Y, X)`` slice from calibration.

    The raster viewer uses numpy row index as plot **x** (here: **Y**) and
    column index as plot **y** (here: **X**). ``dx`` is the physical step per
    row (``Y``), ``dy`` per column (``X``).

    Args:
        header: Loader header with ``dims`` and ``physical_units`` aligned to
            ``dims``.

    Returns:
        Grid specification with strictly positive ``dx`` / ``dy``.

    Raises:
        ValueError: If ``Y`` or ``X`` is missing from ``dims``, or calibration
            is not a finite strictly positive step for either axis.
    """
    if 'Y' not in header.dims or 'X' not in header.dims:
        raise ValueError(
            f'ImageHeader must include Y and X in dims for raster mapping, got dims={header.dims!r}'
        )
    dx = header._physical_step_for_dim('Y')
    dy = header._physical_step_for_dim('X')
    if dx is None or dy is None:
        raise ValueError(
            f'Invalid or missing physical calibration for Y/X in {header.path!r} '
            f'(physical_units={header.physical_units!r}, dims={header.dims!r})'
        )
    x_unit = header._physical_label_for_dim('Y')
    y_unit = header._physical_label_for_dim('X')
    return RasterGridSpec(dx=float(dx), dy=float(dy), x_unit=x_unit, y_unit=y_unit)


def _placeholder_plane() -> tuple[np.ndarray, RasterGridSpec]:
    """Return a tiny neutral plane when no file/channel is selected.

    Returns:
        Placeholder image and grid specification.
    """
    return np.zeros((2, 2), dtype=np.float32), _PLACEHOLDER_GRID


def _load_plane_payload(
    file_id: str | None,
    acq_image: AcqImage | None,
    channel: int | None,
) -> tuple[np.ndarray, RasterGridSpec, bool]:
    """Load ``(array, grid, is_placeholder)`` for a selection.

    This function is safe to run off the UI thread with ``run.io_bound``.

    Args:
        file_id: Selected file id, if any.
        acq_image: Resolved acquisition object, if any.
        channel: Selected channel index, if any.

    Returns:
        Tuple of two-dimensional array ``(Y, X)``, its :class:`RasterGridSpec`,
        and a flag indicating whether the result is the neutral placeholder
        (no contrast publish should occur for placeholders).

    Raises:
        ValueError: If header calibration cannot be mapped.
        IndexError: If ``channel`` is out of range for the loader.
    """
    if file_id is None or acq_image is None or channel is None:
        plane, grid = _placeholder_plane()
        return plane, grid, True
    grid = raster_grid_spec_from_image_header(acq_image.images.header)
    plane = np.asarray(acq_image.images.get_slice_data(channel))
    if plane.ndim != 2:
        raise ValueError(f'Expected 2D slice (Y, X), got shape={plane.shape}')
    return plane, grid, False


def _schedule_coro(coro: Coroutine[Any, Any, None]) -> None:
    """Run ``coro`` on the running loop, or ``asyncio.run`` when no loop exists.

    Args:
        coro: Coroutine to schedule.

    Returns:
        None.
    """
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


class PrimaryImageView(BaseView):
    """NiceGUI primary image panel driven by BaseView selection tracking.

    The view does not maintain a second persistent copy of file/channel/ROI
    selection. It snapshots the current BaseView selection only when scheduling
    an asynchronous image load, so the worker sees a stable set of values while
    BaseView remains the source of truth.

    Args:
        event_bus: Page-scoped event bus.
        title: Card title.
        initially_visible: Whether this view starts visible.
        dark_mode: Initial Plotly raster-viewer theme state.
        dark_mode_provider: Optional callable returning the current application
            dark-mode state when the view is shown after being hidden.
    """

    view_id = ViewId.PRIMARY_IMAGE
    disable_when_busy = False

    def __init__(
        self,
        event_bus: EventBus,
        *,
        title: str = 'Primary image',
        initially_visible: bool = True,
        dark_mode: bool = False,
        dark_mode_provider: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self._title = title
        self._client: Any = None
        self._viewer = PlotlyRasterViewer(
            display_options=PlotlyRasterViewerDisplayOptions(
                theme='dark' if dark_mode else 'light',
            ),
            on_x_range_changed=self._on_viewer_x_range_changed,
            on_roi_bounds_preview=self._on_viewer_roi_bounds_preview,
        )
        self._current_grid: RasterGridSpec | None = None
        self._dark_mode_provider = dark_mode_provider
        # Latest app-level ``primary_x_range`` cache, updated from
        # ``PrimaryXRangeChanged``. Re-applied to the viewer after every
        # raster reload so user/state range survives ``set_data`` rotations.
        self._primary_x_range: tuple[float | None, float | None] = (None, None)

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Create the card, title, and Plotly raster element.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        self._client = ui.context.client

        def _build() -> None:
            with ui.column().classes("w-full h-full min-h-0 flex flex-col overflow-hidden flex-1") as self.root:
                
                # dislpay name of widget, comment it out
                # ui.label(self._title).classes("text-lg font-medium shrink-0")
                
                plot = self._viewer.build()
                plot.classes('w-full h-full min-h-0 flex-1')

        if parent is None:
            _build()
        else:
            with parent:
                _build()

        self.after_build()
        self._refresh_raster_from_current_selection()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to primary-image-specific events while visible.

        BaseView already subscribes to primary selection and busy-state events.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(RoiChanged, self._on_roi_changed))
        self.add_subscription(self.event_bus.subscribe(RoiEditModeChanged, self._on_roi_edit_mode_changed))
        self.add_subscription(
            self.event_bus.subscribe(RoiEditPreviewChanged, self._on_roi_edit_preview_changed)
        )
        self.add_subscription(self.event_bus.subscribe(AnalysisCompleted, self._on_analysis_completed))
        self.add_subscription(self.event_bus.subscribe(ThemeChanged, self._on_theme_changed))
        self.add_subscription(
            self.event_bus.subscribe(ImageContrastChanged, self._on_image_contrast_changed)
        )
        self.add_subscription(
            self.event_bus.subscribe(PrimaryXRangeChanged, self._on_primary_x_range_changed)
        )

    def _on_viewer_x_range_changed(
        self, x_min: float | None, x_max: float | None
    ) -> None:
        """Producer hook: turn a viewer pan/zoom into an app-level intent.

        Args:
            x_min: Minimum x value reported by Plotly, or ``None`` for auto.
            x_max: Maximum x value reported by Plotly, or ``None`` for auto.

        Returns:
            None.
        """
        self.event_bus.publish(SetPrimaryXRangeIntent(x_min=x_min, x_max=x_max))

    def _on_viewer_roi_bounds_preview(
        self,
        roi_id: int,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
    ) -> None:
        """Producer hook: turn a viewer ROI drag into a preview state event.

        Args:
            roi_id: ROI id whose Plotly shape changed.
            x0: First x coordinate in Plotly coordinate space.
            x1: Second x coordinate in Plotly coordinate space.
            y0: First y coordinate in Plotly coordinate space.
            y1: Second y coordinate in Plotly coordinate space.

        Returns:
            None.
        """
        selection = self.current_selection
        if selection.file_id is None or selection.roi_id != roi_id:
            return
        acq_image = self.get_selected_acq_image()
        grid = self._current_grid
        if acq_image is None or grid is None:
            return
        bounds = _rect_roi_bounds_from_plot_coords(
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            grid=grid,
        ).clamped_to(acq_image.rois.image_bounds)
        self.event_bus.publish(
            RoiEditPreviewChanged(selection=selection, bounds=bounds)
        )

    def _on_primary_x_range_changed(self, event: PrimaryXRangeChanged) -> None:
        """Consumer: cache the authoritative x-range and apply it to the viewer.

        Args:
            event: State event from :class:`XRangeController`.

        Returns:
            None.
        """
        self._primary_x_range = (event.x_min, event.x_max)
        self._apply_primary_x_range_to_viewer()

    def _apply_primary_x_range_to_viewer(self) -> None:
        """Push the cached ``primary_x_range`` to the Plotly viewer.

        Behavior matches the agreed contract:

        * ``(None, None)`` -> no-op. ``set_data`` already auto-ranges the
          Plotly view on the new ``uirevision``; we only override when the
          state asks for a non-auto window.
        * ``(x_min, x_max)`` -> schedule ``set_x_axis_range``.

        Skipped silently when the viewer has no data yet.

        Returns:
            None.
        """
        if not self._viewer.has_data:
            return
        x_min, x_max = self._primary_x_range
        if x_min is None or x_max is None:
            return
        asyncio.create_task(
            self._viewer.set_x_axis_range(x_min=x_min, x_max=x_max)
        )

    def _on_theme_changed(self, event: ThemeChanged) -> None:
        """Apply an application theme change to the Plotly raster viewer.

        Args:
            event: Theme state event published by the page header.

        Returns:
            None.
        """
        self._viewer.set_dark_mode(event.dark_mode)

    def _sync_theme_from_provider(self) -> None:
        """Apply the current application theme when a provider is available.

        Hidden views do not consume event traffic, so this keeps the Plotly
        viewer synchronized when the view is shown after a theme change.

        Returns:
            None.
        """
        if self._dark_mode_provider is None:
            return
        self._viewer.set_dark_mode(bool(self._dark_mode_provider()))

    def on_primary_selection_changed(self) -> None:
        """Refresh raster after BaseView updates the primary selection.

        Returns:
            None.
        """
        self._refresh_raster_from_current_selection()

    def refresh_from_state(self) -> None:
        """Refresh raster from cached BaseView selection.

        Returns:
            None.
        """
        self._sync_theme_from_provider()
        self._refresh_raster_from_current_selection()

    def _run_ui(self, fn: Callable[[], None]) -> None:
        """Run UI updates; remarshal via ``Client.safe_invoke`` when needed.

        Args:
            fn: UI update function.

        Returns:
            None.
        """
        try:
            fn()
        except RuntimeError as exc:
            message = str(exc).lower()
            if 'slot' not in message and 'client' not in message:
                raise
            if self._client is None:
                logger.warning('Primary image UI update dropped (no client): %s', exc)
                return
            self._client.safe_invoke(fn)

    def _refresh_raster_from_current_selection(self) -> None:
        """Schedule async reload of the raster from the current selection.

        Returns:
            None.
        """
        file_id = self.current_selection.file_id
        acq_image = self.get_selected_acq_image()
        channel = self.current_selection.channel
        _schedule_coro(self._refresh_raster_async(file_id, acq_image, channel))

    async def _refresh_raster_async(
        self,
        file_id: str | None,
        acq_image: AcqImage | None,
        channel: int | None,
    ) -> None:
        """Load and display one raster snapshot asynchronously.

        Args:
            file_id: Snapshot file id.
            acq_image: Snapshot acquisition image.
            channel: Snapshot channel.

        Returns:
            None.
        """
        try:
            plane, grid, is_placeholder = await run.io_bound(
                _load_plane_payload, file_id, acq_image, channel
            )
        except Exception as exc:
            logger.exception('Primary plane load failed file_id=%r channel=%r', file_id, channel)
            err_msg = str(exc)
            self._run_ui(lambda: ui.notify(err_msg, type='negative'))
            try:
                plane, grid = _placeholder_plane()
                await self._viewer.set_data(plane, grid=grid)
            except RuntimeError as inner:
                logger.warning('Placeholder set_data failed: %s', inner)
            return

        try:
            logger.info('calling self._viewer.set_data:')
            logger.info('  plane:%s min:%s max:%s', plane.shape, plane.min(), plane.max())
            logger.info('  grid:%s', grid)
            self._current_grid = grid
            await self._viewer.set_data(plane, grid=grid)
            self._refresh_roi_overlays(acq_image=acq_image, grid=grid)
            self._refresh_diameter_trace_overlays(acq_image=acq_image, grid=grid)
            if not is_placeholder and file_id is not None and channel is not None and acq_image is not None:
                await self._apply_contrast(acq_image, int(channel))
                try:
                    plane.setflags(write=False)
                except (AttributeError, ValueError):
                    # Non-ndarray or already read-only; safe to proceed.
                    pass
                self.event_bus.publish(
                    PrimaryPlaneLoaded(file_id=file_id, channel=int(channel), plane=plane)
                )
            # Re-apply any non-auto app-level x-range that survives ``set_data``
            # (e.g. analysis-row click within the same file). When the cached
            # range is ``(None, None)`` this is a no-op and ``set_data``'s own
            # auto-range stands.
            self._apply_primary_x_range_to_viewer()
        except RuntimeError as exc:
            logger.exception('set_data failed: %s', exc)
            err_msg = str(exc)
            self._run_ui(lambda: ui.notify(err_msg, type='negative'))

    def _on_image_contrast_changed(self, event: ImageContrastChanged) -> None:
        """Re-apply heatmap LUT/contrast for the current selection.

        Args:
            event: Contrast state event.

        Returns:
            None.
        """
        selection = self.current_selection
        if selection.file_id != event.file_id or selection.channel != int(event.channel):
            return
        acq_image = self.get_selected_acq_image()
        if acq_image is None:
            return
        _schedule_coro(self._apply_contrast(acq_image, int(event.channel)))

    async def _apply_contrast(self, acq_image: AcqImage, channel: int) -> None:
        """Apply the AcqImage's stored contrast for ``channel`` to the viewer.

        Looks up :class:`ImageContrast` on ``acq_image`` and pushes the LUT and
        intensity window into the underlying :class:`PlotlyRasterViewer`. No-op
        when no contrast entry exists (the next ``PrimaryPlaneLoaded`` seeder
        will populate it).

        Args:
            acq_image: Current acquisition image.
            channel: Zero-based channel index.

        Returns:
            None.
        """
        contrast = acq_image.get_image_contrast(int(channel))
        if contrast is None:
            return
        scale = get_colorscale(contrast.color_lut)
        try:
            await self._viewer.set_heatmap_style(
                colorscale=scale,
                zmin=float(contrast.value_min),
                zmax=float(contrast.value_max),
            )
        except RuntimeError as exc:
            logger.warning('Skipping contrast apply (viewer not ready): %s', exc)

    def _on_roi_changed(self, event: RoiChanged) -> None:
        """Refresh ROI overlays after the selected file ROI model changes.

        Args:
            event: ROI changed state event.

        Returns:
            None.
        """
        current_file_id = self.current_selection.file_id
        event_file_id = event.selection.file_id
        if current_file_id is not None and event_file_id == current_file_id:
            self._refresh_roi_overlays_from_current_selection()
            self._refresh_diameter_trace_overlays_from_current_selection()

    def _on_roi_edit_mode_changed(self, event: RoiEditModeChanged) -> None:
        """Enable or disable direct ROI editing in the raster viewer.

        Args:
            event: ROI edit-mode state event.

        Returns:
            None.
        """
        if event.is_editing:
            if event.selection is None or event.selection.file_id != self.current_selection.file_id:
                return
            roi_id = event.selection.roi_id
            if roi_id is None:
                return
            self._viewer.select_roi(roi_id)
            self._viewer.set_roi_editing(True, roi_id)
            return

        self._viewer.set_roi_editing(False, None)
        self._refresh_roi_overlays_from_current_selection()

    def _on_roi_edit_preview_changed(self, event: RoiEditPreviewChanged) -> None:
        """Apply staged ROI edit bounds to the visible overlay only.

        Args:
            event: ROI edit preview state event.

        Returns:
            None.
        """
        selection = self.current_selection
        if event.selection.file_id != selection.file_id or event.selection.roi_id != selection.roi_id:
            return
        acq_image = self.get_selected_acq_image()
        grid = self._current_grid
        if acq_image is None or grid is None:
            return
        self._refresh_roi_overlays(
            acq_image=acq_image,
            grid=grid,
            preview_bounds=event.bounds,
            preview_roi_id=event.selection.roi_id,
        )

    def _on_analysis_completed(self, event: AnalysisCompleted) -> None:
        """Refresh diameter trace overlays when analysis completes.

        Args:
            event: Analysis completion event.

        Returns:
            None.
        """
        if event.analysis_kind is not AnalysisKind.DIAMETER:
            return
        if event.selection.file_id != self.current_selection.file_id:
            return
        if event.selection.channel != self.current_selection.channel:
            return
        if event.selection.roi_id != self.current_selection.roi_id:
            return
        self._refresh_diameter_trace_overlays_from_current_selection()

    def _refresh_roi_overlays_from_current_selection(self) -> None:
        """Schedule ROI overlay refresh from the current selection.

        Returns:
            None.
        """
        acq_image = self.get_selected_acq_image()
        grid = self._current_grid
        self._refresh_roi_overlays(acq_image=acq_image, grid=grid)

    def _refresh_roi_overlays(
        self,
        *,
        acq_image: AcqImage | None,
        grid: RasterGridSpec | None,
        preview_bounds: RectRoiBounds | None = None,
        preview_roi_id: int | None = None,
    ) -> None:
        """Push current rectangular ROI overlays into the Plotly viewer.

        Args:
            acq_image: Current acquisition image, or None.
            grid: Current raster viewer grid, or None.
            preview_bounds: Optional staged bounds for one ROI.
            preview_roi_id: ROI id receiving staged bounds.

        Returns:
            None.
        """
        logger.info('')
        
        if acq_image is None or grid is None:
            self._viewer.set_rois([])
            return
        overlays = _rect_roi_overlays_from_acq_image(acq_image, grid=grid)
        if preview_bounds is not None and preview_roi_id is not None:
            overlays = [
                _rect_roi_overlay_from_bounds(preview_roi_id, preview_bounds, grid=grid)
                if overlay.roi_id == preview_roi_id
                else overlay
                for overlay in overlays
            ]
        self._viewer.set_rois(overlays)
        self._viewer.select_roi(self.current_selection.roi_id)

    def _refresh_diameter_trace_overlays_from_current_selection(self) -> None:
        """Refresh diameter edge trace overlays from the current selection.

        Returns:
            None.
        """
        acq_image = self.get_selected_acq_image()
        grid = self._current_grid
        self._refresh_diameter_trace_overlays(acq_image=acq_image, grid=grid)

    def _refresh_diameter_trace_overlays(
        self,
        *,
        acq_image: AcqImage | None,
        grid: RasterGridSpec | None,
    ) -> None:
        """Push diameter edge trace overlays into the Plotly viewer.

        Args:
            acq_image: Current acquisition image, or None.
            grid: Current raster viewer grid, or None.

        Returns:
            None.
        """

        # logger.info('xxx may be slow down causing reset xxx')

        if acq_image is None or grid is None:
            self._viewer.clear_trace_overlays()
            return

        selection = self.current_selection
        if selection.channel is None or selection.roi_id is None:
            self._viewer.clear_trace_overlays()
            return

        key = AnalysisKey(
            analysis_name=AnalysisKind.DIAMETER.value,
            channel=int(selection.channel),
            roi_id=int(selection.roi_id),
        )
        analysis = acq_image.analysis_set.get(key)
        if analysis is None:
            self._viewer.clear_trace_overlays()
            return

        roi = acq_image.rois.get(int(selection.roi_id))
        if not isinstance(roi, RectROI):
            self._viewer.clear_trace_overlays()
            return

        traces = analysis.get_overlay_traces()
        overlays = roi_local_traces_to_plotly_overlays(traces, roi=roi, grid=grid)
        self._viewer.set_trace_overlays(overlays)

        # logger.info('')

def roi_local_traces_to_plotly_overlays(
    traces: tuple[AnalysisOverlayTraceData, ...],
    *,
    roi: RectROI,
    grid: RasterGridSpec,
) -> list[PlotlyTraceOverlay]:
    """Translate ROI-local analysis traces to full-image Plotly coordinates.

    Args:
        traces: ROI-local overlay traces from ``BaseAnalysis.get_overlay_traces``.
        roi: Rectangular ROI that was analyzed.
        grid: Raster grid with physical spacing for dim0 (time) and dim1 (space).

    Returns:
        Plotly trace overlays in full-image physical coordinates.
    """
    x_offset = float(roi.bounds.dim0_start) * grid.dx
    y_offset = float(roi.bounds.dim1_start) * grid.dy
    overlays: list[PlotlyTraceOverlay] = []
    for trace in traces:
        if not trace.visible or not trace.x:
            continue
        overlays.append(
            PlotlyTraceOverlay(
                trace_id=trace.trace_id,
                x=tuple(x_offset + float(value) for value in trace.x),
                y=tuple(y_offset + float(value) for value in trace.y),
                color=trace.color,
                name=trace.name,
                visible=trace.visible,
            )
        )
    return overlays


def _rect_roi_overlay_from_rect_roi(roi: RectROI, *, grid: RasterGridSpec) -> RectRoiOverlay:
    """Convert an AcqStore ``RectROI`` to a Plotly physical-coordinate overlay.

    AcqStore ROI bounds use ``dim0`` for image rows and ``dim1`` for image
    columns. The raster viewer maps rows to Plotly x and columns to Plotly y.

    Args:
        roi: Rectangular ROI model.
        grid: Raster viewer grid with physical spacing.

    Returns:
        Rectangular ROI overlay in Plotly coordinate space.
    """
    bounds = roi.bounds
    return RectRoiOverlay(
        roi_id=roi.roi_id,
        x0=float(bounds.dim0_start) * grid.dx,
        x1=float(bounds.dim0_stop) * grid.dx,
        y0=float(bounds.dim1_start) * grid.dy,
        y1=float(bounds.dim1_stop) * grid.dy,
        label=str(roi.roi_id),
    )


def _rect_roi_overlay_from_bounds(
    roi_id: int,
    bounds: RectRoiBounds,
    *,
    grid: RasterGridSpec,
) -> RectRoiOverlay:
    """Convert rectangular bounds to a Plotly physical-coordinate overlay.

    Args:
        roi_id: ROI identifier.
        bounds: Rectangular ROI bounds in image pixel coordinates.
        grid: Raster viewer grid with physical spacing.

    Returns:
        Rectangular ROI overlay in Plotly coordinate space.
    """
    return RectRoiOverlay(
        roi_id=roi_id,
        x0=float(bounds.dim0_start) * grid.dx,
        x1=float(bounds.dim0_stop) * grid.dx,
        y0=float(bounds.dim1_start) * grid.dy,
        y1=float(bounds.dim1_stop) * grid.dy,
        label=str(roi_id),
    )


def _rect_roi_bounds_from_plot_coords(
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    grid: RasterGridSpec,
) -> RectRoiBounds:
    """Convert Plotly physical ROI coordinates to pixel-coordinate bounds.

    Args:
        x0: First x coordinate in Plotly coordinate space.
        x1: Second x coordinate in Plotly coordinate space.
        y0: First y coordinate in Plotly coordinate space.
        y1: Second y coordinate in Plotly coordinate space.
        grid: Raster viewer grid with physical spacing.

    Returns:
        Rectangular ROI bounds in acqstore row/column coordinates.
    """
    dim0_start, dim0_stop = sorted((int(round(x0 / grid.dx)), int(round(x1 / grid.dx))))
    dim1_start, dim1_stop = sorted((int(round(y0 / grid.dy)), int(round(y1 / grid.dy))))
    return RectRoiBounds(
        dim0_start=dim0_start,
        dim0_stop=dim0_stop,
        dim1_start=dim1_start,
        dim1_stop=dim1_stop,
    )


def _rect_roi_overlays_from_acq_image(acq_image: AcqImage, *, grid: RasterGridSpec) -> list[RectRoiOverlay]:
    """Build Plotly rectangular ROI overlays from an AcqImage.

    Args:
        acq_image: Acquisition image containing a ROI set.
        grid: Raster viewer grid with physical spacing.

    Returns:
        Rectangular ROI overlays. Non-rectangular ROIs are ignored.
    """
    overlays: list[RectRoiOverlay] = []
    for roi in acq_image.rois:
        if isinstance(roi, RectROI):
            overlays.append(_rect_roi_overlay_from_rect_roi(roi, grid=grid))
    return overlays

