"""Tests for Home page splitter manager."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cloudscope.app_config import (
    DEFAULT_HOME_LEFT_TOOLBAR_OPEN_SPLITTER_PCT,
    HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT,
    AppConfig,
)
from cloudscope.views.splitter_manager import SplitterId, SplitterManager


@dataclass
class FakeSplitter:
    """Small fake object matching the subset of NiceGUI splitter API used by SplitterManager."""

    value: float
    update_count: int = 0

    def update(self) -> None:
        """Record an update call."""
        self.update_count += 1


def test_splitter_manager_set_value_clamps_and_remembers(tmp_path: Path) -> None:
    """Setting a splitter should clamp value and update AppConfig in memory."""
    cfg = AppConfig(path=tmp_path / 'app_config.json')
    manager = SplitterManager(cfg)
    splitter = FakeSplitter(value=0.0)
    manager.register(SplitterId.FILE_LIST, splitter)

    applied = manager.set_value(SplitterId.FILE_LIST, 999.0)

    assert applied == 60.0
    assert splitter.value == 60.0
    assert splitter.update_count == 1
    assert cfg.get_home_splitter_value('file_list') == 60.0


def test_splitter_manager_left_toolbar_open_closed(tmp_path: Path) -> None:
    """Left toolbar open/closed helpers should use closed and remembered open values."""
    cfg = AppConfig(path=tmp_path / 'app_config.json')
    manager = SplitterManager(cfg)
    splitter = FakeSplitter(value=HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT)
    manager.register(SplitterId.LEFT_TOOLBAR, splitter)

    manager.set_left_toolbar_open(True)
    assert splitter.value == DEFAULT_HOME_LEFT_TOOLBAR_OPEN_SPLITTER_PCT

    manager.set_left_toolbar_open(False)
    assert splitter.value == HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT


def test_splitter_manager_capture_does_not_remember_collapsed_left_toolbar(tmp_path: Path) -> None:
    """Collapsed left toolbar values should not replace the remembered open width."""
    cfg = AppConfig(path=tmp_path / 'app_config.json')
    manager = SplitterManager(cfg)
    splitter = FakeSplitter(value=HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT)
    manager.register(SplitterId.LEFT_TOOLBAR, splitter)

    manager.capture_current_value(SplitterId.LEFT_TOOLBAR)

    assert cfg.get_home_splitter_value('left_toolbar') == DEFAULT_HOME_LEFT_TOOLBAR_OPEN_SPLITTER_PCT


def test_splitter_manager_reset_all_updates_registered_splitters(tmp_path: Path) -> None:
    """Reset should restore registered splitters to factory values."""
    cfg = AppConfig(path=tmp_path / 'app_config.json')
    manager = SplitterManager(cfg)
    file_splitter = FakeSplitter(value=45.0)
    left_splitter = FakeSplitter(value=40.0)
    manager.register(SplitterId.FILE_LIST, file_splitter)
    manager.register(SplitterId.LEFT_TOOLBAR, left_splitter)
    cfg.set_home_splitter_value('file_list', 45.0)

    manager.reset_all()

    assert file_splitter.value == cfg.get_home_splitter_value('file_list')
    assert left_splitter.value == HOME_LEFT_TOOLBAR_CLOSED_SPLITTER_PCT
