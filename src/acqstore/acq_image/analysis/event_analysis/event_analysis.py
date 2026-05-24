"""Event analysis for AcqImage channel/ROI selections.

This module provides a lightweight event store for user- or algorithm-defined
x-axis intervals. Unlike velocity and diameter analyses, event analysis is not a
primary kymograph analysis; it may coexist with any primary analysis for the
same ``(channel, roi_id)`` selection.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from acqstore.acq_image.analysis.data_provider import AnalysisDataProvider
from acqstore.acq_image.analysis.model import AnalysisResult, AnalysisRunContext, BaseAnalysis
from acqstore.acq_image.analysis.registry import register_analysis_class


class EventType(StrEnum):
    """Supported acquisition-image event categories."""

    USER = "user"
    RISE = "rise"
    FALL = "fall"
    TRANSIENT = "transient"


@dataclass(frozen=True, slots=True)
class AcqImageEvent:
    """One x-axis interval event for an acquisition image analysis selection.

    Args:
        id: Stable integer event identifier within one event store.
        x0: First x-coordinate in analysis plot coordinates.
        x1: Second x-coordinate in analysis plot coordinates.
        event_type: Semantic event category.
    """

    id: int
    x0: float
    x1: float
    event_type: EventType = EventType.USER

    def __post_init__(self) -> None:
        """Validate event fields.

        Raises:
            ValueError: If ``id`` is not positive or x coordinates are equal.
        """
        if int(self.id) < 1:
            raise ValueError(f"event id must be >= 1, got {self.id!r}")
        if float(self.x0) == float(self.x1):
            raise ValueError("event x0 and x1 must differ")

    @property
    def x_min(self) -> float:
        """Return the smaller x coordinate."""
        return min(float(self.x0), float(self.x1))

    @property
    def x_max(self) -> float:
        """Return the larger x coordinate."""
        return max(float(self.x0), float(self.x1))

    @property
    def duration(self) -> float:
        """Return the interval duration in x-axis units."""
        return abs(float(self.x1) - float(self.x0))

    def to_json_dict(self) -> dict[str, object]:
        """Return a JSON-serializable event record.

        Returns:
            Dictionary with ``id``, ``x0``, ``x1``, ``event_type``, and
            ``duration``.
        """
        return {
            "id": int(self.id),
            "x0": float(self.x0),
            "x1": float(self.x1),
            "event_type": self.event_type.value,
            "duration": self.duration,
        }

    @classmethod
    def from_json_dict(cls, record: dict[str, Any]) -> "AcqImageEvent":
        """Create an event from a JSON-like mapping.

        Args:
            record: Event record from analysis summary JSON.

        Returns:
            Parsed event.

        Raises:
            KeyError: If required fields are missing.
            ValueError: If values are invalid.
        """
        return cls(
            id=int(record["id"]),
            x0=float(record["x0"]),
            x1=float(record["x1"]),
            event_type=EventType(str(record.get("event_type", EventType.USER.value))),
        )


class AcqImageEventStore:
    """Backend store for ``AcqImageEvent`` records.

    This class intentionally has no GUI concepts such as selection, visibility,
    or style. The next id is derived from current contents rather than persisted
    as separate state.
    """

    def __init__(self, events: list[AcqImageEvent] | None = None) -> None:
        """Initialize the store.

        Args:
            events: Optional initial events.
        """
        self._events: dict[int, AcqImageEvent] = {}
        if events:
            self.add_rects(events)

    def __len__(self) -> int:
        """Return the number of stored events."""
        return len(self._events)

    def _next_id(self) -> int:
        """Return the next integer id.

        Returns:
            One greater than the current max id, or 1 for an empty store.
        """
        if not self._events:
            return 1
        return max(self._events) + 1

    def add_rect(
        self,
        x0: float,
        x1: float,
        *,
        event_type: EventType = EventType.USER,
        event_id: int | None = None,
    ) -> AcqImageEvent:
        """Add one x-interval event.

        Args:
            x0: First x-coordinate.
            x1: Second x-coordinate.
            event_type: Event category.
            event_id: Optional caller-supplied id. When omitted, the store uses
                the next integer id.

        Returns:
            Created event.

        Raises:
            ValueError: If the id already exists or coordinates are invalid.
        """
        new_id = self._next_id() if event_id is None else int(event_id)
        if new_id in self._events:
            raise ValueError(f"event id already exists: {new_id}")
        event = AcqImageEvent(id=new_id, x0=float(x0), x1=float(x1), event_type=event_type)
        self._events[event.id] = event
        return event

    def add_rects(self, events: list[AcqImageEvent]) -> list[AcqImageEvent]:
        """Add multiple events.

        Args:
            events: Events to add. Ids must be unique.

        Returns:
            Added events in input order.
        """
        added: list[AcqImageEvent] = []
        for event in events:
            if event.id in self._events:
                raise ValueError(f"event id already exists: {event.id}")
            self._events[int(event.id)] = event
            added.append(event)
        return added

    def delete_rect(self, rect_id: int) -> None:
        """Delete one event by id.

        Args:
            rect_id: Event id to delete.

        Raises:
            KeyError: If the id is not present.
        """
        try:
            del self._events[int(rect_id)]
        except KeyError:
            raise KeyError(f"event id not found: {rect_id}") from None

    def update_rect(
        self,
        rect_id: int,
        *,
        x0: float | None = None,
        x1: float | None = None,
        event_type: EventType | None = None,
    ) -> AcqImageEvent:
        """Update one event.

        Args:
            rect_id: Event id to update.
            x0: Replacement first coordinate, or None to keep current.
            x1: Replacement second coordinate, or None to keep current.
            event_type: Replacement category, or None to keep current.

        Returns:
            Updated event.

        Raises:
            KeyError: If the id is not present.
        """
        rid = int(rect_id)
        event = self.get_required(rid)
        updated = AcqImageEvent(
            id=event.id,
            x0=event.x0 if x0 is None else float(x0),
            x1=event.x1 if x1 is None else float(x1),
            event_type=event.event_type if event_type is None else event_type,
        )
        self._events[rid] = updated
        return updated

    def get_rects(self) -> list[AcqImageEvent]:
        """Return events sorted by id.

        Returns:
            List of events.
        """
        return [self._events[key] for key in sorted(self._events)]

    def get_required(self, rect_id: int) -> AcqImageEvent:
        """Return one event or raise.

        Args:
            rect_id: Event id.

        Returns:
            Matching event.

        Raises:
            KeyError: If the id is not present.
        """
        rid = int(rect_id)
        try:
            return self._events[rid]
        except KeyError:
            raise KeyError(f"event id not found: {rect_id}") from None

    def to_summary_dict(self) -> dict[str, object]:
        """Return structured summary JSON for analysis persistence.

        Returns:
            Summary dictionary with version and event records.
        """
        return {
            "version": 1,
            "events": [event.to_json_dict() for event in self.get_rects()],
        }

    @classmethod
    def from_summary_dict(cls, summary: dict[str, Any]) -> "AcqImageEventStore":
        """Create a store from analysis summary JSON.

        Args:
            summary: Structured summary from ``AnalysisResult.summary``.

        Returns:
            Hydrated event store.
        """
        records = summary.get("events", [])
        events = [AcqImageEvent.from_json_dict(dict(record)) for record in records]
        return cls(events)


@register_analysis_class
class EventAnalysis(BaseAnalysis):
    """Non-primary event interval analysis for one channel/ROI."""

    analysis_name = "event"
    exclusive_group = None
    depends_on = ()

    def __init__(
        self,
        *,
        channel: int,
        roi_id: int,
        detection_params: dict[str, object] | None = None,
    ) -> None:
        """Create an event analysis.

        Args:
            channel: Channel index.
            roi_id: ROI identifier.
            detection_params: Optional detection parameters. Event analysis does
                not currently use detection parameters.
        """
        super().__init__(channel=channel, roi_id=roi_id, detection_params=detection_params)
        self.events = AcqImageEventStore()
        self._sync_summary()

    def run(
        self,
        data_provider: AnalysisDataProvider,
        *,
        context: AnalysisRunContext | None = None,
        dependencies: dict[str, BaseAnalysis] | None = None,
    ) -> AnalysisResult:
        """Return current event results without running an algorithm.

        Args:
            data_provider: Unused analysis data provider.
            context: Optional run context.
            dependencies: Unused dependency mapping.

        Returns:
            Current analysis result.
        """
        _ = data_provider, context, dependencies
        self._sync_summary()
        return self.result

    def add_rect(
        self,
        x0: float,
        x1: float,
        *,
        event_type: EventType = EventType.USER,
        event_id: int | None = None,
    ) -> AcqImageEvent:
        """Add one event and mark analysis dirty.

        Args:
            x0: First x-coordinate.
            x1: Second x-coordinate.
            event_type: Event category.
            event_id: Optional caller-supplied id.

        Returns:
            Created event.
        """
        event = self.events.add_rect(x0, x1, event_type=event_type, event_id=event_id)
        self._sync_summary()
        self.set_dirty()
        return event

    def add_rects(self, events: list[AcqImageEvent]) -> list[AcqImageEvent]:
        """Add multiple events and mark analysis dirty.

        Args:
            events: Events to add.

        Returns:
            Added events.
        """
        added = self.events.add_rects(events)
        self._sync_summary()
        self.set_dirty()
        return added

    def delete_rect(self, rect_id: int) -> None:
        """Delete one event and mark analysis dirty.

        Args:
            rect_id: Event id to delete.
        """
        self.events.delete_rect(rect_id)
        self._sync_summary()
        self.set_dirty()

    def update_rect(
        self,
        rect_id: int,
        *,
        x0: float | None = None,
        x1: float | None = None,
        event_type: EventType | None = None,
    ) -> AcqImageEvent:
        """Update one event and mark analysis dirty.

        Args:
            rect_id: Event id.
            x0: Optional replacement x0.
            x1: Optional replacement x1.
            event_type: Optional replacement category.

        Returns:
            Updated event.
        """
        event = self.events.update_rect(rect_id, x0=x0, x1=x1, event_type=event_type)
        self._sync_summary()
        self.set_dirty()
        return event

    def get_rects(self) -> list[AcqImageEvent]:
        """Return current events.

        Returns:
            List of events sorted by id.
        """
        return self.events.get_rects()

    def load_json_dict(self, record: dict[str, Any]) -> None:
        """Load event analysis state from a JSON analysis record.

        Args:
            record: Analysis sidecar record.
        """
        super().load_json_dict(record)
        self.events = AcqImageEventStore.from_summary_dict(self.result.summary)
        self._sync_summary()
        self.set_clean()

    def _sync_summary(self) -> None:
        """Synchronize ``AnalysisResult.summary`` with the event store."""
        self.result.summary = self.events.to_summary_dict()
