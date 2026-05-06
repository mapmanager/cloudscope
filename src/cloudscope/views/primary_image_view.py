"""Primary raster image view: AcqStore slice + header calibration into ``PlotlyRasterViewer``.

``z`` / ``t`` are **not** raster-viewer concepts. They belong to :meth:`BaseFileLoader.get_slice_data`,
which defaults to ``z=0`` and ``t=0`` when omitted; CloudScope relies on those defaults for v1.

Pixel arrays are passed through from AcqStore without forced dtype conversion; the raster
pipeline casts where needed (e.g. PNG encoding uses ``float32`` internally).
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
from cloudscope.events import (
    FileSelectionChanged,
    ChannelSelectionChanged,
    RoiSelectionChanged,
)
from cloudscope.utils.logging import get_logger
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer

logger = get_logger(__name__)

_PLACEHOLDER_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='Pixels', y_unit='Pixels')


def raster_grid_spec_from_image_header(header: ImageHeader) -> RasterGridSpec:
    """Build :class:`RasterGridSpec` for a ``(Y, X)`` slice from ``ImageHeader`` calibration.

    The raster viewer uses numpy row index as plot **x** (here: **Y**) and column index as
    plot **y** (here: **X**). ``dx`` is the physical step per row (``Y``), ``dy`` per column
    (``X``).

    Args:
        header: Loader header with ``dims`` and ``physical_units`` aligned to ``dims``.

    Returns:
        Grid specification with strictly positive ``dx`` / ``dy``.

    Raises:
        ValueError: If ``Y`` or ``X`` is missing from ``dims``, or calibration is not a
            finite strictly positive step for either axis.
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
    """Tiny neutral plane when no file/channel is selected."""
    return np.zeros((2, 2), dtype=np.float32), _PLACEHOLDER_GRID


def _load_plane_payload(
    file_id: str | None,
    acq_image: AcqImage | None,
    channel: int | None,
) -> tuple[np.ndarray, RasterGridSpec]:
    """Load ``(array, grid)`` for the current selection (runs off the UI thread when used with ``io_bound``).

    Args:
        file_id: Selected file id, if any.
        acq_image: Resolved acquisition object, if any.
        channel: Selected channel index, if any.

    Returns:
        Two-dimensional array ``(Y, X)`` and its :class:`RasterGridSpec`.

    Raises:
        ValueError: If header calibration cannot be mapped (see :func:`raster_grid_spec_from_image_header`).
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
    """Run ``coro`` on the running loop, or ``asyncio.run`` when no loop exists."""
    try:
        asyncio.get_running_loop().create_task(coro)
    except RuntimeError:
        asyncio.run(coro)


class PrimaryImageView:
    """NiceGUI primary image panel driven by selection events and ``PlotlyRasterViewer``.

    Subscribes to ``FileSelectionChanged``, ``ChannelSelectionChanged``, and
    ``RoiSelectionChanged``. ROI id is cached for future drawing tickets; it does not
    change the raster in v1.

    Args:
        event_bus: Page-scoped event bus.
        title: Card title.
    """

    def __init__(self, event_bus: EventBus, *, title: str = 'Primary image') -> None:
        self._event_bus = event_bus
        self._title = title
        self._client: Any = None
        self._viewer = PlotlyRasterViewer()
        self._file_id: str | None = None
        self._acq_image: AcqImage | None = None
        self._channel: int | None = None
        self._roi_id: int | None = None

        self._event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed)
        self._event_bus.subscribe(ChannelSelectionChanged, self._on_channel_selection_changed)
        self._event_bus.subscribe(RoiSelectionChanged, self._on_roi_selection_changed)

    def build(self) -> None:
        """Create the card, title, and Plotly raster element.

        Returns:
            None.
        """
        self._client = ui.context.client
        plot = self._viewer.build()
        plot.classes('w-full h-80')
        self._refresh_raster()

    def _run_ui(self, fn: Callable[[], None]) -> None:
        """Run UI updates; remarshal via ``Client.safe_invoke`` when slot context is missing."""
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

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        self._file_id = event.file_id
        self._acq_image = event.acq_image
        self._channel = event.channel
        self._roi_id = event.roi_id
        self._refresh_raster()

    def _on_channel_selection_changed(self, event: ChannelSelectionChanged) -> None:
        self._channel = event.channel
        self._refresh_raster()

    def _on_roi_selection_changed(self, event: RoiSelectionChanged) -> None:
        self._roi_id = event.roi_id

    def _refresh_raster(self) -> None:
        """Schedule async reload of the raster from current selection."""
        _schedule_coro(self._refresh_raster_async())

    async def _refresh_raster_async(self) -> None:
        fid = self._file_id
        img = self._acq_image
        ch = self._channel
        try:
            plane, grid = await run.io_bound(_load_plane_payload, fid, img, ch)
        except Exception as exc:
            logger.exception('Primary plane load failed file_id=%r channel=%r', fid, ch)
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
            logger.info(f'  plane:{plane.shape} min:{plane.min()} max:{plane.max()}')
            logger.info(f'  grid:{grid}')
            await self._viewer.set_data(plane, grid=grid)
        except RuntimeError as exc:
            logger.exception('set_data failed: %s', exc)
            err_msg = str(exc)
            self._run_ui(lambda: ui.notify(err_msg, type='negative'))
