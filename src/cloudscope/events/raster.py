"""Raster/plane state events used to centralize 2D slice decoding.

The primary image view is the sole decoder of slice data for the primary image
axis. After a successful decode it publishes :class:`PrimaryPlaneLoaded` so
other views (notably the image toolbar) can seed contrast state without
calling :meth:`BaseFileLoader.get_slice_data` themselves.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cloudscope.events.base import StateEvent


@dataclass(frozen=True)
class PrimaryPlaneLoaded(StateEvent):
    """Published after :class:`PrimaryImageView` finishes loading a 2D plane.

    The plane is shared by reference (no defensive copy) to avoid duplicating
    decode work. Subscribers MUST treat ``plane`` as read-only;
    :class:`PrimaryImageView` calls ``plane.setflags(write=False)`` before
    publishing so accidental in-place mutation raises.

    Args:
        file_id: Stable file identifier the plane belongs to.
        channel: Zero-based channel index decoded.
        plane: 2D ``(Y, X)`` ndarray. Read-only.
    """

    file_id: str
    channel: int
    plane: np.ndarray
