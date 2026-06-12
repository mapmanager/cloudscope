"""Integration tests for SmartExpansion + BaseView MVC lifecycle wiring."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.event_bus import EventBus
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.smart_expansion_widget.smart_expansion import SmartExpansion


@dataclass(frozen=True)
class _TestEvent:
    """Test event."""


class _FakeRoot:
    """Small stand-in for a NiceGUI element."""

    def __init__(self) -> None:
        self.visible = True
        self.update_count = 0

    def update(self) -> None:
        """Record update calls."""
        self.update_count += 1


class _FakeView(BaseView):
    """Fake BaseView that tracks subscriptions and refreshes."""

    view_id = ViewId.FILE_LIST

    def __init__(self, event_bus: EventBus, *, initially_visible: bool = False) -> None:
        super().__init__(event_bus=event_bus, initially_visible=initially_visible)
        self.events: list[_TestEvent] = []
        self.refresh_count = 0

    def build(self, parent=None):
        """Build fake root."""
        self.root = _FakeRoot()  # type: ignore[assignment]
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to test events."""
        self.add_subscription(self.event_bus.subscribe(_TestEvent, self.events.append))

    def refresh_from_state(self) -> None:
        """Record refresh calls."""
        self.refresh_count += 1


def _wire_expansion(view: _FakeView, *, initially_open: bool = True) -> SmartExpansion:
    """Return a SmartExpansion wired like the Home page composer."""
    expansion = SmartExpansion(
        'Panel',
        initially_open=initially_open,
        on_open=view.show,
        on_close=view.hide,
    )
    with expansion:
        view.build()
    expansion.apply_initial_state()
    return expansion


def test_open_expansion_connects_view_to_events() -> None:
    """An open SmartExpansion should let its BaseView consume events."""
    bus = EventBus()
    view = _FakeView(bus, initially_visible=False)
    _wire_expansion(view, initially_open=True)

    bus.publish(_TestEvent())

    assert len(view.events) == 1
    assert view.refresh_count == 1
    assert view.is_visible is True


def test_closed_expansion_disconnects_view_from_events() -> None:
    """A collapsed SmartExpansion should unsubscribe its BaseView."""
    bus = EventBus()
    view = _FakeView(bus, initially_visible=False)
    expansion = _wire_expansion(view, initially_open=True)

    expansion.close()
    bus.publish(_TestEvent())

    assert view.events == []
    assert view.is_visible is False


def test_reopen_expansion_refreshes_from_state() -> None:
    """Reopening a SmartExpansion should refresh the wrapped BaseView."""
    bus = EventBus()
    view = _FakeView(bus, initially_visible=False)
    expansion = _wire_expansion(view, initially_open=True)

    expansion.close()
    expansion.open()
    bus.publish(_TestEvent())

    assert view.refresh_count == 2
    assert len(view.events) == 1


def test_initially_closed_expansion_stays_disconnected_until_opened() -> None:
    """Closed startup expansions should not consume events until opened."""
    bus = EventBus()
    view = _FakeView(bus, initially_visible=False)
    expansion = _wire_expansion(view, initially_open=False)

    bus.publish(_TestEvent())
    assert view.events == []
    assert view.refresh_count == 0

    expansion.open()
    bus.publish(_TestEvent())

    assert len(view.events) == 1
    assert view.refresh_count == 1
