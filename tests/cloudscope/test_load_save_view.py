"""Tests for load/save toolbar view logic."""

from __future__ import annotations

from cloudscope.event_bus import EventBus
from cloudscope.events import (
    AppStatusChanged,
    FileSelectionChanged,
    StatusLevel,
    StatusSource,
    TaskKind,
    TaskProgressChanged,
    TaskStatus,
)
from cloudscope.app_config import AppConfig, normalize_stored_path
from cloudscope.views.load_save_view import LoadSaveView


class _ToggleButton:
    def __init__(self) -> None:
        self.disabled = False

    def disable(self) -> None:
        self.disabled = True

    def enable(self) -> None:
        self.disabled = False


class _Dialog:
    def __init__(self) -> None:
        self.opened = False

    def open(self) -> None:
        self.opened = True

    def close(self) -> None:
        self.opened = False


class _Label:
    def __init__(self) -> None:
        self.text = ''


class _Progress:
    def __init__(self) -> None:
        self.value = 0.0


def test_save_selected_disabled_without_dirty_selection(tmp_path) -> None:
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    view = LoadSaveView(event_bus=bus, app_config=cfg)
    view.subscribe_events()
    view._save_selected_button = _ToggleButton()
    view._save_all_button = _ToggleButton()

    bus.publish(FileSelectionChanged(file_id=None, acq_image=None, channel=None, roi_id=None))
    assert view._save_selected_button.disabled is True


def test_task_progress_opens_and_closes_dialog(tmp_path) -> None:
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    view = LoadSaveView(event_bus=bus, app_config=cfg)
    view.subscribe_events()
    view._progress_dialog = _Dialog()
    view._progress_bar = _Progress()
    view._progress_label = _Label()
    view._progress_message = _Label()
    view._save_selected_button = _ToggleButton()
    view._save_all_button = _ToggleButton()

    bus.publish(
        TaskProgressChanged(
            task_kind=TaskKind.LOAD,
            task_id='1',
            task_label='Load file',
            status=TaskStatus.RUNNING,
            current=1,
            total=4,
            message='Step',
        )
    )
    assert view._progress_dialog.opened is True
    assert view._progress_bar.value == 0.25

    bus.publish(
        TaskProgressChanged(
            task_kind=TaskKind.LOAD,
            task_id='1',
            task_label='Load file',
            status=TaskStatus.COMPLETED,
            current=4,
            total=4,
            message='Done',
        )
    )
    assert view._progress_dialog.opened is False


def test_recent_item_matches_app_path_respects_last_path(tmp_path) -> None:
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
    bus = EventBus()
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    view = LoadSaveView(event_bus=bus, app_config=cfg)
    assert cfg.get_last_path() == ''
    assert not view._recent_item_matches_app_path('/any/path')


def test_status_event_calls_notify(tmp_path, monkeypatch) -> None:
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
