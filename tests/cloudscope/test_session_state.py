"""Tests for reconnect session snapshot helpers and view blobs."""

from __future__ import annotations

import pytest

from cloudscope.session_state import (
    VIEW_SESSION_SCHEMA_VERSION,
    HomePageChromeState,
    HomePageRestorableState,
    HomePageSessionSnapshot,
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


def test_home_page_restorable_state_round_trip() -> None:
    """Restorable app state should survive a to_dict/from_dict round trip."""
    state = HomePageRestorableState(
        selection=PrimarySelection(file_id='file-a', channel=1, roi_id=2),
        primary_x_range=(10.0, 20.0),
        file_ids=('file-a', 'file-b'),
    )
    restored = HomePageRestorableState.from_dict(state.to_dict())
    assert restored.selection == state.selection
    assert restored.primary_x_range == (10.0, 20.0)
    assert restored.file_ids == ('file-a', 'file-b')
    assert restored.schema_version == VIEW_SESSION_SCHEMA_VERSION


def test_home_page_chrome_state_round_trip() -> None:
    """Chrome flags should survive a to_dict/from_dict round trip."""
    chrome = HomePageChromeState(
        file_list_open=True,
        analysis_plot_open=False,
        left_toolbar_active_view_id='sum_intensity_analysis',
        right_pool_open=True,
    )
    restored = HomePageChromeState.from_dict(chrome.to_dict())
    assert restored == chrome


def test_home_page_chrome_state_capture_and_collapsed_left_toolbar() -> None:
    """Capture should record left-tab id and treat None as collapsed."""
    chrome = HomePageChromeState.capture(
        file_list_open=True,
        analysis_plot_open=True,
        left_toolbar_active_view_id=None,
        right_pool_open=False,
    )
    assert chrome.left_toolbar_active_view_id is None
    restored = HomePageChromeState.from_dict(chrome.to_dict())
    assert restored.left_toolbar_active_view_id is None
    assert restored.file_list_open is True


def test_home_page_session_snapshot_round_trip() -> None:
    """Snapshot serialization should preserve chrome, app state, and views."""
    snapshot = HomePageSessionSnapshot(
        chrome=HomePageChromeState.defaults(),
        app_state=HomePageRestorableState(
            selection=PrimarySelection(file_id='file-a'),
            primary_x_range=(0.0, 5.0),
            file_ids=('file-a',),
        ),
        views={'primary_image': {'schema_version': VIEW_SESSION_SCHEMA_VERSION}},
    )
    restored = HomePageSessionSnapshot.from_dict(snapshot.to_dict())
    assert restored.chrome == snapshot.chrome
    assert restored.app_state.selection == snapshot.app_state.selection
    assert restored.app_state.primary_x_range == (0.0, 5.0)
    assert restored.views == snapshot.views


def test_session_snapshot_from_dict_rejects_bad_schema() -> None:
    """Unsupported schema versions on the snapshot should fail fast."""
    payload = HomePageSessionSnapshot.empty().to_dict()
    payload['schema_version'] = 999
    with pytest.raises(ValueError, match='unsupported'):
        HomePageSessionSnapshot.from_dict(payload)
