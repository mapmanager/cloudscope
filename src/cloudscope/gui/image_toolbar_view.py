"""CloudScope wrapper for the general-purpose ImageToolbarWidget."""

from __future__ import annotations

from typing import Protocol

from nicegui import ui

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.acq_image_list import AcqImageList
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import PrimarySelectionChanged, SelectChannelIntent, SelectRoiIntent
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
            consume primary-selection state events.
        acq_image_list: Backend file list used to derive channel and ROI options
            for the selected file.
    """

    def __init__(
        self,
        event_bus: EventBus,
        acq_image_list: AcqImageList,
    ) -> None:
        self._event_bus = event_bus
        self._acq_image_list = acq_image_list
        self._toolbar: ImageToolbarWidget | None = None

        self._event_bus.subscribe(PrimarySelectionChanged, self._on_selection_changed)

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

    def set_data(self, acq_image_list: AcqImageList) -> None:
        """Replace the backend file list used by the toolbar.

        Args:
            acq_image_list: New backend file list.

        Returns:
            None.
        """
        self._acq_image_list = acq_image_list

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

    def _on_selection_changed(self, event: PrimarySelectionChanged) -> None:
        """Update toolbar state from CloudScope primary-selection state.

        Args:
            event: Current primary selection.

        Returns:
            None.
        """
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

        acq_image = self._acq_image_list.get_file_by_id(event.file_id)
        if acq_image is None:
            self._toolbar.set_file_ext(
                None,
                None,
                None,
                channel_options=[],
                roi_options=[],
            )
            return

        self._toolbar.set_file_ext(
            event.file_id,
            event.channel,
            event.roi_id,
            channel_options=channel_options_for_acq_image(acq_image),
            roi_options=roi_options_for_acq_image(acq_image),
        )
