"""Tests for LeftToolbarView composition state."""

from __future__ import annotations

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.views.app_config_view import AppConfigView
from cloudscope.views.left_panel_file_list_view import LeftPanelFileListView
from cloudscope.views.left_toolbar_view import LeftPanelReferenceImageView, LeftToolbarView
from cloudscope.views.metadata_widget.experiment_metadata_view import ExperimentMetadataView
from cloudscope.views.metadata_widget.image_header_metadata_view import ImageHeaderMetadataView
from cloudscope.views.diameter_analysis_view import DiameterAnalysisView
from cloudscope.views.sum_intensity_analysis_view import SumIntensityAnalysisView
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
    assert isinstance(view.file_list_view, LeftPanelFileListView)
    assert isinstance(view.experiment_metadata_view, ExperimentMetadataView)
    assert isinstance(view.image_header_metadata_view, ImageHeaderMetadataView)
    assert isinstance(view.velocity_analysis_view, VelocityAnalysisView)
    assert isinstance(view.diameter_analysis_view, DiameterAnalysisView)
    assert isinstance(view.sum_intensity_analysis_view, SumIntensityAnalysisView)
    assert isinstance(view.app_config_view, AppConfigView)
    assert isinstance(view.reference_image_view, LeftPanelReferenceImageView)
    assert view.panel_view_ids == (
        ViewId.LEFT_TOOLBAR_FILE_LIST,
        ViewId.EXPERIMENT_METADATA,
        ViewId.IMAGE_HEADER_METADATA,
        ViewId.VELOCITY_ANALYSIS,
        ViewId.DIAMETER_ANALYSIS,
        ViewId.SUM_INTENSITY_ANALYSIS,
        ViewId.LEFT_TOOLBAR_REFERENCE_IMAGE,
        ViewId.APP_CONFIG,
        ViewId.APP_INFO,
    )
    assert view.active_view_id is None
