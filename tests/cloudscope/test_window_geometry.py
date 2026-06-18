"""Tests for Option C window geometry tracking."""

from __future__ import annotations

from unittest.mock import MagicMock

from cloudscope.app_config import AppConfig
from cloudscope.window_geometry import WindowGeometryTracker


class _FakeEventSlot:
    """Minimal pywebview-like event slot supporting ``+=`` registration."""

    def __init__(self) -> None:
        self.handlers: list[object] = []

    def __iadd__(self, handler: object) -> _FakeEventSlot:
        self.handlers.append(handler)
        return self


class _FakeEvents:
    def __init__(self) -> None:
        self.moved = _FakeEventSlot()
        self.resized = _FakeEventSlot()
        self.closed = _FakeEventSlot()


class _FakeWindow:
    def __init__(self, *, x: int = 10, y: int = 20, width: int = 800, height: int = 600) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.events = _FakeEvents()


def _main_tracker(app_config: AppConfig, window: _FakeWindow) -> WindowGeometryTracker:
    return WindowGeometryTracker(
        window,
        app_config.get_window_rect,
        app_config.set_window_rect,
        save=app_config.save,
    )


def test_attach_registers_move_and_resize_handlers(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    window = _FakeWindow()
    tracker = _main_tracker(app_config, window)

    tracker.attach()

    assert len(window.events.moved.handlers) == 1
    assert len(window.events.resized.handlers) == 1


def test_sync_from_window_updates_app_config(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    window = _FakeWindow(x=100, y=200, width=1200, height=900)
    tracker = _main_tracker(app_config, window)

    tracker.sync_from_window()

    assert app_config.get_window_rect() == (100, 200, 1200, 900)


def test_on_moved_preserves_width_and_height(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    app_config.set_window_rect(1, 2, 800, 600)
    window = _FakeWindow(x=50, y=60, width=800, height=600)
    tracker = _main_tracker(app_config, window)

    tracker._on_moved()

    assert app_config.get_window_rect() == (50, 60, 800, 600)


def test_on_resized_preserves_x_and_y(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    app_config.set_window_rect(10, 20, 800, 600)
    window = _FakeWindow(x=10, y=20, width=1024, height=768)
    tracker = _main_tracker(app_config, window)

    tracker._on_resized()

    assert app_config.get_window_rect() == (10, 20, 1024, 768)


def test_on_moved_sets_pool_rect_when_unset(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    window = _FakeWindow(x=50, y=60, width=1000, height=800)
    tracker = WindowGeometryTracker(
        window,
        app_config.get_pool_window_rect,
        app_config.set_pool_window_rect,
    )

    tracker._on_moved()

    assert app_config.get_pool_window_rect() == (50, 60, 1000, 800)


def test_persist_saves_once(tmp_path) -> None:
    app_config = AppConfig.ephemeral(config_path=tmp_path / 'config.json')
    window = _FakeWindow(x=11, y=22, width=333, height=444)
    save = MagicMock()
    tracker = WindowGeometryTracker(
        window,
        app_config.get_window_rect,
        app_config.set_window_rect,
        save=save,
    )

    tracker.persist()
    tracker.persist()

    save.assert_called_once()
    assert app_config.get_window_rect() == (11, 22, 333, 444)
