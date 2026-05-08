"""Tests for load/save toolbar view logic."""

from __future__ import annotations

from cloudscope.event_bus import EventBus
from cloudscope.events import (
    AppStatusChanged,
    FileSelectionChanged,
    StatusLevel,
    StatusSource,
)
from cloudscope.app_config import AppConfig, normalize_stored_path
from cloudscope.views.load_save_view import LoadSaveView


class _ToggleButton:
    """Fake button tracking enable/disable calls."""

    def __init__(self) -> None:
        self.disabled = False

    def disable(self) -> None:
        """Mark disabled."""
        self.disabled = True

    def enable(self) -> None:
        """Mark enabled."""
        self.disabled = False


class _DirtyAcqImage:
    """Fake acquisition image exposing dirty state."""

    is_dirty = True


class _CleanAcqImage:
    """Fake acquisition image exposing clean state."""

    is_dirty = False


def test_save_selected_disabled_without_dirty_selection(tmp_path) -> None:
    """Selection state tracked by BaseView should drive save-selected state."""
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    view = LoadSaveView(event_bus=bus, app_config=cfg)
    view._save_selected_button = _ToggleButton()
    view._save_all_button = _ToggleButton()
    view.on_show()

    bus.publish(FileSelectionChanged(file_id=None, acq_image=None, channel=None, roi_id=None))

    assert view._save_selected_button.disabled is True


def test_save_selected_enabled_with_dirty_selection(tmp_path) -> None:
    """Dirty selected AcqImage should enable Save Selected."""
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    view = LoadSaveView(event_bus=bus, app_config=cfg)
    view._save_selected_button = _ToggleButton()
    view._save_all_button = _ToggleButton()
    view.on_show()

    bus.publish(FileSelectionChanged(file_id='/tmp/a.oir', acq_image=_DirtyAcqImage(), channel=0, roi_id=1))

    assert view._save_selected_button.disabled is False




def test_save_selected_disabled_with_clean_selection(tmp_path) -> None:
    """Clean selected AcqImage should keep Save Selected disabled."""
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    view = LoadSaveView(event_bus=bus, app_config=cfg)
    view._save_selected_button = _ToggleButton()
    view._save_all_button = _ToggleButton()
    view.on_show()

    bus.publish(FileSelectionChanged(file_id='/tmp/a.oir', acq_image=_CleanAcqImage(), channel=0, roi_id=1))

    assert view._save_selected_button.disabled is True


def test_recent_item_matches_app_path_respects_last_path(tmp_path) -> None:
    """Recent path comparison should normalize the persisted last path."""
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    file_path = tmp_path / 'doc.tif'
    file_path.write_text('x', encoding='utf-8')
    cfg.set_last_path(str(file_path))
    view = LoadSaveView(event_bus=bus, app_config=cfg)
    assert view._recent_item_matches_app_path(str(file_path))
    assert view._recent_item_matches_app_path(normalize_stored_path(str(file_path)))
    assert not view._recent_item_matches_app_path(str(tmp_path / 'other.tif'))


def test_recent_item_matches_app_path_false_when_last_path_empty(tmp_path) -> None:
    """Empty last path should never match a recent item."""
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    view = LoadSaveView(event_bus=bus, app_config=cfg)
    assert cfg.get_last_path() == ''
    assert not view._recent_item_matches_app_path('/any/path')


def test_status_event_calls_notify(tmp_path, monkeypatch) -> None:
    """LoadSaveView should still forward app status notifications."""
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    view = LoadSaveView(event_bus=bus, app_config=cfg)
    view.subscribe_events()
    notify_calls: list[str] = []

    def _notify(msg: str, *, type: str) -> None:
        notify_calls.append(f'{type}:{msg}')

    monkeypatch.setattr('cloudscope.views.load_save_view.ui.notify', _notify)
    bus.publish(AppStatusChanged(level=StatusLevel.INFO, message='ok', source=StatusSource.SYSTEM))
    assert notify_calls == ['info:ok']
