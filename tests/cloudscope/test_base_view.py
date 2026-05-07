"""Tests for ``BaseView`` lifecycle behavior."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.event_bus import EventBus
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId


@dataclass(frozen=True)
class TestEvent:
    """Test event."""


class FakeRoot:
    """Small stand-in for a NiceGUI element."""

    def __init__(self) -> None:
        self.visible = True
        self.update_count = 0

    def update(self) -> None:
        """Record update calls."""
        self.update_count += 1


class FakeView(BaseView):
    """Fake view that subscribes while visible."""

    view_id = ViewId.METADATA

    def __init__(self, event_bus: EventBus, *, initially_visible: bool = True) -> None:
        super().__init__(event_bus=event_bus, initially_visible=initially_visible)
        self.events: list[TestEvent] = []
        self.refresh_count = 0

    def build(self, parent=None):
        """Build fake root."""
        self.root = FakeRoot()  # type: ignore[assignment]
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to test events."""
        self.add_subscription(self.event_bus.subscribe(TestEvent, self.events.append))

    def refresh_from_state(self) -> None:
        """Record refresh calls."""
        self.refresh_count += 1


def test_visible_view_subscribes_after_build() -> None:
    """Initially visible views should subscribe and refresh after build."""
    bus = EventBus()
    view = FakeView(bus)

    view.build()
    bus.publish(TestEvent())

    assert len(view.events) == 1
    assert view.refresh_count == 1


def test_hidden_view_does_not_consume_events_until_shown() -> None:
    """Initially hidden views should not consume events until shown."""
    bus = EventBus()
    view = FakeView(bus, initially_visible=False)

    view.build()
    bus.publish(TestEvent())
    view.show()
    bus.publish(TestEvent())

    assert len(view.events) == 1
    assert view.refresh_count == 1


def test_hide_unsubscribes_from_events() -> None:
    """Hiding a view should unsubscribe its event handlers."""
    bus = EventBus()
    view = FakeView(bus)

    view.build()
    view.hide()
    bus.publish(TestEvent())

    assert view.events == []
    assert view.root is not None
    assert view.root.visible is False

from cloudscope.events import ChannelSelectionChanged, FileSelectionChanged, RoiSelectionChanged


def test_base_view_tracks_primary_selection_for_all_views() -> None:
    """BaseView should cache file/channel/ROI selection while visible."""
    bus = EventBus()
    view = FakeView(bus)
    view.build()

    bus.publish(FileSelectionChanged(file_id="/tmp/a.oir", acq_image="image", channel=0, roi_id=1))
    bus.publish(ChannelSelectionChanged(channel=2))
    bus.publish(RoiSelectionChanged(roi_id=3))

    assert view.current_selection.file_id == "/tmp/a.oir"
    assert view.current_selection.channel == 2
    assert view.current_selection.roi_id == 3
    assert view.current_acq_image == "image"
