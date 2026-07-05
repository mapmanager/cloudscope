"""Primary raster image view: slice + header calibration into ``PlotlyRasterViewer``.

Lazy acquisition data loads are orchestrated by
:class:`cloudscope.controllers.acq_image_data_controller.AcqImageDataController`
before :class:`FileSelectionChanged` is published. This view refreshes from
:class:`BaseView` selection hooks and slices via
:meth:`BaseFileLoader.get_slice_data_loaded` (no implicit disk I/O).

``z`` / ``t`` are **not** raster-viewer concepts. They belong to
:meth:`BaseFileLoader.get_slice_data_loaded`. :class:`PrimaryImageView` owns
view-local ``z`` and ``t`` indices (default ``0``) and optional T/Z sliders
when the loaded header exposes multi-element ``T`` or ``Z`` axes.

Pixel arrays are passed through from AcqStore without forced dtype conversion;
the raster pipeline casts where needed (e.g. PNG encoding uses ``float32``
internally).
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from pathlib import Path

import numpy as np
from nicegui import run, ui

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.analysis.model import AnalysisKey, AnalysisOverlayTraceData
from acqstore.acq_image.roi import RectROI, RectRoiBounds
from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader
from acqstore.acq_image.metadata import ImageHeaderMetadata
from cloudscope.app_config import AppConfig, home_stack_layout_margins_profile
from cloudscope.contrast_seeding import (
    default_channel_color_lut,
    ensure_channel_contrast_from_plane,
    ephemeral_auto_contrast_from_plane,
)
from cloudscope.event_bus import EventBus
from cloudscope.events.analysis import AnalysisCompleted, AnalysisKind
from cloudscope.events.contrast import ImageContrastChanged, UpdateImageContrastIntent
from cloudscope.events.metadata import MetadataChanged
from cloudscope.events.raster import PrimaryPlaneLoaded
from cloudscope.events.roi import RoiChanged, RoiEditModeChanged, RoiEditPreviewChanged
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.x_range import PrimaryXRangeChanged, SetPrimaryXRangeIntent, x_ranges_equal
from cloudscope.raster_display_cache import (
    RasterDisplayCache,
    RasterDisplayCacheKey,
    RasterDisplayPlaneKind,
)
from cloudscope.utils.load_errors import format_raster_load_error
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.contrast_widget.colorscales import get_colorscale
from nicewidgets.raster_viewer.backend.pyramid import ImagePyramid
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec
from nicewidgets.raster_viewer.frontend.plotly_display_options import (
    PlotlyRasterViewerDisplayOptions,
)
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer
from nicewidgets.raster_viewer.frontend.roi_overlay import RectRoiOverlay
from nicewidgets.raster_viewer.frontend.trace_overlay import PlotlyTraceOverlay

logger = get_logger(__name__)

_IDLE_MESSAGE = 'No file selected'


def slice_slider_spec_for_header(header: ImageHeader, dim: str) -> tuple[int, int] | None:
    """Return inclusive slider bounds for one stack axis, or ``None`` when hidden.

    Args:
        header: Loader header describing file axis order and sizes.
        dim: Axis label, typically ``'T'`` or ``'Z'``.

    Returns:
        ``(min_index, max_index)`` when ``dim`` is present with size ``> 1``;
        otherwise ``None``.
    """
    if dim not in header.dims:
        return None
    count = int(header.sizes.get(dim, 1))
    if count <= 1:
        return None
    return 0, count - 1


def format_slice_slider_display(value: int, max_index: int) -> str:
    """Format a 0-based slice index and max for display beside a T/Z slider.

    Internal slider state and :meth:`BaseFileLoader.get_slice_data_loaded`
    indices remain 0-based; this helper is display-only and uses 1-based
    slice numbers (e.g. index ``0`` of ``10`` planes → ``'1/10'``).

    Args:
        value: Current 0-based slider value (inclusive lower bound is ``0``).
        max_index: Current 0-based slider maximum (inclusive).

    Returns:
        Human-readable ``'{display_value}/{display_count}'`` string.
    """
    return f'{int(value) + 1}/{int(max_index) + 1}'


def _configure_nicegui_slider_bounds(
    slider: ui.slider,
    *,
    min_index: int,
    max_index: int,
    value: int,
) -> int:
    """Apply ``min``/``max``/``value`` to an existing NiceGUI ``ui.slider``.

    Follows the working pattern in ``sandbox/slider_demo.py``:

    1. Mutate ``slider._props['min']`` / ``['max']`` directly (never
       ``slider.props('min=… max=…')`` for bounds — that breaks Quasar).
    2. Assign ``slider.value``.
    3. Call ``slider.update()`` to push state to the browser.

    Args:
        slider: Built NiceGUI slider element.
        min_index: Lower bound (inclusive).
        max_index: Upper bound (inclusive).
        value: Desired slider position before clamping.

    Returns:
        Clamped value written to the slider.
    """
    clamped = max(min_index, min(max_index, int(value)))
    
    # print('====================')
    # logger.info(f'min_index={min_index} {type(min_index)}')
    # logger.info(f'max_index={max_index} {type(max_index)}')
    # logger.info(f'value={value} {type(value)}')
    # logger.info(f'clamped={clamped} {type(clamped)}')
    # logger.info(f'slider._props={slider._props}')

    slider._props['min'] = int(min_index)
    slider._props['max'] = int(max_index)
    slider.value = clamped
    slider.update()

    # logger.debug(
    #     'slider bounds updated: min=%s max=%s value=%s',
    #     min_index,
    #     max_index,
    #     clamped,
    # )

    # logger.info('=== AFTER')
    # logger.info(f'slider._props={slider._props}')

    return clamped


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


def _load_plane_payload(
    file_id: str | None,
    acq_image: AcqImage | None,
    channel: int | None,
    *,
    z: int = 0,
    t: int = 0,
) -> tuple[np.ndarray, RasterGridSpec, bool] | None:
    """Load ``(array, grid, is_placeholder)`` for a selection.

    This function is safe to run off the UI thread with ``run.io_bound``.

    Args:
        file_id: Selected file id, if any.
        acq_image: Resolved acquisition object, if any.
        channel: Selected channel index, if any.
        z: Index along ``Z`` when present; ignored when absent.
        t: Index along ``T`` when present; ignored when absent.

    Returns:
        Tuple of two-dimensional array ``(Y, X)``, its :class:`RasterGridSpec`,
        and ``False`` when real data was loaded. ``None`` when there is no valid
        selection.

    Raises:
        ValueError: If header calibration cannot be mapped.
        IndexError: If ``channel`` is out of range for the loader.
    """
    if file_id is None or acq_image is None or channel is None:
        return None
    grid = raster_grid_spec_from_image_header(acq_image.images.header)
    plane = np.asarray(
        acq_image.images.get_slice_data_loaded(int(channel), z=int(z), t=int(t))
    )
    if plane.ndim != 2:
        raise ValueError(f'Expected 2D slice (Y, X), got shape={plane.shape}')
    return plane, grid, False


def _load_primary_display_payload(
    file_id: str | None,
    acq_image: AcqImage | None,
    channel: int | None,
    cache: RasterDisplayCache | None,
    *,
    z: int = 0,
    t: int = 0,
) -> tuple[np.ndarray, RasterGridSpec, ImagePyramid | None, bool] | None:
    """Load primary display payload, optionally using the raster display cache.

    This function is safe to run off the UI thread with ``run.io_bound``.

    Args:
        file_id: Selected file id, if any.
        acq_image: Resolved acquisition object, if any.
        channel: Selected channel index, if any.
        cache: Optional shared LRU cache for planes and pyramids.
        z: Index along ``Z`` when present; ignored when absent.
        t: Index along ``T`` when present; ignored when absent.

    Returns:
        Tuple of plane, grid, optional cached pyramid, and placeholder flag.
        ``pyramid`` is ``None`` when no cache is configured. The whole result is
        ``None`` when there is no valid selection.

    Raises:
        ValueError: If header calibration cannot be mapped or slice is not 2D.
        IndexError: If ``channel`` is out of range for the loader.
    """
    if file_id is None or acq_image is None or channel is None:
        return None

    grid = raster_grid_spec_from_image_header(acq_image.images.header)
    channel_index = int(channel)
    z_index = int(z)
    t_index = int(t)

    def _load_plane() -> np.ndarray:
        plane = np.asarray(
            acq_image.images.get_slice_data_loaded(
                channel_index,
                z=z_index,
                t=t_index,
            )
        )
        if plane.ndim != 2:
            raise ValueError(f'Expected 2D slice (Y, X), got shape={plane.shape}')
        return plane

    if cache is None:
        return _load_plane(), grid, None, False

    key = RasterDisplayCacheKey(
        file_id=file_id,
        channel=channel_index,
        z=z_index,
        t=t_index,
        kind=RasterDisplayPlaneKind.PRIMARY,
    )
    entry = cache.get_or_build(key, plane_loader=_load_plane)
    return entry.plane, grid, entry.pyramid, False


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
        raster_display_cache: Optional shared LRU cache for planes and pyramids.
        app_config: Optional shared app config for contrast seeding defaults.
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
        raster_display_cache: RasterDisplayCache | None = None,
        app_config: AppConfig | None = None,
        app_state: Any | None = None,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._title = title
        self._client: Any = None
        self._app_config = app_config
        self._viewer = PlotlyRasterViewer(
            display_options=PlotlyRasterViewerDisplayOptions(
                theme='dark' if dark_mode else 'light',
                show_trace_overlays=False,
                show_x_axis_labels=True,
                show_y_axis_labels=False,
                layout_margins_profile=home_stack_layout_margins_profile(),
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
        # Set when this view publishes x-range from its own Plotly viewer so
        # the consumer path does not round-trip ``set_x_axis_range`` back.
        self._viewer_originated_x_range = False
        self._raster_display_cache = raster_display_cache
        self._idle_label: ui.label | None = None
        self._z = 0
        self._t = 0
        self._last_file_id: str | None = None
        self._last_channel: int | None = None
        self._contrast_auto_per_slice = True
        self._manual_contrast_lut = 'Gray'
        self._manual_contrast_range: tuple[int, int] | None = None
        self._suppress_slider_events = False
        self._slice_refresh_generation = 0
        self._slice_row: ui.row | None = None
        self._t_group: ui.row | None = None
        self._z_group: ui.row | None = None
        self._t_axis_label: ui.label | None = None
        self._t_slice_label: ui.label | None = None
        self._t_slider: ui.slider | None = None
        self._z_axis_label: ui.label | None = None
        self._z_slice_label: ui.label | None = None
        self._z_slider: ui.slider | None = None

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
                with ui.element('div').classes('relative w-full h-full min-h-0 flex-1'):
                    plot = self._viewer.build()
                    plot.classes('w-full h-full min-h-0')
                    self._idle_label = ui.label(_IDLE_MESSAGE).classes(
                        'absolute inset-0 flex items-center justify-center opacity-70 pointer-events-none'
                    )
                with ui.row().classes('w-full items-center gap-2 px-1 py-1 shrink-0') as self._slice_row:
                    with ui.row().classes('hidden items-center gap-2 flex-1 min-w-0') as self._t_group:
                        self._t_axis_label = ui.label('T').classes('shrink-0 text-sm font-medium')
                        self._t_slider = ui.slider(min=0, max=0, value=0, step=1).classes('flex-1 min-w-0')
                        self._t_slice_label = ui.label('1/1').classes(
                            'shrink-0 tabular-nums text-sm'
                        )
                        self._t_slider.on_value_change(self._on_t_slider_changed)
                    with ui.row().classes('hidden items-center gap-2 flex-1 min-w-0') as self._z_group:
                        self._z_axis_label = ui.label('Z').classes('shrink-0 text-sm font-medium')
                        self._z_slider = ui.slider(min=0, max=0, value=0, step=1).classes('flex-1 min-w-0')
                        self._z_slice_label = ui.label('1/1').classes(
                            'shrink-0 tabular-nums text-sm'
                        )
                        self._z_slider.on_value_change(self._on_z_slider_changed)

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
            self.event_bus.subscribe(UpdateImageContrastIntent, self._on_update_contrast_intent)
        )
        self.add_subscription(
            self.event_bus.subscribe(PrimaryXRangeChanged, self._on_primary_x_range_changed)
        )
        self.add_subscription(
            self.event_bus.subscribe(MetadataChanged, self._on_metadata_changed)
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
        candidate = (x_min, x_max)
        if x_ranges_equal(candidate, self._primary_x_range):
            return
        self._viewer_originated_x_range = True
        self.event_bus.publish(SetPrimaryXRangeIntent(x_min=x_min, x_max=x_max))

    def _acq_image_for_slice_sliders(self) -> AcqImage | None:
        """Return the acquisition image whose header drives T/Z slider bounds.

        ``PrimaryImageView`` is built without ``app_state``; slider bounds must
        come from ``current_acq_image`` on :class:`FileSelectionChanged`. Reject
        a cached image whose ``file_id`` differs from ``current_selection`` so a
        stale header cannot leave the browser slider at the previous file's
        ``max`` (including ``max=0`` from the placeholder build).

        Returns:
            Matching :class:`AcqImage`, or ``None`` when unavailable or stale.
        """
        file_id = self.current_selection.file_id
        if file_id is None:
            return None
        acq_image = self.current_acq_image
        if acq_image is None:
            acq_image = self.get_acq_image_by_file_id(file_id)
        if acq_image is None:
            return None
        try:
            paths_match = Path(acq_image.file_id).resolve() == Path(file_id).resolve()
        except OSError:
            paths_match = str(acq_image.file_id) == str(file_id)
        if not paths_match:
            logger.warning(
                'slice slider sync skipped: stale acq_image file_id=%s selection=%s',
                acq_image.file_id,
                file_id,
            )
            return None
        return acq_image

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

    def _on_metadata_changed(self, event: MetadataChanged) -> None:
        """Refresh axis calibration when image-header metadata changes.

        Physical unit edits do not require rebuilding the cached pyramid; the
        refresh re-applies the current header grid to the cached plane.

        Args:
            event: Metadata state event.

        Returns:
            None.
        """
        if event.metadata_section_id != ImageHeaderMetadata.metadata_section_id:
            return
        if event.file_id != self.current_selection.file_id:
            return
        self._refresh_raster_from_current_selection()

    def _on_primary_x_range_changed(self, event: PrimaryXRangeChanged) -> None:
        """Consumer: cache the authoritative x-range and apply it to the viewer.

        Args:
            event: State event from :class:`XRangeController`.

        Returns:
            None.
        """
        self._primary_x_range = (event.x_min, event.x_max)
        if self._viewer_originated_x_range:
            self._viewer_originated_x_range = False
            return
        self._apply_primary_x_range_to_viewer()

    def _apply_primary_x_range_to_viewer(self, *, include_auto: bool = True) -> None:
        """Push the cached ``primary_x_range`` to the Plotly viewer.

        * ``(None, None)`` -> schedule ``reset_x_axis_to_full_extent`` when
          ``include_auto`` is True (linked 1D plot double-click reset).
        * ``(x_min, x_max)`` -> schedule ``set_x_axis_range``.

        After ``set_data``, callers pass ``include_auto=False`` so auto-range
        from the new dataset is not overridden.

        Skipped silently when the viewer has no data yet.

        Returns:
            None.
        """
        if not self._viewer.has_data:
            return
        x_min, x_max = self._primary_x_range
        if x_min is None or x_max is None:
            if include_auto:
                asyncio.create_task(self._viewer.reset_x_axis_to_full_extent())
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
        """Refresh the raster when BaseView selection changes.

        Returns:
            None.
        """
        file_id = self.current_selection.file_id
        channel = self.current_selection.channel
        if file_id != self._last_file_id:
            self._z = 0
            self._t = 0
            self._contrast_auto_per_slice = True
            self._manual_contrast_range = None
        elif channel != self._last_channel:
            self._contrast_auto_per_slice = True
            self._manual_contrast_range = None
        self._last_file_id = file_id
        self._last_channel = channel
        # Cancel in-flight Z/T slice reloads from the previous selection so a
        # stale Path B completion cannot overwrite the new file's viewer state.
        self._slice_refresh_generation += 1
        self._sync_slice_sliders_from_header()
        self._refresh_raster_from_current_selection(include_overlays=True)

    def _set_idle_visible(self, visible: bool, message: str = _IDLE_MESSAGE) -> None:
        """Show or hide the idle-state label over the raster viewer.

        Args:
            visible: Whether the idle label should be visible.
            message: Text to display when idle.

        Returns:
            None.
        """
        if self._idle_label is None:
            return
        self._idle_label.text = message
        self._idle_label.set_visibility(visible)

    async def _clear_primary_display(self, message: str = _IDLE_MESSAGE) -> None:
        """Clear raster data and show the idle label.

        Args:
            message: Idle-state message to display.

        Returns:
            None.
        """
        try:
            await self._viewer.clear_data()
        except RuntimeError as exc:
            logger.warning('Primary image clear_data failed: %s', exc)
        self._current_grid = None
        self._run_ui(lambda: self._set_idle_visible(True, message))

    def refresh_from_state(self) -> None:
        """Refresh raster from cached BaseView selection.

        Returns:
            None.
        """
        self._sync_theme_from_provider()
        self._sync_slice_sliders_from_header()
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

    def _refresh_raster_from_current_selection(self, *, include_overlays: bool = True) -> None:
        """Schedule async reload of the raster from the current selection.

        Args:
            include_overlays: When ``True``, refresh ROI and diameter overlays
                after the plane loads. Slice-only refreshes pass ``False``.

        Returns:
            None.
        """
        file_id = self.current_selection.file_id
        acq_image = self.get_selected_acq_image()
        channel = self.current_selection.channel
        _schedule_coro(
            self._refresh_raster_async(
                file_id,
                acq_image,
                channel,
                z=self._z,
                t=self._t,
                include_overlays=include_overlays,
            )
        )

    def _refresh_raster_for_slice_change(self) -> None:
        """Schedule a plane-only reload after a T/Z slider change.

        Returns:
            None.
        """
        self._slice_refresh_generation += 1
        generation = self._slice_refresh_generation
        file_id = self.current_selection.file_id
        acq_image = self.get_selected_acq_image()
        channel = self.current_selection.channel
        # logger.debug(
        #     'Primary raster Path B (Z/T scrub): file_id=%s channel=%s z=%s t=%s gen=%s',
        #     file_id,
        #     channel,
        #     self._z,
        #     self._t,
        #     generation,
        # )
        _schedule_coro(
            self._refresh_raster_async(
                file_id,
                acq_image,
                channel,
                z=self._z,
                t=self._t,
                include_overlays=False,
                slice_generation=generation,
            )
        )

    def _on_t_slider_changed(self, event: Any) -> None:
        """Update the view-local ``t`` index and reload the display plane.

        Args:
            event: NiceGUI slider value-change event.

        Returns:
            None.
        """
        if self._suppress_slider_events:
            return
        self._t = int(event.value)
        if self._t_slider is not None and self._t_slice_label is not None:
            self._t_slice_label.text = format_slice_slider_display(
                self._t,
                int(self._t_slider._props['max']),
            )
        self._refresh_raster_for_slice_change()

    def _on_z_slider_changed(self, event: Any) -> None:
        """Update the view-local ``z`` index and reload the display plane.

        Args:
            event: NiceGUI slider value-change event.

        Returns:
            None.
        """
        if self._suppress_slider_events:
            # logger.debug('Z slider change suppressed')
            return
        # logger.debug('Z slider changed: value=%s', event.value)
        self._z = int(event.value)
        if self._z_slider is not None and self._z_slice_label is not None:
            self._z_slice_label.text = format_slice_slider_display(
                self._z,
                int(self._z_slider._props['max']),
            )
        self._refresh_raster_for_slice_change()

    def _sync_slice_sliders_from_header(self) -> None:
        """Show or hide T/Z sliders and sync values from the current header.

        Returns:
            None.
        """
        if (
            self._t_group is None
            or self._z_group is None
            or self._t_slider is None
            or self._z_slider is None
            or self._t_slice_label is None
            or self._z_slice_label is None
        ):
            return
        acq_image = self._acq_image_for_slice_sliders()
        if acq_image is None:
            # logger.debug(
            #     'slice slider sync: no acq_image for file_id=%s',
            #     self.current_selection.file_id,
            # )
            self._run_ui(self._hide_slice_sliders)
            return

        header = acq_image.images.header
        t_spec = slice_slider_spec_for_header(header, 'T')
        z_spec = slice_slider_spec_for_header(header, 'Z')
        # logger.debug(
        #     'slice slider sync: file_id=%s z_spec=%s t_spec=%s view_z=%s view_t=%s',
        #     self.current_selection.file_id,
        #     z_spec,
        #     t_spec,
        #     self._z,
        #     self._t,
        # )

        def _apply() -> None:
            assert self._t_group is not None
            assert self._z_group is not None
            assert self._t_slider is not None
            assert self._z_slider is not None
            assert self._t_slice_label is not None
            assert self._z_slice_label is not None
            self._suppress_slider_events = True
            try:
                if t_spec is None:
                    self._t_group.classes(add='hidden', remove='flex-1')
                else:
                    t_min, t_max = t_spec
                    self._t = _configure_nicegui_slider_bounds(
                        self._t_slider,
                        min_index=t_min,
                        max_index=t_max,
                        value=self._t,
                    )
                    self._t_slice_label.text = format_slice_slider_display(self._t, t_max)
                    self._t_group.classes(remove='hidden', add='flex-1')

                if z_spec is None:
                    self._z_group.classes(add='hidden', remove='flex-1')
                else:
                    z_min, z_max = z_spec
                    self._z = _configure_nicegui_slider_bounds(
                        self._z_slider,
                        min_index=z_min,
                        max_index=z_max,
                        value=self._z,
                    )
                    self._z_slice_label.text = format_slice_slider_display(self._z, z_max)
                    self._z_group.classes(remove='hidden', add='flex-1')
            finally:
                self._suppress_slider_events = False

        self._run_ui(_apply)

    def _hide_slice_sliders(self) -> None:
        """Hide both T/Z slice control groups when no file is selected."""
        if self._t_group is not None:
            self._t_group.classes(add='hidden', remove='flex-1')
        if self._z_group is not None:
            self._z_group.classes(add='hidden', remove='flex-1')

    async def _refresh_raster_async(
        self,
        file_id: str | None,
        acq_image: AcqImage | None,
        channel: int | None,
        *,
        z: int,
        t: int,
        include_overlays: bool,
        slice_generation: int | None = None,
    ) -> None:
        """Load and display one raster snapshot asynchronously.

        Args:
            file_id: Snapshot file id.
            acq_image: Snapshot acquisition image.
            channel: Snapshot channel.
            z: Snapshot ``Z`` slice index.
            t: Snapshot ``T`` slice index.
            include_overlays: When ``True``, refresh ROI and diameter overlays.
            slice_generation: When set, drop stale completions from superseded
                Z/T scrubs so only the latest slice reload mutates the viewer.

        Returns:
            None.
        """
        # path_label = 'B-slice' if not include_overlays else 'A-selection'

        def _refresh_context_stale() -> bool:
            if (
                slice_generation is not None
                and slice_generation != self._slice_refresh_generation
            ):
                return True
            sel = self.current_selection
            if file_id != sel.file_id or channel != sel.channel:
                return True
            if z != self._z or t != self._t:
                return True
            return False

        # logger.debug(
        #     'Primary raster refresh start: path=%s file_id=%s channel=%s z=%s t=%s gen=%s',
        #     path_label,
        #     file_id,
        #     channel,
        #     z,
        #     t,
        #     slice_generation,
        # )

        if _refresh_context_stale():
            # logger.debug(
            #     'Primary raster refresh dropped (stale before load): path=%s '
            #     'file_id=%s channel=%s z=%s t=%s gen=%s current_gen=%s',
            #     path_label,
            #     file_id,
            #     channel,
            #     z,
            #     t,
            #     slice_generation,
            #     self._slice_refresh_generation,
            # )
            return
        try:
            payload = await run.io_bound(
                _load_primary_display_payload,
                file_id,
                acq_image,
                channel,
                self._raster_display_cache,
                z=z,
                t=t,
            )
        except Exception as exc:
            presentation = format_raster_load_error(
                exc,
                acq_image=acq_image,
                channel=channel,
                operation='Primary image',
            )
            logger.exception(presentation.log_message)
            self._run_ui(lambda: ui.notify(presentation.notify_message, type='negative'))
            await self._clear_primary_display()
            return

        if payload is None:
            await self._clear_primary_display()
            return

        if _refresh_context_stale():
            # logger.debug(
            #     'Primary raster refresh dropped (stale after load): path=%s '
            #     'file_id=%s channel=%s z=%s t=%s gen=%s current_gen=%s',
            #     path_label,
            #     file_id,
            #     channel,
            #     z,
            #     t,
            #     slice_generation,
            #     self._slice_refresh_generation,
            # )
            return

        plane, grid, pyramid, is_placeholder = payload
        if is_placeholder:
            await self._clear_primary_display()
            return

        try:
            self._current_grid = grid
            self._run_ui(lambda: self._set_idle_visible(False))
            if _refresh_context_stale():
                # logger.debug(
                #     'Primary raster refresh dropped (stale before viewer): path=%s '
                #     'file_id=%s channel=%s z=%s t=%s gen=%s current_gen=%s',
                #     path_label,
                #     file_id,
                #     channel,
                #     z,
                #     t,
                #     slice_generation,
                #     self._slice_refresh_generation,
                # )
                return
            if pyramid is None:
                await self._viewer.set_data(plane, grid=grid)
            elif not include_overlays:
                preserved_viewport = self._viewer.get_viewport()
                response = await self._viewer.swap_slice_plane(
                    plane,
                    grid=grid,
                    pyramid=pyramid,
                    display_axis_ranges=preserved_viewport,
                )
                # logger.debug(
                #     'Primary raster Path B pushed to viewer: mode=%s level=%s z=%s t=%s',
                #     response.mode,
                #     response.level,
                #     z,
                #     t,
                # )
            else:
                await self._viewer.set_data_from_pyramid(
                    plane, grid=grid, pyramid=pyramid
                )
            if include_overlays:
                self._refresh_roi_overlays(acq_image=acq_image, grid=grid)
                self._refresh_diameter_trace_overlays(acq_image=acq_image, grid=grid)
            if not is_placeholder and file_id is not None and channel is not None and acq_image is not None:
                channel_index = int(channel)
                if acq_image.get_image_contrast(channel_index) is None:
                    ensure_channel_contrast_from_plane(
                        acq_image,
                        channel_index,
                        plane,
                        self._app_config,
                    )
                await self._apply_display_contrast(
                    plane,
                    channel_index,
                    preserve_viewport=not include_overlays,
                )
                try:
                    plane.setflags(write=False)
                except (AttributeError, ValueError):
                    # Non-ndarray or already read-only; safe to proceed.
                    pass
                self.event_bus.publish(
                    PrimaryPlaneLoaded(
                        file_id=file_id,
                        channel=int(channel),
                        z=int(z),
                        t=int(t),
                        plane=plane,
                        use_auto_contrast=self._contrast_auto_per_slice,
                    )
                )
            # Re-apply any non-auto app-level x-range that survives ``set_data``
            # (e.g. analysis-row click within the same file). When the cached
            # range is ``(None, None)`` this is a no-op and ``set_data``'s own
            # auto-range stands. Z/T slice scrubs must not re-apply x-only zoom
            # on top of a full ``set_data`` reset — that leaves inconsistent
            # x/y viewport state and breaks double-click reset and Z/T sliders.
            if include_overlays:
                self._apply_primary_x_range_to_viewer(include_auto=False)
                self._sync_slice_sliders_from_header()
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

    def _on_update_contrast_intent(self, event: UpdateImageContrastIntent) -> None:
        """Track auto vs sticky manual contrast mode from toolbar edits.

        Args:
            event: User contrast update intent.

        Returns:
            None.
        """
        selection = self.current_selection
        if selection.file_id != event.file_id or selection.channel != int(event.channel):
            return
        if event.from_auto:
            self._contrast_auto_per_slice = True
            self._manual_contrast_range = None
        else:
            self._contrast_auto_per_slice = False
            self._manual_contrast_lut = str(event.color_lut)
            self._manual_contrast_range = (int(event.value_min), int(event.value_max))
        _schedule_coro(
            self._apply_contrast_style(
                str(event.color_lut),
                int(event.value_min),
                int(event.value_max),
            )
        )

    async def _apply_contrast_style(
        self,
        color_lut: str,
        value_min: int,
        value_max: int,
        *,
        preserve_viewport: bool = False,
    ) -> None:
        """Push one LUT/intensity window to the Plotly viewer.

        Args:
            color_lut: LUT identifier.
            value_min: Heatmap minimum intensity.
            value_max: Heatmap maximum intensity.
            preserve_viewport: When ``True``, keep the current Plotly viewport
                during overview PNG re-encode on slice scrubs.

        Returns:
            None.
        """
        scale = get_colorscale(color_lut)
        try:
            await self._viewer.set_heatmap_style(
                colorscale=scale,
                zmin=float(value_min),
                zmax=float(value_max),
                preserve_viewport=preserve_viewport,
            )
        except RuntimeError as exc:
            logger.warning('Skipping contrast apply (viewer not ready): %s', exc)

    async def _apply_display_contrast(
        self,
        plane: np.ndarray,
        channel: int,
        *,
        preserve_viewport: bool = False,
    ) -> None:
        """Apply ephemeral auto or sticky manual contrast to the viewer.

        Does not write contrast state to :class:`AcqImage` on slice navigation.

        Args:
            plane: Current 2D display plane.
            channel: Zero-based channel index.
            preserve_viewport: When ``True``, keep the current Plotly viewport
                during overview PNG re-encode on slice scrubs.

        Returns:
            None.
        """
        if self._contrast_auto_per_slice:
            value_min, value_max = ephemeral_auto_contrast_from_plane(plane, self._app_config)
            color_lut = default_channel_color_lut(self._app_config, channel)
        else:
            color_lut = self._manual_contrast_lut
            if self._manual_contrast_range is None:
                value_min, value_max = ephemeral_auto_contrast_from_plane(plane, self._app_config)
            else:
                value_min, value_max = self._manual_contrast_range
        await self._apply_contrast_style(color_lut, value_min, value_max, preserve_viewport=preserve_viewport)

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
        await self._apply_contrast_style(
            contrast.color_lut,
            contrast.value_min,
            contrast.value_max,
        )

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
        # logger.info('is this getting called twice?')
        
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

