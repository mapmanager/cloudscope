"""
Base event classes shared by every CloudScope event family.

Events are split into:
- Intent events (user or system requests)
- State events (facts after mutation)
"""

from __future__ import annotations


class Event:
    """Base event."""


class IntentEvent(Event):
    """Base class for intent events."""


class StateEvent(Event):
    """Base class for state events."""
