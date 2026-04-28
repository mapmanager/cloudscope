"""CloudScope wrapper for the general-purpose ImageToolbarWidget."""

from __future__ import annotations

from typing import Protocol

from nicegui import ui

from acqstore.acq_image.acq_image import AcqImage
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import (
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
    SelectChannelIntent,
    SelectRoiIntent,
)
from nicewidgets.image_toolbar_widget.image_toolbar_widget import ImageToolbarWidget
from nicewidgets.image_toolbar_widget.intent import (
    ImageToolbarIntent,
    ImageToolbarSelectChannelIntent,
    ImageToolbarSelectRoiIntent,
)


class _ImageHelperProtocol(Protocol):
    """Minimal image-helper surface required by the toolbar view."""

    @property
    def channel_indices(self) -> list[int]:
        """Return channel indices available for this image."""


class _RoiHelperProtocol(Protocol):
    """Minimal ROI-helper surface required by the toolbar view."""

    def get_roi_ids(self) -> list[int]:
        """Return ROI identifiers in display order."""


def channel_options_for_acq_image(acq_image: AcqImage) -> list[str]:
    """Return toolbar channel option strings for one acquisition image.

    Args:
        acq_image: Acquisition image whose image helper exposes
            ``channel_indices``.

    Returns:
        Channel option strings expected by ``ImageToolbarWidget``.
    """
    images: _ImageHelperProtocol = acq_image.images
    return [str(channel) for channel in images.channel_indices]


def roi_options_for_acq_image(acq_image: AcqImage) -> list[int]:
    """Return toolbar ROI option integers for one acquisition image.

    Args:
        acq_image: Acquisition image whose ROI helper exposes ``get_roi_ids``.

    Returns:
        ROI identifiers expected by ``ImageToolbarWidget``.
    """
    rois: _RoiHelperProtocol = acq_image.rois
    return list(rois.get_roi_ids())


class ImageToolbarView:
    """CloudScope view wrapper around ``nicewidgets.ImageToolbarWidget``.

    The wrapped widget emits NiceWidgets intent dataclasses. This view converts
    selection intents into CloudScope intent events. ROI CRUD/edit intents are
    intentionally ignored in this first integration pass because CloudScope does
    not yet define ROI mutation events.

    Args:
        event_bus: CloudScope event bus used to publish selection intents and
            consume selection state events.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._toolbar: ImageToolbarWidget | None = None

        self._event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed)
        self._event_bus.subscribe(ChannelSelectionChanged, self._on_channel_selection_changed)
        self._event_bus.subscribe(RoiSelectionChanged, self._on_roi_selection_changed)

    def build(self, parent: ui.element | None = None) -> ImageToolbarWidget:
        """Build and return the underlying NiceWidgets image toolbar.

        Args:
            parent: Optional NiceGUI parent element. If omitted, the widget is
                built in the current slot.

        Returns:
            Created ``ImageToolbarWidget``.
        """
        if parent is None:
            self._toolbar = ImageToolbarWidget(on_intent=self._on_toolbar_intent)
            return self._toolbar

        with parent:
            self._toolbar = ImageToolbarWidget(on_intent=self._on_toolbar_intent)
            return self._toolbar

    def _on_toolbar_intent(self, intent: ImageToolbarIntent) -> None:
        """Translate NiceWidgets toolbar intents into CloudScope intents.

        Args:
            intent: NiceWidgets toolbar intent emitted by user interaction.

        Returns:
            None.
        """
        if isinstance(intent, ImageToolbarSelectChannelIntent):
            self._event_bus.publish(SelectChannelIntent(channel=intent.channel))
            return

        if isinstance(intent, ImageToolbarSelectRoiIntent):
            self._event_bus.publish(SelectRoiIntent(roi_id=intent.roi_id))
            return

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        """Update toolbar file, option lists, and channel/ROI from file selection."""
        if self._toolbar is None:
            return

        if event.file_id is None:
            self._toolbar.set_file_ext(
                None,
                None,
                None,
                channel_options=[],
                roi_options=[],
            )
            return

        acq_image = event.acq_image
        if acq_image is None:
            ch_opts, r_opts = self._synthetic_options_for_demo(event.channel, event.roi_id)
            self._toolbar.set_file_ext(
                event.file_id,
                event.channel,
                event.roi_id,
                channel_options=ch_opts,
                roi_options=r_opts,
            )
            return

        self._toolbar.set_file_ext(
            event.file_id,
            event.channel,
            event.roi_id,
            channel_options=channel_options_for_acq_image(acq_image),
            roi_options=roi_options_for_acq_image(acq_image),
        )

    def _on_channel_selection_changed(self, event: ChannelSelectionChanged) -> None:
        """Sync toolbar channel without rebuilding option lists."""
        if self._toolbar is None:
            return
        self._toolbar.set_channel_ext(event.channel)

    def _on_roi_selection_changed(self, event: RoiSelectionChanged) -> None:
        """Sync toolbar ROI without rebuilding option lists."""
        if self._toolbar is None:
            return
        self._toolbar.set_roi_ext(event.roi_id)

    @staticmethod
    def _synthetic_options_for_demo(
        channel: int | None,
        roi_id: int | None,
    ) -> tuple[list[str], list[int]]:
        """Build minimal option lists when no ``AcqImage`` is loaded (demo mode)."""
        ch_opts: list[str] = []
        if channel is not None:
            ch_opts = [str(channel)]
        r_opts: list[int] = []
        if roi_id is not None:
            r_opts = [roi_id]
        return ch_opts, r_opts
