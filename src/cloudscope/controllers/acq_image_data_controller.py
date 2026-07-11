"""Controller for AcqImage lazy data load/unload lifecycle.

:meth:`ensure_loaded_for_selection` is invoked by :class:`HomePageController`
before ``FileSelectionChanged`` is published. Views subscribe only to selection
state events and read already-loaded data. This controller also owns runtime
unload so views do not need to know about lazy-loading internals.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from nicegui import run

from acqstore.acq_image.acq_image import AcqImage

from cloudscope.event_bus import EventBus
from cloudscope.events.files import ImageDataLoaded, ImageDataUnloaded
from cloudscope.events.status import AppStatusChanged, StatusLevel, StatusSource
from cloudscope.raster_display_cache import RasterDisplayCache
from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)


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


class AcqImageDataController:
    """Ensure AcqImage lazy data is loaded/unloaded by controllers, not views."""

    def __init__(
        self,
        *,
        event_bus: EventBus | None = None,
        raster_display_cache: RasterDisplayCache | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._raster_display_cache = raster_display_cache
        # Monotonic token used to ignore stale async loads when selection changes
        # before an earlier disk I/O request finishes. Private to this controller.
        self._load_generation = 0
        self._active_file_id: str | None = None

    def ensure_loaded_for_selection(
        self,
        file_id: str | None,
        acq_image: AcqImage | None,
        *,
        on_complete: Callable[[], None],
    ) -> None:
        """Load lazy data when needed, then invoke ``on_complete``.

        When ``file_id`` or ``acq_image`` is ``None``, or all required lazy
        data are already cached, ``on_complete`` runs synchronously. Otherwise
        primary pixels and analysis CSV tables are loaded off the UI thread and
        ``on_complete`` runs only when the request is still current.

        Args:
            file_id: Selected file identifier, if any.
            acq_image: Resolved acquisition object when a backend list is loaded.
            on_complete: Callback invoked after pixels are ready. Typically
                publishes :class:`FileSelectionChanged`.

        Returns:
            None.
        """
        if file_id is None or acq_image is None:
            on_complete()
            return

        if file_id != self._active_file_id:
            self._active_file_id = file_id
            self._load_generation += 1

        if acq_image.is_fully_loaded:
            on_complete()
            return

        generation = self._load_generation
        _schedule_coro(self._load_lazy_data_async(generation, file_id, acq_image, on_complete))

    def unload_file_data(
        self,
        file_id: str,
        acq_image: AcqImage,
        *,
        on_complete: Callable[[], None] | None = None,
    ) -> None:
        """Unload one file's lazy data off the UI event loop.

        Args:
            file_id: Stable acquisition file identifier.
            acq_image: Acquisition image to unload.
            on_complete: Optional callback invoked after successful unload.
        """
        _schedule_coro(self._unload_file_data_async(file_id, acq_image, on_complete))

    async def _load_lazy_data_async(
        self,
        generation: int,
        file_id: str,
        acq_image: AcqImage,
        on_complete: Callable[[], None],
    ) -> None:
        """Load lazy data off the UI thread and run ``on_complete`` when current.

        Args:
            generation: Load token captured when the async work was scheduled.
            file_id: File identifier for the load request.
            acq_image: Acquisition image whose pixels should be loaded.
            on_complete: Callback invoked after a successful, still-current load.

        Returns:
            None.
        """
        try:
            await run.io_bound(acq_image.load_lazy_data)
        except Exception as exc:
            logger.exception('AcqImage lazy data load failed file_id=%r', file_id)
            self._publish_status(
                StatusLevel.ERROR,
                f'Image data load failed for {acq_image.name}: {exc}',
            )
            return

        if generation != self._load_generation or self._active_file_id != file_id:
            return

        if self._event_bus is not None:
            self._event_bus.publish(
                ImageDataLoaded(
                    file_id=file_id,
                    file_list_row=dict(acq_image.get_schema_row()),
                )
            )
        on_complete()


    async def _unload_file_data_async(
        self,
        file_id: str,
        acq_image: AcqImage,
        on_complete: Callable[[], None] | None,
    ) -> None:
        """Unload lazy data off the UI thread and publish refresh state.

        Args:
            file_id: Stable acquisition file identifier.
            acq_image: Acquisition image to unload.
            on_complete: Optional callback invoked after successful unload.
        """
        try:
            await run.io_bound(acq_image.unload_lazy_data)
        except Exception as exc:
            logger.exception('AcqImage lazy data unload failed file_id=%r', file_id)
            self._publish_status(
                StatusLevel.ERROR,
                f'Image data unload failed for {acq_image.name}: {exc}',
            )
            return

        if self._raster_display_cache is not None:
            self._raster_display_cache.invalidate_file(file_id)
        if self._event_bus is not None:
            self._event_bus.publish(
                ImageDataUnloaded(
                    file_id=file_id,
                    file_list_row=dict(acq_image.get_schema_row()),
                )
            )
        if on_complete is not None:
            on_complete()

    def _publish_status(self, level: StatusLevel, message: str) -> None:
        """Publish a user-visible status event when an event bus is available."""
        if self._event_bus is None:
            return
        self._event_bus.publish(
            AppStatusChanged(
                level=level,
                source=StatusSource.LOAD,
                message=message,
            )
        )
