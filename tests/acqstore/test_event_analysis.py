"""Tests for AcqStore event analysis."""

from __future__ import annotations

import pytest

from acqstore.acq_image.acq_analysis_set import AcqAnalysisSet
from acqstore.acq_image.analysis.event_analysis.event_analysis import (
    AcqImageEvent,
    AcqImageEventStore,
    EventAnalysis,
    EventType,
)
from acqstore.acq_image.analysis.model import AnalysisKey


def test_event_store_add_update_delete_and_summary_roundtrip() -> None:
    """Event store should support CRUD and summary hydration."""
    store = AcqImageEventStore()
    first = store.add_rect(2.0, 1.0)
    second = store.add_rect(5.0, 8.0, event_type=EventType.TRANSIENT)

    assert first.id == 1
    assert first.duration == 1.0
    assert first.x_min == 1.0
    assert second.id == 2

    updated = store.update_rect(second.id, x1=9.0, event_type=EventType.RISE)
    assert updated.duration == 4.0
    assert updated.event_type is EventType.RISE

    store.delete_rect(first.id)
    summary = store.to_summary_dict()
    reloaded = AcqImageEventStore.from_summary_dict(summary)

    assert [event.to_json_dict() for event in reloaded.get_rects()] == [
        {"id": 2, "x0": 5.0, "x1": 9.0, "event_type": "rise", "duration": 4.0}
    ]


def test_event_store_rejects_duplicate_ids() -> None:
    """Event store should reject duplicate event ids."""
    store = AcqImageEventStore([AcqImageEvent(id=1, x0=0.0, x1=1.0)])
    with pytest.raises(ValueError):
        store.add_rect(2.0, 3.0, event_id=1)


def test_event_analysis_persists_events_in_summary() -> None:
    """EventAnalysis should serialize events through AnalysisResult.summary."""
    analysis = EventAnalysis(channel=0, roi_id=10)
    event = analysis.add_rect(1.0, 3.0, event_type=EventType.USER)

    record = analysis.to_json_dict()
    assert record["analysis_name"] == "event"
    assert record["summary"]["events"][0]["id"] == event.id

    reloaded = EventAnalysis(channel=0, roi_id=10)
    reloaded.load_json_dict(record)

    events = reloaded.get_rects()
    assert len(events) == 1
    assert events[0].id == event.id
    assert events[0].x0 == 1.0
    assert events[0].x1 == 3.0
    assert not reloaded.is_dirty()


def test_event_analysis_can_coexist_with_primary_analysis() -> None:
    """Event analysis should not conflict with primary-kymograph analyses."""
    from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import RadonVelocityAnalysis

    analysis_set = AcqAnalysisSet("fake.tif")
    analysis_set.add(RadonVelocityAnalysis(channel=0, roi_id=1))
    event_analysis = analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)

    assert analysis_set.get_required(AnalysisKey("radon_velocity", 0, 1)) is not None
    assert isinstance(event_analysis, EventAnalysis)
