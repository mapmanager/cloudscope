"""Reference image view for AcqStore overview/reference images."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any

import numpy as np
from nicegui import run, ui

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.file_loaders.base_file_loader import ReferenceImagePlane
from cloudscope.event_bus import EventBus
from cloudscope.events.theme import ThemeChanged
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.raster_viewer.backend.image_model import RasterGridSpec
from nicewidgets.raster_viewer.frontend.plotly_display_options import (
    PlotlyRasterViewerDisplayOptions,
)
from nicewidgets.raster_viewer.frontend.plotly_viewer import PlotlyRasterViewer

logger = get_logger(__name__)

_PLACEHOLDER_GRID = RasterGridSpec(dx=1.0, dy=1.0, x_unit='Pixels', y_unit='Pixels')


def _placeholder_plane() -> tuple[np.ndarray, RasterGridSpec, str]:
    """Return a tiny placeholder image for empty reference-image states.

    Returns:
        Placeholder image, grid specification, and display message.
    """
    return np.zeros((2, 2), dtype=np.float32), _PLACEHOLDER_GRID, 'No reference image'


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
) -> tuple[np.ndarray, RasterGridSpec, str]:
    """Load ``(array, grid, message)`` for a reference image selection.

    This function is safe to run off the UI thread with ``run.io_bound``.
    Channel and coordinate interpretation are delegated to AcqStore's
    :meth:`ReferenceImage.get_plane` API; this view does not infer array layout.

    Args:
        file_id: Selected file id, if any.
        acq_image: Selected acquisition image, if any.
        channel: Selected channel, if any.

    Returns:
        Two-dimensional reference image, grid specification, and status message.
    """
    if file_id is None or acq_image is None:
        plane, grid, _ = _placeholder_plane()
        return plane, grid, 'No file selected'

    reference_image = acq_image.images.reference_image
    if reference_image is None:
        plane, grid, _ = _placeholder_plane()
        return plane, grid, 'No reference image for selected file'

    reference_plane = reference_image.get_plane(channel)
    grid = raster_grid_spec_from_reference_plane(reference_plane)
    return np.asarray(reference_plane.array), grid, 'Reference image'


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
        title: Card title.
        initially_visible: Whether this view starts visible.
        dark_mode: Initial Plotly raster-viewer theme state.
        dark_mode_provider: Optional callable returning the current application
            dark-mode state when the view is shown after being hidden.
    """

    view_id = ViewId.REFERENCE_IMAGE
    disable_when_busy = False

    def __init__(
        self,
        event_bus: EventBus,
        *,
        title: str = 'Reference image',
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
            )
        )
        self._status_label: ui.label | None = None
        self._last_file_id: str | None = None
        self._last_channel: int | None = None
        self._dark_mode_provider = dark_mode_provider

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
                ui.label(self._title).classes('text-lg font-medium')
                self._status_label = ui.label('No reference image')
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
            plane, grid, message = await run.io_bound(
                _load_reference_plane_payload,
                file_id,
                acq_image,
                channel,
            )
        except Exception as exc:
            logger.exception('Reference image load failed file_id=%r channel=%r', file_id, channel)
            err_msg = str(exc)
            self._run_ui(lambda: ui.notify(err_msg, type='negative'))
            plane, grid, message = _placeholder_plane()
            message = f'Reference image error: {err_msg}'

        try:
            await self._viewer.set_data(plane, grid=grid)
            if self._status_label is not None:
                self._status_label.text = message
        except RuntimeError as exc:
            logger.exception('Reference image set_data failed: %s', exc)
            err_msg = str(exc)
            self._run_ui(lambda: ui.notify(err_msg, type='negative'))
