"""Controller for per-channel image contrast updates.

Translates :class:`UpdateImageContrastIntent` into a mutation on the named
:class:`AcqImage` and publishes :class:`ImageContrastChanged`. The controller
is deliberately dumb: it never decodes slice data, never computes Auto, and has
no :class:`AppConfig` dependency. Auto contrast is computed inside
:class:`ContrastWidget` before the intent is published, so the intent always
carries the full final state.
"""

from __future__ import annotations

from acqstore.acq_image.image_contrast import ImageContrast

from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.event_bus import EventBus
from cloudscope.events.contrast import ImageContrastChanged, UpdateImageContrastIntent
from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)


class ContrastController:
    """Handle contrast intent events and publish contrast state events.

    Args:
        event_bus: Page-scoped event bus.
        home_controller: Controller owning the current :class:`AcqImageList`.
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        home_controller: HomePageController,
    ) -> None:
        self._event_bus = event_bus
        self._home_controller = home_controller

    def bind(self) -> None:
        """Subscribe to contrast intent events.

        Returns:
            None.
        """
        self._event_bus.subscribe(UpdateImageContrastIntent, self._on_update_intent)

    def _on_update_intent(self, intent: UpdateImageContrastIntent) -> None:
        """Apply a user contrast change and publish the resulting state event.

        Args:
            intent: Update request carrying the full new contrast state.

        Returns:
            None.
        """
        acq_image_list = self._home_controller.state.acq_image_list
        if acq_image_list is None:
            logger.warning(
                'Ignoring UpdateImageContrastIntent: no AcqImageList loaded (file_id=%r channel=%r)',
                intent.file_id,
                intent.channel,
            )
            return

        acq_image = acq_image_list.get_file_by_id(intent.file_id)
        if acq_image is None:
            logger.warning(
                'Ignoring UpdateImageContrastIntent for unknown file_id=%r channel=%r',
                intent.file_id,
                intent.channel,
            )
            return

        existing = acq_image.get_image_contrast(int(intent.channel))
        if existing is None:
            # No plane has been loaded yet; the next PrimaryPlaneLoaded event
            # will seed defaults. Drop this stale intent rather than guess
            # img_min/img_max from incomplete data.
            logger.warning(
                'Ignoring UpdateImageContrastIntent for file_id=%r channel=%r: no contrast seeded yet',
                intent.file_id,
                intent.channel,
            )
            return

        new_contrast = ImageContrast(
            color_lut=str(intent.color_lut),
            value_min=int(intent.value_min),
            value_max=int(intent.value_max),
            img_min=int(existing.img_min),
            img_max=int(existing.img_max),
        )
        acq_image.set_image_contrast(int(intent.channel), new_contrast)
        self._event_bus.publish(
            ImageContrastChanged(
                file_id=str(intent.file_id),
                channel=int(intent.channel),
                contrast=new_contrast,
            )
        )
