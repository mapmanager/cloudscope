"""CloudScope wrapper for the general-purpose ImageToolbarWidget."""

from __future__ import annotations

from typing import Final, Protocol

import numpy as np
from nicegui import ui

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.image_contrast import contrast_clip_min_max
from cloudscope.app_config import AppConfig
from cloudscope.contrast_seeding import (
    contrast_auto_percentiles,
    default_channel_color_lut,
    ephemeral_auto_contrast_from_plane,
)
from cloudscope.event_bus import EventBus
from cloudscope.events.contrast import ImageContrastChanged, UpdateImageContrastIntent
from cloudscope.events.raster import PrimaryPlaneLoaded
from cloudscope.events.roi import (
    AddRoiIntent,
    ApplyRoiFullHeightIntent,
    ApplyRoiFullWidthIntent,
    BeginEditRoiIntent,
    CancelEditRoiIntent,
    DeleteRoiIntent,
    RoiChanged,
    RoiEditModeChanged,
    SubmitEditRoiIntent,
)
from cloudscope.events.selection import SelectChannelIntent, SelectRoiIntent
from cloudscope.state import PrimarySelection
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.contrast_widget.contrast_widget import ContrastWidget
from nicewidgets.contrast_widget.intent import ContrastChangedIntent
from nicewidgets.image_toolbar_widget.image_toolbar_widget import ImageToolbarWidget
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

logger = get_logger(__name__)

_USE_CURRENT_ROI: Final = object()


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

    def __init__(
        self,
        event_bus: EventBus,
        *,
        initially_visible: bool = True,
        app_config: AppConfig | None = None,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=initially_visible)
        self._toolbar: ImageToolbarWidget | None = None
        self._contrast: ContrastWidget | None = None
        self._app_config = app_config
        self._last_selection_key: tuple[str | None, int | None] = (None, None)

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the image toolbar view.

        The toolbar and contrast widgets do not own layout containers; this
        view wraps them in one ``ui.row`` so all controls share a single
        horizontal line and wrap together when the container narrows.

        Args:
            parent: Optional NiceGUI parent element. If omitted, the widget is
                built in the current slot.

        Returns:
            Root element for this view.
        """
        if parent is None:
            with ui.row().classes("w-full items-center flex-wrap gap-1 py-0 px-1") as self.root:
                self._build_children()
        else:
            with parent:
                with ui.row().classes("w-full items-center flex-wrap gap-1 py-0 px-1") as self.root:
                    self._build_children()
        self.after_build()
        return self.root

    def _build_children(self) -> None:
        """Build the image toolbar and contrast widget on the same row."""
        self._toolbar = ImageToolbarWidget(on_intent=self._on_toolbar_intent)
        with ui.element('div').classes('ml-auto'):
            self._contrast = ContrastWidget(
                on_intent=self._on_contrast_intent,
                auto_contrast_callback=self._compute_auto_contrast,
            )
        # Wait for a real plane before enabling the contrast controls.
        self._contrast.set_enabled_ext(False)

    def subscribe_events(self) -> None:
        """Subscribe to toolbar-specific events while visible.

        BaseView already subscribes to primary selection events.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(RoiChanged, self._on_roi_changed))
        self.add_subscription(self.event_bus.subscribe(RoiEditModeChanged, self._on_roi_edit_mode_changed))
        self.add_subscription(self.event_bus.subscribe(PrimaryPlaneLoaded, self._on_plane_loaded))
        self.add_subscription(
            self.event_bus.subscribe(ImageContrastChanged, self._on_image_contrast_changed)
        )

    def _compute_auto_contrast(self, plane: np.ndarray) -> tuple[int, int]:
        """Compute auto contrast for ``plane`` using AppConfig percentiles.

        Args:
            plane: 2D ndarray supplied by the contrast widget.

        Returns:
            ``(value_min, value_max)`` integer pair for the slider.
        """
        if self._app_config is None:
            low, high = 1.0, 99.5
        else:
            low, high = contrast_auto_percentiles(self._app_config)
        return contrast_clip_min_max(
            plane, percentile_low=low, percentile_high=high
        )

    def _on_contrast_intent(self, intent: ContrastChangedIntent) -> None:
        """Translate widget intents into ``UpdateImageContrastIntent``.

        Args:
            intent: Widget intent carrying the full new state.

        Returns:
            None.
        """
        file_id = self.current_selection.file_id
        channel = self.current_selection.channel
        if file_id is None or channel is None:
            return
        self.event_bus.publish(
            UpdateImageContrastIntent(
                file_id=str(file_id),
                channel=int(channel),
                color_lut=intent.color_lut,
                value_min=intent.value_min,
                value_max=intent.value_max,
                from_auto=intent.from_auto,
            )
        )

    def _on_plane_loaded(self, event: PrimaryPlaneLoaded) -> None:
        """Seed the contrast widget from a freshly decoded plane.

        Ignores planes that do not match the current selection (a later plane
        load will be processed when it arrives).

        Args:
            event: Plane state event.

        Returns:
            None.
        """
        selection = self.current_selection
        if event.file_id != selection.file_id or selection.channel != int(event.channel):
            return
        if self._contrast is None:
            return
        self._contrast.set_image_ext(event.plane)
        if event.use_auto_contrast:
            value_min, value_max = ephemeral_auto_contrast_from_plane(
                event.plane,
                self._app_config,
            )
            color_lut = default_channel_color_lut(self._app_config, int(event.channel))
            self._contrast.set_lut_ext(color_lut)
            self._contrast.set_range_ext(value_min=value_min, value_max=value_max)
        self._contrast.set_enabled_ext(True)

    def _on_image_contrast_changed(self, event: ImageContrastChanged) -> None:
        """Keep the widget consistent with controller-published state.

        Args:
            event: Contrast state event.

        Returns:
            None.
        """
        if self._contrast is None:
            return
        selection = self.current_selection
        if event.file_id != selection.file_id or selection.channel != int(event.channel):
            return
        self._contrast.set_lut_ext(event.contrast.color_lut)
        self._contrast.set_range_ext(
            value_min=event.contrast.value_min, value_max=event.contrast.value_max
        )

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

        On every ``(file_id, channel)`` transition the contrast widget is
        disabled so the user cannot drag against stale bounds; the next
        ``PrimaryPlaneLoaded`` event re-enables it.

        Returns:
            None.
        """
        new_key = (self.current_selection.file_id, self.current_selection.channel)
        if new_key != self._last_selection_key:
            self._last_selection_key = new_key
            if self._contrast is not None:
                self._contrast.set_enabled_ext(False)
                if new_key == (None, None):
                    self._contrast.set_image_ext(None)
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
