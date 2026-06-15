"""Velocity-analysis pool model-change events.

The velocity pool is an ``acqstore`` DataFrame cache owned by ``AcqImageList``.
CloudScope controllers update that backend object and publish these events so
views can refresh without knowing which low-level action caused the mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cloudscope.events.base import StateEvent


class VelocityPoolChangeKind(StrEnum):
    """Supported velocity-pool mutation kinds."""

    REFRESH_ROW = "refresh_row"
    REMOVE_ROW = "remove_row"
    REMOVE_ROI = "remove_roi"
    REBUILD = "rebuild"


@dataclass(frozen=True)
class VelocityPoolChanged(StateEvent):
    """Emitted after the backend velocity pool has changed.

    Args:
        change_kind: Mutation applied to the pool.
        file_id: File identifier for row/ROI mutations, or None for rebuilds.
        channel: Channel index for row mutations, or None when not applicable.
        roi_id: ROI identifier for row/ROI mutations, or None when not applicable.
    """

    change_kind: VelocityPoolChangeKind
    file_id: str | None = None
    channel: int | None = None
    roi_id: int | None = None
