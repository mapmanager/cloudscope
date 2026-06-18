"""Tests for Option C desktop launcher helpers."""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch


@dataclass
class _RunConfig:
    host: str | None
    port: int | None
    native: bool
    reload: bool
    remote: bool
    storage_secret: str


def _local_native_config() -> _RunConfig:
    return _RunConfig(
        host=None,
        port=None,
        native=True,
        reload=False,
        remote=False,
        storage_secret='test-secret',
    )


def test_option_c_enabled_from_multi_window_env(monkeypatch) -> None:
    from cloudscope.desktop_launcher import option_c_enabled

    monkeypatch.setenv('CLOUDSCOPE_MULTI_WINDOW', '1')
    monkeypatch.delenv('CLOUDSCOPE_DESKTOP_LAUNCHER', raising=False)
    assert option_c_enabled() is True


def test_option_c_enabled_from_launcher_env(monkeypatch) -> None:
    from cloudscope.desktop_launcher import option_c_enabled

    monkeypatch.delenv('CLOUDSCOPE_MULTI_WINDOW', raising=False)
    monkeypatch.setenv('CLOUDSCOPE_DESKTOP_LAUNCHER', 'option_c')
    assert option_c_enabled() is True


def test_option_c_disabled_by_default(monkeypatch) -> None:
    from cloudscope.desktop_launcher import option_c_enabled

    monkeypatch.delenv('CLOUDSCOPE_MULTI_WINDOW', raising=False)
    monkeypatch.delenv('CLOUDSCOPE_DESKTOP_LAUNCHER', raising=False)
    assert option_c_enabled() is False


def test_single_window_requested(monkeypatch) -> None:
    from cloudscope.desktop_launcher import single_window_requested

    monkeypatch.delenv('CLOUDSCOPE_SINGLE_WINDOW', raising=False)
    assert single_window_requested() is False
    monkeypatch.setenv('CLOUDSCOPE_SINGLE_WINDOW', '1')
    assert single_window_requested() is True


def test_should_use_option_c_desktop_default_local_native(monkeypatch) -> None:
    from cloudscope.desktop_launcher import should_use_option_c_desktop

    monkeypatch.delenv('CLOUDSCOPE_SINGLE_WINDOW', raising=False)
    assert should_use_option_c_desktop(_local_native_config()) is True


def test_should_use_option_c_desktop_false_when_single_window(monkeypatch) -> None:
    from cloudscope.desktop_launcher import should_use_option_c_desktop

    monkeypatch.setenv('CLOUDSCOPE_SINGLE_WINDOW', '1')
    assert should_use_option_c_desktop(_local_native_config()) is False


def test_should_use_option_c_desktop_false_when_remote(monkeypatch) -> None:
    from cloudscope.desktop_launcher import should_use_option_c_desktop

    monkeypatch.delenv('CLOUDSCOPE_SINGLE_WINDOW', raising=False)
    config = _RunConfig(
        host='0.0.0.0',
        port=8080,
        native=False,
        reload=False,
        remote=True,
        storage_secret='test-secret',
    )
    assert should_use_option_c_desktop(config) is False


def test_should_use_option_c_desktop_false_when_not_native(monkeypatch) -> None:
    from cloudscope.desktop_launcher import should_use_option_c_desktop

    monkeypatch.delenv('CLOUDSCOPE_SINGLE_WINDOW', raising=False)
    config = _RunConfig(
        host=None,
        port=None,
        native=False,
        reload=False,
        remote=False,
        storage_secret='test-secret',
    )
    assert should_use_option_c_desktop(config) is False


def test_pool_launcher_open_pool_creates_window_with_offset() -> None:
    from cloudscope.desktop_launcher import POOL_WINDOW_HEIGHT, POOL_WINDOW_WIDTH, PoolLauncher

    class _FakeEventSlot:
        def __init__(self) -> None:
            self.handlers: list[object] = []

        def __iadd__(self, handler: object) -> _FakeEventSlot:
            self.handlers.append(handler)
            return self

    class _FakeEvents:
        def __init__(self) -> None:
            self.closed = _FakeEventSlot()

    main_window = MagicMock()
    main_window.x = 200
    main_window.y = 300
    pool_window = MagicMock()
    pool_window.events = _FakeEvents()

    with patch('webview.create_window', return_value=pool_window) as create_window:
        launcher = PoolLauncher(url_host='127.0.0.1', port=12345, main_window=main_window)
        launcher.open_pool()

    create_window.assert_called_once_with(
        'CloudScope Velocity Pool',
        url='http://127.0.0.1:12345/pool',
        x=240,
        y=340,
        width=POOL_WINDOW_WIDTH,
        height=POOL_WINDOW_HEIGHT,
    )
    assert launcher.pool_window is pool_window


def test_pool_launcher_open_pool_focuses_existing_window() -> None:
    from cloudscope.desktop_launcher import PoolLauncher

    pool_window = MagicMock()
    launcher = PoolLauncher(url_host='127.0.0.1', port=12345)
    launcher.pool_window = pool_window

    with patch('webview.create_window') as create_window:
        launcher.open_pool()

    pool_window.show.assert_called_once()
    create_window.assert_not_called()


def test_pool_launcher_default_position_without_main_window() -> None:
    from cloudscope.desktop_launcher import PoolLauncher

    launcher = PoolLauncher(url_host='127.0.0.1', port=12345)
    assert launcher._default_pool_position() == (140, 140)


def test_get_pool_launcher_none_outside_option_c() -> None:
    from cloudscope.desktop_launcher import get_pool_launcher

    assert get_pool_launcher() is None
