"""CloudScope wrapper for the general-purpose ImageToolbarWidget."""

from __future__ import annotations

from typing import Final, Protocol

from nicegui import ui

from acqstore.acq_image.acq_image import AcqImage
from cloudscope.event_bus import EventBus
from cloudscope.events import (
    AddRoiIntent,
    ApplyRoiFullHeightIntent,
    ApplyRoiFullWidthIntent,
    BeginEditRoiIntent,
    CancelEditRoiIntent,
    DeleteRoiIntent,
    RoiChanged,
    RoiEditModeChanged,
    SelectChannelIntent,
    SelectRoiIntent,
    SubmitEditRoiIntent,
)
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.image_toolbar_widget.image_toolbar_widget import ImageToolbarWidget
_USE_CURRENT_ROI: Final = object()

from nicewidgets.image_toolbar_widget.intent import (
    ImageToolbarIntent,
    ImageToolbarRoiAddRequestIntent,
    ImageToolbarRoiApplyFullHeightIntent,
    ImageToolbarRoiApplyFullWidthIntent,
    ImageToolbarRoiDeleteRequestIntent,
    ImageToolbarRoiEditCancelIntent,
    ImageToolbarRoiEditStartIntent,
    ImageToolbarRoiEditSubmitIntent,
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


class ImageToolbarView(BaseView):
    """CloudScope view wrapper around ``nicewidgets.ImageToolbarWidget``.

    The wrapped widget emits NiceWidgets intent dataclasses. This view converts
    selection and ROI CRUD/edit requests into CloudScope intent events. Model
    mutation is handled by controllers.

    Args:
        event_bus: CloudScope event bus used to publish selection/ROI intents and
            consume selection state events.
    """

    view_id = ViewId.IMAGE_TOOLBAR
    disable_when_busy = True

    def __init__(self, event_bus: EventBus, *, initially_visible: bool = True) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self._toolbar: ImageToolbarWidget | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the image toolbar view.

        Args:
            parent: Optional NiceGUI parent element. If omitted, the widget is
                built in the current slot.

        Returns:
            Root element for this view.
        """
        if parent is None:
            with ui.row().classes("w-full") as self.root:
                self._toolbar = ImageToolbarWidget(on_intent=self._on_toolbar_intent)
        else:
            with parent:
                with ui.row().classes("w-full") as self.root:
                    self._toolbar = ImageToolbarWidget(on_intent=self._on_toolbar_intent)
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to toolbar-specific events while visible.

        BaseView already subscribes to primary selection events.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(RoiChanged, self._on_roi_changed))
        self.add_subscription(self.event_bus.subscribe(RoiEditModeChanged, self._on_roi_edit_mode_changed))

    def _on_toolbar_intent(self, intent: ImageToolbarIntent) -> None:
        """Translate NiceWidgets toolbar intents into CloudScope intents.

        Args:
            intent: NiceWidgets toolbar intent emitted by user interaction.

        Returns:
            None.
        """
        if isinstance(intent, ImageToolbarSelectChannelIntent):
            self.event_bus.publish(SelectChannelIntent(channel=intent.channel))
            return

        if isinstance(intent, ImageToolbarSelectRoiIntent):
            self.event_bus.publish(SelectRoiIntent(roi_id=intent.roi_id))
            return

        if isinstance(intent, ImageToolbarRoiAddRequestIntent):
            self.event_bus.publish(AddRoiIntent(selection=self._selection_snapshot()))
            return

        if isinstance(intent, ImageToolbarRoiDeleteRequestIntent):
            self.event_bus.publish(
                DeleteRoiIntent(selection=self._selection_snapshot(roi_id=intent.roi_id))
            )
            return

        if isinstance(intent, ImageToolbarRoiEditStartIntent):
            self.event_bus.publish(
                BeginEditRoiIntent(selection=self._selection_snapshot(roi_id=intent.roi_id))
            )
            return

        if isinstance(intent, ImageToolbarRoiEditCancelIntent):
            self.event_bus.publish(
                CancelEditRoiIntent(selection=self._selection_snapshot(roi_id=intent.roi_id))
            )
            return

        if isinstance(intent, ImageToolbarRoiEditSubmitIntent):
            self.event_bus.publish(
                SubmitEditRoiIntent(selection=self._selection_snapshot(roi_id=intent.roi_id))
            )
            return

        if isinstance(intent, ImageToolbarRoiApplyFullWidthIntent):
            self.event_bus.publish(
                ApplyRoiFullWidthIntent(selection=self._selection_snapshot(roi_id=intent.roi_id))
            )
            return

        if isinstance(intent, ImageToolbarRoiApplyFullHeightIntent):
            self.event_bus.publish(
                ApplyRoiFullHeightIntent(selection=self._selection_snapshot(roi_id=intent.roi_id))
            )
            return

    def on_primary_selection_changed(self) -> None:
        """Sync toolbar state after BaseView updates the primary selection.

        Returns:
            None.
        """
        self._sync_toolbar_from_selection()

    def refresh_from_state(self) -> None:
        """Refresh toolbar state from cached BaseView selection.

        Returns:
            None.
        """
        self._sync_toolbar_from_selection()

    def _on_roi_changed(self, event: RoiChanged) -> None:
        """Refresh ROI options after ROI model mutation.

        Args:
            event: ROI changed state event.

        Returns:
            None.
        """
        if event.selection.file_id != self.current_selection.file_id:
            return
        self._sync_toolbar_from_selection()

    def _on_roi_edit_mode_changed(self, event: RoiEditModeChanged) -> None:
        """React to ROI edit-mode state changes.

        The current nicewidgets toolbar owns its own visual edit-mode lifecycle
        for user clicks. This handler intentionally does not force private
        widget state; it exists so future programmatic edit-mode synchronization
        has a stable event subscription point.

        Args:
            event: ROI edit-mode state event.

        Returns:
            None.
        """
        if event.selection is not None and event.selection.file_id != self.current_selection.file_id:
            return

    def _selection_snapshot(self, *, roi_id: int | None | object = _USE_CURRENT_ROI) -> PrimarySelection:
        """Return a copied primary selection for intent events.

        Args:
            roi_id: Optional ROI id override. If omitted, the cached selection's
                ROI id is used.

        Returns:
            Copied selection snapshot.
        """
        selected_roi_id = self.current_selection.roi_id if roi_id is _USE_CURRENT_ROI else roi_id
        return PrimarySelection(
            file_id=self.current_selection.file_id,
            channel=self.current_selection.channel,
            roi_id=selected_roi_id,  # type: ignore[arg-type]
        )

    def _sync_toolbar_from_selection(self) -> None:
        """Apply cached selection and AcqImage data to the toolbar widget.

        Returns:
            None.
        """
        if self._toolbar is None:
            return

        file_id = self.current_selection.file_id
        channel = self.current_selection.channel
        roi_id = self.current_selection.roi_id

        if file_id is None:
            self._toolbar.set_file_ext(
                None,
                None,
                None,
                channel_options=[],
                roi_options=[],
            )
            return

        acq_image = self.current_acq_image
        if acq_image is None:
            ch_opts, r_opts = self._synthetic_options_for_demo(channel, roi_id)
            self._toolbar.set_file_ext(
                file_id,
                channel,
                roi_id,
                channel_options=ch_opts,
                roi_options=r_opts,
            )
            return

        roi_options = roi_options_for_acq_image(acq_image)
        if roi_id is not None and roi_id not in roi_options:
            roi_id = roi_options[0] if roi_options else None
        self._toolbar.set_file_ext(
            file_id,
            channel,
            roi_id,
            channel_options=channel_options_for_acq_image(acq_image),
            roi_options=roi_options,
        )

    @staticmethod
    def _synthetic_options_for_demo(
        channel: int | None,
        roi_id: int | None,
    ) -> tuple[list[str], list[int]]:
        """Build minimal option lists when no ``AcqImage`` is loaded.

        Args:
            channel: Current channel selection.
            roi_id: Current ROI selection.

        Returns:
            Channel and ROI option lists compatible with ``ImageToolbarWidget``.
        """
        ch_opts: list[str] = []
        if channel is not None:
            ch_opts = [str(channel)]
        r_opts: list[int] = []
        if roi_id is not None:
            r_opts = [roi_id]
        return ch_opts, r_opts
