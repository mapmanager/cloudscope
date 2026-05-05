"""Tests for CloudScope event bus subscription lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from cloudscope.event_bus import EventBus


@dataclass(frozen=True)
class BaseEvent:
    """Base test event."""


@dataclass(frozen=True)
class ChildEvent(BaseEvent):
    """Child test event."""


def test_subscribe_publish_and_unsubscribe() -> None:
    """Unsubscribed handlers should not receive later events."""
    bus = EventBus()
    seen: list[object] = []
    subscription = bus.subscribe(ChildEvent, seen.append)

    bus.publish(ChildEvent())
    subscription.unsubscribe()
    bus.publish(ChildEvent())

    assert len(seen) == 1


def test_publish_dispatches_to_base_event_subscribers() -> None:
    """Subscribers to base event classes should receive child events."""
    bus = EventBus()
    seen: list[object] = []
    bus.subscribe(BaseEvent, seen.append)

    event = ChildEvent()
    bus.publish(event)

    assert seen == [event]


def test_unsubscribe_is_idempotent() -> None:
    """Unsubscribing missing handlers should be safe."""
    bus = EventBus()

    def handler(_event: object) -> None:
        pass

    bus.unsubscribe(ChildEvent, handler)
    subscription = bus.subscribe(ChildEvent, handler)
    subscription.unsubscribe()
    subscription.unsubscribe()
