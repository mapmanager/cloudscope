"""
Event bus for CloudScope.
"""

from collections import defaultdict
from collections.abc import Callable


class EventBus:
    """Simple typed event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[type, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Callable) -> None:
        """Subscribe to an event type."""
        self._subscribers[event_type].append(handler)

    def publish(self, event: object) -> None:
        """Publish an event."""
        for cls in type(event).__mro__:
            if cls is object:
                break
            for handler in self._subscribers.get(cls, []):
                handler(event)