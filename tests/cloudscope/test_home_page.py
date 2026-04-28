"""Tests for home-page startup config loading helpers."""

from __future__ import annotations

from cloudscope.gui.app_config import AppConfig
from cloudscope.gui.home_page import _load_initial_acq_image_list


def test_load_initial_list_returns_none_when_last_path_unset(tmp_path) -> None:
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    cfg.set_last_path('')

    result = _load_initial_acq_image_list(cfg)
    assert result is None


def test_load_initial_list_warns_and_returns_none_on_failure(tmp_path, monkeypatch) -> None:
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    cfg.set_last_path(tmp_path / 'bad.tif')
    notify_calls: list[str] = []

    class FailingAcqImageList:
        def __init__(self, _path: str) -> None:
            raise RuntimeError('boom')

    def _notify(message: str, *, type: str) -> None:
        notify_calls.append(f'{type}:{message}')

    monkeypatch.setattr('cloudscope.gui.home_page.AcqImageList', FailingAcqImageList)
    monkeypatch.setattr('cloudscope.gui.home_page.ui.notify', _notify)

    result = _load_initial_acq_image_list(cfg)
    assert result is None
    assert len(notify_calls) == 1
    assert 'warning:Could not load last path:' in notify_calls[0]


def test_load_initial_list_updates_recent_folder_and_last_path(tmp_path, monkeypatch) -> None:
    cfg = AppConfig.load(config_path=tmp_path / 'app_config.json')
    folder = tmp_path / 'folder'
    folder.mkdir()
    cfg.set_last_path(folder)

    class DummyAcqImageList:
        def __init__(self, path: str) -> None:
            self.path = path

    monkeypatch.setattr('cloudscope.gui.home_page.AcqImageList', DummyAcqImageList)

    result = _load_initial_acq_image_list(cfg)
    assert result is not None
    assert cfg.get_recent_folders()[-1] == str(folder.resolve())
    assert cfg.get_last_path() == str(folder.resolve())
