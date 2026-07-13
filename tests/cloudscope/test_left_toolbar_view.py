"""Tests for LeftToolbarView composition state."""

from __future__ import annotations

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.events.app_config import BlindedAnalysisModeChanged
from cloudscope.views.app_config_view import AppConfigView
from cloudscope.views.debug_view import DebugView
from cloudscope.views.left_panel_file_list_view import LeftPanelFileListView
from cloudscope.views.left_toolbar_view import LeftPanelReferenceImageView, LeftToolbarView
from cloudscope.views.metadata_widget.experiment_metadata_view import ExperimentMetadataView
from cloudscope.views.metadata_widget.image_header_metadata_view import ImageHeaderMetadataView
from cloudscope.views.diameter_analysis_view import DiameterAnalysisView
from cloudscope.views.sum_intensity_analysis_view import SumIntensityAnalysisView
from cloudscope.views.velocity_analysis_view import VelocityAnalysisView
from cloudscope.views.view_ids import ViewId
from cloudscope.views.view_manager import ViewManager


class _FakeButton:
    """Minimal button stand-in for toolbar state tests."""

    def __init__(self) -> None:
        self.enabled = True
        self.props_values: list[str] = []
        self.update_count = 0

    def props(self, value: str) -> None:
        self.props_values.append(value)

    def update(self) -> None:
        self.update_count += 1


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
    assert isinstance(view.debug_view, DebugView)
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
        ViewId.DEBUG,
    )
    assert view.active_view_id is None


def test_left_toolbar_resolves_valid_initial_active_tab(tmp_path) -> None:
    """A valid initial tab id should be honored for build-time restore."""
    config = AppConfig.load(config_path=tmp_path / "app_config.json")
    view = LeftToolbarView(
        event_bus=EventBus(),
        app_state=None,
        app_config=config,
        view_manager=ViewManager(),
        initial_active_view_id=ViewId.SUM_INTENSITY_ANALYSIS,
    )

    assert view._resolve_initial_active_view_id() is ViewId.SUM_INTENSITY_ANALYSIS  # noqa: SLF001


def test_left_toolbar_ignores_unknown_initial_active_tab(tmp_path) -> None:
    """An id this toolbar cannot display should collapse to no active tab."""
    config = AppConfig.load(config_path=tmp_path / "app_config.json")
    view = LeftToolbarView(
        event_bus=EventBus(),
        app_state=None,
        app_config=config,
        view_manager=ViewManager(),
        initial_active_view_id=ViewId.PRIMARY_IMAGE,
    )

    assert view._resolve_initial_active_view_id() is None  # noqa: SLF001


def test_left_toolbar_disables_metadata_button_when_blinded(tmp_path) -> None:
    config = AppConfig.load(config_path=tmp_path / "app_config.json")
    config.set_blinded(True)
    view = LeftToolbarView(
        event_bus=EventBus(),
        app_state=None,
        app_config=config,
        view_manager=ViewManager(),
    )
    metadata_button = _FakeButton()
    config_button = _FakeButton()
    view._buttons = {  # noqa: SLF001
        ViewId.EXPERIMENT_METADATA: metadata_button,
        ViewId.APP_CONFIG: config_button,
    }

    view._refresh_button_state()  # noqa: SLF001

    assert metadata_button.enabled is False
    assert config_button.enabled is True


def test_left_toolbar_ignores_metadata_click_when_blinded(tmp_path, monkeypatch) -> None:
    config = AppConfig.load(config_path=tmp_path / "app_config.json")
    config.set_blinded(True)
    view = LeftToolbarView(
        event_bus=EventBus(),
        app_state=None,
        app_config=config,
        view_manager=ViewManager(),
    )
    calls: list[ViewId | None] = []
    monkeypatch.setattr(view, "_apply_active_view", calls.append)

    view._on_tab_clicked(ViewId.EXPERIMENT_METADATA)  # noqa: SLF001

    assert calls == []


def test_left_toolbar_closes_metadata_when_blinded_turns_on(tmp_path, monkeypatch) -> None:
    config = AppConfig.load(config_path=tmp_path / "app_config.json")
    view = LeftToolbarView(
        event_bus=EventBus(),
        app_state=None,
        app_config=config,
        view_manager=ViewManager(),
    )
    view._active_view_id = ViewId.EXPERIMENT_METADATA  # noqa: SLF001
    calls: list[ViewId | None] = []
    monkeypatch.setattr(view, "_apply_active_view", calls.append)

    view.on_blinded_analysis_mode_changed(BlindedAnalysisModeChanged(blinded=True))

    assert calls == [None]
