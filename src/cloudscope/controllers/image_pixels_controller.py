"""Controller that loads full image pixel volumes before file selection is published.

:meth:`ensure_loaded` is invoked by :class:`HomePageController` before
``FileSelectionChanged`` is published. Views subscribe only to selection state
events and slice from memory via :meth:`BaseFileLoader.get_slice_data_loaded`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

from nicegui import run

from acqstore.acq_image.acq_image import AcqImage

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


class ImagePixelsController:
    """Ensure pixel data is loaded before selection state events are published."""

    def __init__(self) -> None:
        self._load_generation = 0
        self._active_file_id: str | None = None

    def ensure_loaded(
        self,
        file_id: str | None,
        acq_image: AcqImage | None,
        *,
        on_complete: Callable[[], None],
    ) -> None:
        """Load pixels when needed, then invoke ``on_complete``.

        When ``file_id`` or ``acq_image`` is ``None``, or pixels are already
        cached, ``on_complete`` runs synchronously. Otherwise the full volume
        is loaded off the UI thread and ``on_complete`` runs only when the
        request is still current.

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

        if acq_image.pixels_loaded():
            on_complete()
            return

        generation = self._load_generation
        _schedule_coro(self._load_pixels_async(generation, file_id, acq_image, on_complete))

    async def _load_pixels_async(
        self,
        generation: int,
        file_id: str,
        acq_image: AcqImage,
        on_complete: Callable[[], None],
    ) -> None:
        """Load pixel data off the UI thread and run ``on_complete`` when current.

        Args:
            generation: Load token captured when the async work was scheduled.
            file_id: File identifier for the load request.
            acq_image: Acquisition image whose pixels should be loaded.
            on_complete: Callback invoked after a successful, still-current load.

        Returns:
            None.
        """
        try:
            await run.io_bound(acq_image.load_image_data)
        except Exception:
            logger.exception(
                'Image pixel load failed file_id=%r',
                file_id,
            )
            return

        if generation != self._load_generation or self._active_file_id != file_id:
            return

        on_complete()
