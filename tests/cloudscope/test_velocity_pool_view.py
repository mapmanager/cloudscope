"""Headless tests for VelocityPoolView callbacks."""

from __future__ import annotations

from cloudscope.event_bus import EventBus
from cloudscope.events.selection import SelectFileIntent
from cloudscope.views.velocity_pool_view import VelocityPoolView


def test_velocity_pool_view_row_selection_publishes_select_file_intent() -> None:
    """Selecting a pool row should request the matching file/channel/ROI."""
    bus = EventBus()
    intents: list[SelectFileIntent] = []
    bus.subscribe(SelectFileIntent, intents.append)
    view = VelocityPoolView(event_bus=bus, app_state=None)

    view._on_row_selected(
        "row-a",
        {"path": "file-a", "channel": 2, "roi_id": 5},
    )

    assert intents == [SelectFileIntent(file_id="file-a", channel=2, roi_id=5)]
