"""Reference image view for AcqStore overview/reference images."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from nicegui import run, ui

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.file_loaders.base_file_loader import ReferenceImage, ReferenceImagePlane
from acqstore.acq_image.image_contrast import contrast_clip_min_max
from cloudscope.app_config import AppConfig
from cloudscope.contrast_seeding import contrast_auto_percentiles
from cloudscope.event_bus import EventBus
from cloudscope.events.theme import ThemeChanged
from cloudscope.raster_display_cache import (
    RasterDisplayCache,
    RasterDisplayCacheKey,
    RasterDisplayPlaneKind,
)
from cloudscope.session_state import (
    VIEW_SESSION_SCHEMA_VERSION,
    require_keys,
    require_schema_version,
    selection_guard_from_selection,
)
from cloudscope.utils.load_errors import format_raster_load_error
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec
from nicewidgets.raster_viewer.backend.pyramid import ImagePyramid
from nicewidgets.raster_viewer.frontend.plotly_display_options import (
    PlotlyRasterViewerDisplayOptions,
)
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer
from nicewidgets.raster_viewer.frontend.trace_overlay import PlotlyTraceOverlay

logger = get_logger(__name__)

# Overview pixel budget for the reference image. Typical reference images
# (e.g. 512x512, 2048x2048) fit within this budget and render the full extent
# at full pyramid resolution, so the static overview PNG matches the crisp
# zoomed-in heatmap instead of a coarse box-averaged thumbnail.
_REFERENCE_OVERVIEW_MAX_PIXELS = 4_000_000
_SCAN_PATH_TRACE_ID = 'scan_path'
_SCAN_PATH_TRACE_COLOR = 'cyan'
_SCAN_PATH_LINE_WIDTH = 4.0


@dataclass(slots=True)
class ReferenceImageViewState:
    """Serializable reconnect session state for :class:`ReferenceImageView`.

    The reference image reloads its plane from the current selection on rebuild,
    so only the user-mutable raster display options (context-menu toggles) are
    worth restoring. A viewport is intentionally omitted because reference plane
    reloads reset the Plotly viewport.

    Args:
        selection_guard: Selection identity captured at export time and used by
            :class:`BaseView` to skip stale reconnect blobs.
        display_options: Raster viewer display options.
        schema_version: Session blob schema version.
    """

    selection_guard: dict[str, Any]
    display_options: PlotlyRasterViewerDisplayOptions = field(
        default_factory=PlotlyRasterViewerDisplayOptions
    )
    schema_version: int = VIEW_SESSION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable session blob.

        Returns:
            Mapping with schema version, selection guard, and display options.
        """
        return {
            'schema_version': self.schema_version,
            'selection_guard': dict(self.selection_guard),
            'display_options': self.display_options.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReferenceImageViewState:
        """Build state from a blob produced by :meth:`to_dict`.

        Args:
            data: Session blob from :meth:`export_session_state`.

        Returns:
            Reconstructed :class:`ReferenceImageViewState`.

        Raises:
            KeyError: If required keys (including ``schema_version``) are absent.
            ValueError: If ``schema_version`` is unsupported.
        """
        require_schema_version(data)
        require_keys(data, 'selection_guard', 'display_options')
        return cls(
            selection_guard=dict(data['selection_guard']),
            display_options=PlotlyRasterViewerDisplayOptions.from_dict(data['display_options']),
            schema_version=int(data.get('schema_version', VIEW_SESSION_SCHEMA_VERSION)),
        )


def raster_grid_spec_from_reference_plane(plane: ReferenceImagePlane) -> RasterGridSpec:
    """Build a raster viewer grid from an AcqStore reference-image plane.

    Args:
        plane: Display-ready reference image plane from AcqStore.

    Returns:
        Raster viewer grid using the plane physical spacing and units.
    """
    return RasterGridSpec(
        dx=float(plane.dx),
        dy=float(plane.dy),
        x_unit=str(plane.x_unit),
        y_unit=str(plane.y_unit),
    )


def _load_reference_plane_payload(
    file_id: str | None,
    acq_image: AcqImage | None,
    channel: int | None,
) -> tuple[np.ndarray | None, RasterGridSpec | None, str, bool]:
    """Load reference-image payload for a selection.

    This function is safe to run off the UI thread with ``run.io_bound``.
    Channel and coordinate interpretation are delegated to AcqStore's
    :meth:`ReferenceImage.get_plane` API; this view does not infer array layout.

    Args:
        file_id: Selected file id, if any.
        acq_image: Selected acquisition image, if any.
        channel: Selected channel, if any.

    Returns:
        Tuple of ``(array, grid, message, is_real_reference)``. ``array`` and
        ``grid`` are ``None`` when no reference plane is available.
    """
    if file_id is None or acq_image is None:
        return None, None, 'No file selected', False

    reference_image = acq_image.images.reference_image
    if reference_image is None:
        return None, None, 'No reference image for selected file', False

    reference_plane = reference_image.get_plane(channel)
    grid = raster_grid_spec_from_reference_plane(reference_plane)
    array = np.asarray(reference_plane.array)
    return array, grid, 'Reference image', True


def _load_reference_display_payload(
    file_id: str | None,
    acq_image: AcqImage | None,
    channel: int | None,
    cache: RasterDisplayCache | None,
) -> tuple[np.ndarray | None, RasterGridSpec | None, ImagePyramid | None, str, bool]:
    """Load reference display payload, optionally using the raster display cache.

    This function is safe to run off the UI thread with ``run.io_bound``.

    Args:
        file_id: Selected file id, if any.
        acq_image: Selected acquisition image, if any.
        channel: Selected channel, if any.
        cache: Optional shared LRU cache for planes and pyramids.

    Returns:
        Tuple of ``(array, grid, pyramid, message, is_real_reference)``.
        ``array``, ``grid``, and ``pyramid`` are ``None`` when no reference
        plane is available. ``pyramid`` is ``None`` when no cache is configured.
    """
    plane, grid, message, is_real_reference = _load_reference_plane_payload(
        file_id,
        acq_image,
        channel,
    )
    if not is_real_reference or plane is None or grid is None or file_id is None or channel is None:
        return plane, grid, None, message, is_real_reference

    if cache is None:
        return plane, grid, None, message, is_real_reference

    key = RasterDisplayCacheKey(
        file_id=file_id,
        channel=int(channel),
        z=0,
        t=0,
        kind=RasterDisplayPlaneKind.REFERENCE,
    )

    def _load_plane() -> np.ndarray:
        loaded = np.asarray(plane)
        if loaded.ndim != 2:
            raise ValueError(f'Expected 2D reference plane (Y, X), got shape={loaded.shape}')
        return loaded

    entry = cache.get_or_build(key, plane_loader=_load_plane)
    return entry.plane, grid, entry.pyramid, message, is_real_reference


def scan_path_to_plotly_overlays(
    reference_image: ReferenceImage,
    *,
    grid: RasterGridSpec,
) -> list[PlotlyTraceOverlay]:
    """Translate a reference-image scan path to Plotly trace overlays.

    AcqStore exposes scan-path pixel coordinates as ``(x_pixels, y_pixels)``
    where ``x`` is the reference-image column axis and ``y`` is the row axis.
    The raster viewer maps rows to Plotly x and columns to Plotly y.

    Args:
        reference_image: AcqStore reference image snapshot.
        grid: Raster grid for the displayed reference plane.

    Returns:
        One overlay when a scan path is available, otherwise an empty list.

    Raises:
        ValueError: If the stored scan path is not shaped as ``(2, N)``.
    """
    if not reference_image.has_scan_path():
        return []
    scan_path_xy = reference_image.get_scan_path_plot()
    if scan_path_xy is None:
        return []
    x_pixels, y_pixels = scan_path_xy
    plotly_x = tuple(float(value) * grid.dx for value in y_pixels)
    plotly_y = tuple(float(value) * grid.dy for value in x_pixels)
    return [
        PlotlyTraceOverlay(
            trace_id=_SCAN_PATH_TRACE_ID,
            x=plotly_x,
            y=plotly_y,
            color=_SCAN_PATH_TRACE_COLOR,
            line_width=_SCAN_PATH_LINE_WIDTH,
            name='Scan path',
            mode='lines+markers',
            # TODO may want to switch back to just plotly_type 'scatter'.
            plotly_type='scattergl',
        )
    ]


def reference_contrast_window(
    plane: np.ndarray,
    *,
    percentile_low: float = 1.0,
    percentile_high: float = 99.5,
) -> tuple[float, float] | None:
    """Return a stable percentile contrast window for a reference image plane.

    Reuses :func:`contrast_clip_min_max` so the reference image PNG uses the
    same default-window logic as the primary image. The window is baked into
    the PNG pixels by the raster service, which keeps the overview contrast
    stable across pan/zoom instead of per-clip auto-stretching.

    Args:
        plane: 2D reference image array.
        percentile_low: Lower percentile for auto clipping.
        percentile_high: Upper percentile for auto clipping.

    Returns:
        ``(zmin, zmax)`` floats, or ``None`` when the plane is empty or the
        window is degenerate (``zmax <= zmin``). A ``None`` result leaves the
        viewer's per-clip auto-stretch in place.
    """
    if plane.size == 0:
        return None
    lo, hi = contrast_clip_min_max(
        plane,
        percentile_low=percentile_low,
        percentile_high=percentile_high,
    )
    if hi <= lo:
        return None
    return float(lo), float(hi)


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


class ReferenceImageView(BaseView):
    """Display the selected AcqImage reference image when one exists.

    The view is a thin CloudScope consumer of AcqStore's reference-image API. It
    does not interpret reference array dimensions, channel axes, units, or line
    ROI metadata; those concerns belong to AcqStore. ROI selection changes are
    intentionally ignored because reference images do not manage AcqImage ROIs.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional page/controller state object used to resync the
            primary selection when the view is shown after being hidden.
        title: Card title.
        initially_visible: Whether this view starts visible.
        dark_mode: Initial Plotly raster-viewer theme state.
        dark_mode_provider: Optional callable returning the current application
            dark-mode state when the view is shown after being hidden.
        raster_display_cache: Optional shared LRU cache for planes and pyramids.
    """

    view_id = ViewId.REFERENCE_IMAGE
    disable_when_busy = False

    def __init__(
        self,
        event_bus: EventBus,
        *,
        app_state: Any | None = None,
        title: str = 'Reference image',
        initially_visible: bool = True,
        dark_mode: bool = False,
        dark_mode_provider: Callable[[], bool] | None = None,
        raster_display_cache: RasterDisplayCache | None = None,
        app_config: AppConfig | None = None,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._title = title
        self._client: Any = None
        self._app_config = app_config
        self._viewer = PlotlyRasterViewer(
            display_options=PlotlyRasterViewerDisplayOptions(
                theme='dark' if dark_mode else 'light',
            )
        )
        self._last_file_id: str | None = None
        self._last_channel: int | None = None
        self._dark_mode_provider = dark_mode_provider
        self._raster_display_cache = raster_display_cache

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Create the reference image card.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        self._client = ui.context.client

        def _build() -> None:
            with ui.card().classes('w-full') as self.root:
                plot = self._viewer.build()
                plot.classes('w-full h-80')

        if parent is None:
            _build()
        else:
            with parent:
                _build()

        self.after_build()
        self._refresh_reference_from_current_selection(force=True)
        return self.root

    def export_session_state(self) -> dict[str, Any]:
        """Return a reconnect session blob for this view.

        Returns:
            JSON-serializable blob describing selection identity and current
            raster display options.
        """
        state = ReferenceImageViewState(
            selection_guard=selection_guard_from_selection(self.current_selection),
            display_options=self._viewer.display_options,
        )
        return state.to_dict()

    def apply_session_state(self, data: dict[str, Any]) -> None:
        """Apply a reconnect session blob to this view.

        Args:
            data: Blob produced by :meth:`export_session_state`.

        Returns:
            None.
        """
        state = ReferenceImageViewState.from_dict(data)
        self._apply_raster_display_options(state.display_options)

    def _apply_raster_display_options(self, options: PlotlyRasterViewerDisplayOptions) -> None:
        """Push raster viewer display options to the Plotly widget.

        Args:
            options: Desired viewer display options.

        Returns:
            None.
        """
        viewer = self._viewer
        viewer.set_plotly_toolbar_visible(options.show_plotly_toolbar)
        viewer.set_roi_overlays_visible(options.show_rois)
        viewer.set_roi_labels_visible(options.show_roi_labels)
        viewer.set_trace_overlays_visible(options.show_trace_overlays)
        viewer.set_x_axis_labels_visible(options.show_x_axis_labels)
        viewer.set_y_axis_labels_visible(options.show_y_axis_labels)
        viewer.set_square_plot(options.square_plot)
        viewer.set_hover_info_visible(options.show_hover_info)

    def subscribe_events(self) -> None:
        """Subscribe to reference-image-specific events while visible.

        BaseView already subscribes to primary selection and busy-state events.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(ThemeChanged, self._on_theme_changed))

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
        """Refresh only when file or channel changes.

        ROI-only selection changes are ignored by design because reference
        images are independent of runtime AcqImage ROI selection.

        Returns:
            None.
        """
        self._refresh_reference_from_current_selection(force=False)

    def refresh_from_state(self) -> None:
        """Refresh reference image from current app state.

        Returns:
            None.
        """
        self._sync_theme_from_provider()
        self._refresh_reference_from_current_selection(force=True)

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
                logger.warning('Reference image UI update dropped (no client): %s', exc)
                return
            self._client.safe_invoke(fn)

    def _refresh_reference_from_current_selection(self, *, force: bool) -> None:
        """Schedule reference image refresh from the cached selection.

        Args:
            force: When true, refresh even if file/channel did not change.

        Returns:
            None.
        """
        file_id = self.current_selection.file_id
        channel = self.current_selection.channel
        if not force and file_id == self._last_file_id and channel == self._last_channel:
            return
        self._last_file_id = file_id
        self._last_channel = channel
        acq_image = self.get_selected_acq_image()
        _schedule_coro(self._refresh_reference_async(file_id, acq_image, channel))

    async def _refresh_reference_async(
        self,
        file_id: str | None,
        acq_image: AcqImage | None,
        channel: int | None,
    ) -> None:
        """Load and display a reference image snapshot asynchronously.

        Args:
            file_id: Snapshot file id.
            acq_image: Snapshot acquisition image.
            channel: Snapshot channel.

        Returns:
            None.
        """
        try:
            plane, grid, pyramid, _message, is_real_reference = await run.io_bound(
                _load_reference_display_payload,
                file_id,
                acq_image,
                channel,
                self._raster_display_cache,
            )
        except Exception as exc:
            presentation = format_raster_load_error(
                exc,
                acq_image=acq_image,
                channel=channel,
                operation='Reference image',
            )
            logger.exception(presentation.log_message)
            self._run_ui(lambda: ui.notify(presentation.notify_message, type='negative'))
            try:
                await self._viewer.clear_data()
            except RuntimeError as inner:
                logger.warning('Reference image clear_data failed: %s', inner)
            return

        if not is_real_reference or plane is None or grid is None:
            try:
                await self._viewer.clear_data()
            except RuntimeError as exc:
                logger.exception('Reference image clear_data failed: %s', exc)
                err_msg = str(exc)
                self._run_ui(lambda: ui.notify(err_msg, type='negative'))
            return

        try:
            if pyramid is None:
                await self._viewer.set_data(
                    plane,
                    grid=grid,
                    overview_max_pixels=_REFERENCE_OVERVIEW_MAX_PIXELS,
                )
            else:
                await self._viewer.set_data_from_pyramid(
                    plane,
                    grid=grid,
                    pyramid=pyramid,
                    overview_max_pixels=_REFERENCE_OVERVIEW_MAX_PIXELS,
                )
            await self._apply_reference_contrast(plane)
            self._refresh_scan_path_trace_overlays(acq_image=acq_image, grid=grid)
        except (RuntimeError, ValueError) as exc:
            logger.exception('Reference image display refresh failed: %s', exc)
            err_msg = str(exc)
            self._run_ui(lambda: ui.notify(err_msg, type='negative'))

    def _refresh_scan_path_trace_overlays(
        self,
        *,
        acq_image: AcqImage | None,
        grid: RasterGridSpec | None,
    ) -> None:
        """Push reference-image scan-path trace overlays into the Plotly viewer.

        Args:
            acq_image: Current acquisition image, or None.
            grid: Current raster viewer grid, or None.

        Returns:
            None.

        Raises:
            ValueError: If the stored scan path is not shaped as ``(2, N)``.
        """
        if acq_image is None or grid is None:
            return
        reference_image = acq_image.images.reference_image
        if reference_image is None:
            return
        overlays = scan_path_to_plotly_overlays(reference_image, grid=grid)
        if overlays:
            self._viewer.set_trace_overlays(overlays)

    async def _apply_reference_contrast(self, plane: np.ndarray) -> None:
        """Bake a stable percentile contrast window into the reference PNG.

        No-op for empty or degenerate planes, which keeps the viewer's default
        per-clip auto-stretch. This is not wired to the contrast toolbar; the
        window is derived directly from the loaded plane.

        Args:
            plane: 2D reference image array just passed to the viewer.

        Returns:
            None.
        """
        percentile_low, percentile_high = contrast_auto_percentiles(self._app_config)
        window = reference_contrast_window(
            plane,
            percentile_low=percentile_low,
            percentile_high=percentile_high,
        )
        if window is None:
            return
        zmin, zmax = window
        try:
            await self._viewer.set_heatmap_contrast(zmin=zmin, zmax=zmax)
        except RuntimeError as exc:
            logger.warning('Skipping reference contrast (viewer not ready): %s', exc)
