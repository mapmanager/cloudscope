"""Tests for LeftToolbarView composition state."""

from __future__ import annotations

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.views.app_config_view import AppConfigView
from cloudscope.views.left_toolbar_view import LeftToolbarView
from cloudscope.views.metadata_widget.metadata_view import MetadataView
from cloudscope.views.velocity_analysis_view import VelocityAnalysisView
from cloudscope.views.view_ids import ViewId
from cloudscope.views.view_manager import ViewManager


def test_left_toolbar_constructs_panel_views(tmp_path) -> None:
    """LeftToolbarView should own the current left-panel child views."""
    bus = EventBus()
    config = AppConfig.load(config_path=tmp_path / "app_config.json")
    manager = ViewManager()

    view = LeftToolbarView(
        event_bus=bus,
        app_state=None,
        app_config=config,
        view_manager=manager,
    )

    assert view.view_id is ViewId.LEFT_TOOLBAR
    assert isinstance(view.metadata_view, MetadataView)
    assert isinstance(view.velocity_analysis_view, VelocityAnalysisView)
    assert isinstance(view.app_config_view, AppConfigView)
    assert view.panel_view_ids == (
        ViewId.METADATA,
        ViewId.VELOCITY_ANALYSIS,
        ViewId.APP_CONFIG,
        ViewId.APP_INFO,
    )
    assert view.active_view_id is None
