"""Tests for reconnect session snapshot helpers and view blobs."""

from __future__ import annotations

import pytest

from cloudscope.session_state import (
    VIEW_SESSION_SCHEMA_VERSION,
    require_keys,
    require_schema_version,
    selection_guard_from_selection,
    selection_guard_matches,
)
from cloudscope.state import PrimarySelection
from cloudscope.views.acq_analysis_plot_view import AcqAnalysisPlotView
from cloudscope.event_bus import EventBus


def test_require_keys_raises_on_missing_key() -> None:
    """Missing blob keys should fail fast."""
    with pytest.raises(KeyError, match='missing keys'):
        require_keys({'schema_version': 1}, 'schema_version', 'z')


def test_require_schema_version_rejects_mismatch() -> None:
    """Unsupported schema versions should raise."""
    with pytest.raises(ValueError, match='unsupported'):
        require_schema_version({'schema_version': 99})


def test_selection_guard_round_trip() -> None:
    """Exported guards should match the same selection on apply."""
    selection = PrimarySelection(
        file_id='file-a',
        channel=1,
        roi_id=2,
        analysis_name='sum_intensity',
    )
    blob = {'selection_guard': selection_guard_from_selection(selection)}
    assert selection_guard_matches(blob, selection) is True
    assert selection_guard_matches(blob, PrimarySelection(file_id='other')) is False


def test_acq_analysis_plot_view_session_round_trip() -> None:
    """Export/apply should preserve analysis plot session chrome."""
    view = AcqAnalysisPlotView(EventBus())
    view.current_selection = PrimarySelection(file_id='file-a', channel=0, roi_id=1)
    view._events_visible = False
    blob = view.export_session_state()
    assert blob['schema_version'] == VIEW_SESSION_SCHEMA_VERSION
    assert blob['events_visible'] is False

    view._events_visible = True
    view.apply_session_state(blob)
    assert view._events_visible is False
