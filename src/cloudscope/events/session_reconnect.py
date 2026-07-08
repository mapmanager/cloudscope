"""Reconnect hydrate event published after a hard client rebuild."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cloudscope.events.base import StateEvent

if TYPE_CHECKING:
    from acqstore.acq_image.acq_image import AcqImage


@dataclass(frozen=True)
class HomePageSessionReconnectRestore(StateEvent):
    """One-shot hydrate after hard reconnect when widgets are rebuilt.

    Published once per reconnect after ``HomePage.build(reconnect=True)``.
    Not used for normal user selection changes.

    Args:
        file_id: Selected file identifier, or ``None`` if nothing is selected.
        acq_image: Resolved ``AcqImage`` when a list is loaded, else ``None``.
        channel: Current channel for ``file_id``.
        roi_id: Current ROI for ``file_id``.
        analysis_name: Optional analysis identity when an analysis tree row
            was selected. See :class:`cloudscope.state.PrimarySelection`.
        primary_x_range: Authoritative shared x-range from ``HomePageState``.
        view_session: Per-view session blobs keyed by ``ViewId`` string values.
    """

    file_id: str | None
    acq_image: AcqImage | None
    channel: int | None
    roi_id: int | None
    analysis_name: str | None
    primary_x_range: tuple[float | None, float | None]
    view_session: dict[str, dict[str, Any]]
