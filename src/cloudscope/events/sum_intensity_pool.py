"""Sum-intensity pool model-change events.

The sum-intensity pool is an ``acqstore`` DataFrame cache owned by
``AcqImageList``. CloudScope controllers update that backend object and publish
these events so views can refresh without knowing which low-level action caused
the mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from cloudscope.events.base import StateEvent


class SumIntensityPoolChangeKind(StrEnum):
    """Supported sum-intensity-pool mutation kinds."""

    REFRESH_ROWS = "refresh_rows"
    REMOVE_ROWS = "remove_rows"
    REMOVE_ROI = "remove_roi"
    REFRESH_FILE = "refresh_file"
    REBUILD = "rebuild"


@dataclass(frozen=True)
class SumIntensityPoolChanged(StateEvent):
    """Emitted after the backend sum-intensity pool has changed.

    Args:
        change_kind: Mutation applied to the pool.
        file_id: File identifier for row/file/ROI mutations, or None for rebuilds.
        channel: Channel index for row mutations, or None when not applicable.
        roi_id: ROI identifier for row/ROI mutations, or None when not applicable.
    """

    change_kind: SumIntensityPoolChangeKind
    file_id: str | None = None
    channel: int | None = None
    roi_id: int | None = None
