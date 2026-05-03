"""Tests for event-style analysis APIs."""

import pytest

from acqstore.acq_image.analysis.examples import VelocityEventAnalysis


def test_velocity_event_analysis_event_crud() -> None:
    """VelocityEventAnalysis should manage event dictionaries."""
    analysis = VelocityEventAnalysis(channel=0, roi_id=1)
    analysis.add_event({"event_id": 1, "kind": "stall"})
    analysis.edit_event(1, {"kind": "fast"})
    analysis.delete_event(1)

    assert analysis.result.summary["events"] == []
    assert analysis.result.summary["num_events"] == 0
    assert analysis.is_dirty()


def test_velocity_event_edit_missing_event_raises() -> None:
    """Editing a missing event should raise KeyError."""
    analysis = VelocityEventAnalysis(channel=0, roi_id=1)

    with pytest.raises(KeyError):
        analysis.edit_event(1, {"kind": "fast"})
