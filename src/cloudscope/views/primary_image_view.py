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
from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader
from cloudscope.event_bus import EventBus
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer

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
) -> tuple[np.ndarray, RasterGridSpec]:
    """Load ``(array, grid)`` for a selection.

    This function is safe to run off the UI thread with ``run.io_bound``.

    Args:
        file_id: Selected file id, if any.
        acq_image: Resolved acquisition object, if any.
        channel: Selected channel index, if any.

    Returns:
        Two-dimensional array ``(Y, X)`` and its :class:`RasterGridSpec`.

    Raises:
        ValueError: If header calibration cannot be mapped.
        IndexError: If ``channel`` is out of range for the loader.
    """
    if file_id is None or acq_image is None or channel is None:
        return _placeholder_plane()
    grid = raster_grid_spec_from_image_header(acq_image.images.header)
    plane = np.asarray(acq_image.images.get_slice_data(channel))
    if plane.ndim != 2:
        raise ValueError(f'Expected 2D slice (Y, X), got shape={plane.shape}')
    return plane, grid


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
    """

    view_id = ViewId.PRIMARY_IMAGE
    disable_when_busy = False

    def __init__(
        self,
        event_bus: EventBus,
        *,
        title: str = 'Primary image',
        initially_visible: bool = True,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self._title = title
        self._client: Any = None
        self._viewer = PlotlyRasterViewer()

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Create the card, title, and Plotly raster element.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        self._client = ui.context.client

        def _build() -> None:
            with ui.card().classes("w-full") as self.root:
                ui.label(self._title).classes("text-lg font-medium")
                plot = self._viewer.build()
                plot.classes('w-full h-80')

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
            plane, grid = await run.io_bound(_load_plane_payload, file_id, acq_image, channel)
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
            await self._viewer.set_data(plane, grid=grid)
        except RuntimeError as exc:
            logger.exception('set_data failed: %s', exc)
            err_msg = str(exc)
            self._run_ui(lambda: ui.notify(err_msg, type='negative'))
