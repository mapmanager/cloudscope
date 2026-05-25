"""Tests for velocity analysis view non-UI behavior."""

from __future__ import annotations

from cloudscope.event_bus import EventBus
from cloudscope.state import PrimarySelection
from cloudscope.views.base_view import BaseView
from cloudscope.views.velocity_analysis_view import VelocityAnalysisView
from cloudscope.views.view_ids import ViewId


def test_velocity_analysis_view_is_base_view() -> None:
    """VelocityAnalysisView should participate in BaseView lifecycle."""
    view = VelocityAnalysisView(event_bus=EventBus())

    assert isinstance(view, BaseView)
    assert view.view_id is ViewId.VELOCITY_ANALYSIS


def test_velocity_analysis_view_selection_snapshot_uses_base_selection() -> None:
    """Selection snapshot should copy the BaseView cached selection."""
    view = VelocityAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id='/tmp/a.oir', channel=1, roi_id=2)

    snapshot = view._selection_snapshot()

    assert snapshot == PrimarySelection(file_id='/tmp/a.oir', channel=1, roi_id=2)
    assert snapshot is not view.current_selection


def test_velocity_analysis_view_has_no_view_level_cancel_button() -> None:
    """Cancellation should be handled by TaskProgressDialogView, not this panel."""
    view = VelocityAnalysisView(event_bus=EventBus())

    assert not hasattr(view, '_cancel_button')

from cloudscope.events.roi import RoiChanged, RoiChangeKind


def test_velocity_analysis_view_refreshes_on_roi_changed_for_current_file() -> None:
    """VelocityAnalysisView should refresh when ROI model changes for current file."""
    view = VelocityAnalysisView(event_bus=EventBus())
    view.current_selection = PrimarySelection(file_id="file-a", channel=0, roi_id=1)
    calls = []
    view._refresh_selection_dependent_ui = lambda: calls.append("refresh")  # type: ignore[method-assign]

    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="file-a", channel=0, roi_id=None),
        )
    )
    view._on_roi_changed(
        RoiChanged(
            operation=RoiChangeKind.DELETE,
            selection=PrimarySelection(file_id="other", channel=0, roi_id=None),
        )
    )

    assert calls == ["refresh"]
