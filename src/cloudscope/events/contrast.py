"""Contrast intents and state events.

`UpdateImageContrastIntent` is published by views when the user changes any
contrast control. The widget computes Auto locally and emits the resulting
state, so the controller never needs an explicit Auto branch and never decodes
slice data.

`ImageContrastChanged` is published by :class:`ContrastController` after the
AcqImage's per-channel ``ImageContrast`` is mutated.
"""

from __future__ import annotations

from dataclasses import dataclass

from acqstore.acq_image.image_contrast import ImageContrast

from cloudscope.events.base import IntentEvent, StateEvent


@dataclass(frozen=True)
class UpdateImageContrastIntent(IntentEvent):
    """User requested a contrast update for ``(file_id, channel)``.

    Args:
        file_id: Stable file identifier.
        channel: Zero-based channel index.
        color_lut: Selected LUT identifier.
        value_min: Minimum intensity displayed.
        value_max: Maximum intensity displayed.
    """

    file_id: str
    channel: int
    color_lut: str
    value_min: int
    value_max: int


@dataclass(frozen=True)
class ImageContrastChanged(StateEvent):
    """Per-channel contrast was mutated on the named AcqImage.

    Args:
        file_id: Stable file identifier.
        channel: Zero-based channel index.
        contrast: Snapshot of the new :class:`ImageContrast`.
    """

    file_id: str
    channel: int
    contrast: ImageContrast
