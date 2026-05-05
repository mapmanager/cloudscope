"""Typed event bus for CloudScope."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class EventSubscription:
    """Handle for one event-bus subscription.

    Args:
        event_bus: Event bus that owns the subscription.
        event_type: Event type the handler is subscribed to.
        handler: Callable invoked when matching events are published.
    """

    event_bus: EventBus
    event_type: type
    handler: Callable[[Any], None]

    def unsubscribe(self) -> None:
        """Remove this subscription from its event bus.

        Returns:
            None.
        """
        self.event_bus.unsubscribe(self.event_type, self.handler)


class EventBus:
    """Simple typed event bus with unsubscribe support."""

    def __init__(self) -> None:
        """Initialize an empty event bus."""
        self._subscribers: dict[type, list[Callable[[Any], None]]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable[[Any], None]) -> EventSubscription:
        """Subscribe to an event type.

        Args:
            event_type: Event class to subscribe to.
            handler: Callable invoked with matching events.

        Returns:
            Subscription handle that can be used to unsubscribe.
        """
        self._subscribers[event_type].append(handler)
        return EventSubscription(self, event_type, handler)

    def unsubscribe(self, event_type: type, handler: Callable[[Any], None]) -> None:
        """Remove one event subscription if present.

        Args:
            event_type: Event class previously subscribed to.
            handler: Handler previously registered for ``event_type``.

        Returns:
            None.
        """
        handlers = self._subscribers.get(event_type)
        if not handlers:
            return
        try:
            handlers.remove(handler)
        except ValueError:
            return
        if not handlers:
            self._subscribers.pop(event_type, None)

    def publish(self, event: object) -> None:
        """Publish an event to handlers for its class and base classes.

        Args:
            event: Event object to publish.

        Returns:
            None.
        """
        for cls in type(event).__mro__:
            if cls is object:
                break
            for handler in tuple(self._subscribers.get(cls, ())):
                handler(event)
