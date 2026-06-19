"""Lightweight tests for ``header_view`` API (no NiceGUI client required)."""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

import pytest

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.events.theme import ThemeChanged
from cloudscope.views.header_view import CLOUDSCOPE_GITHUB_URL, _open_external, _open_pool, build_main_header, enable_page_dark_mode


def test_build_main_header_signature_accepts_title() -> None:
    """Header builder stays a simple page-level hook with configurable title."""
    sig = inspect.signature(build_main_header)
    assert "title" in sig.parameters
    assert "event_bus" in sig.parameters
    params = sig.parameters["title"]
    assert params.default == "CloudScope"


def test_build_main_header_is_documented_callable() -> None:
    assert callable(build_main_header)
    assert build_main_header.__doc__


def test_header_view_exposes_cloudscope_github_url() -> None:
    assert CLOUDSCOPE_GITHUB_URL == "https://github.com/mapmanager/cloudscope"


def test_open_external_uses_system_browser_for_option_c(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: object())
    with patch('cloudscope.views.header_view.webbrowser.open') as open_url:
        with patch('cloudscope.views.header_view.ui.run_javascript') as run_js:
            _open_external(CLOUDSCOPE_GITHUB_URL)
    open_url.assert_called_once_with(CLOUDSCOPE_GITHUB_URL)
    run_js.assert_not_called()


def test_open_pool_uses_desktop_launcher_when_available() -> None:
    launcher = MagicMock()
    with patch('cloudscope.desktop_launcher.get_pool_launcher', return_value=launcher):
        _open_pool()
    launcher.open_pool.assert_called_once()


def test_open_pool_uses_window_open_in_web_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: None, raising=False)
    with patch('cloudscope.views.header_view.app') as mock_app:
        mock_app.native = None
        with patch('cloudscope.views.header_view.ui.run_javascript') as run_js:
            _open_pool()
    run_js.assert_called_once_with("window.open('/pool', 'cloudscope_pool')")


def test_open_pool_warns_in_legacy_single_window_native(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: None, raising=False)
    native = MagicMock()
    native.main_window = object()
    with patch('cloudscope.views.header_view.app') as mock_app:
        mock_app.native = native
        with patch('cloudscope.views.header_view.ui.notify') as notify:
            with patch('cloudscope.views.header_view.ui.run_javascript') as run_js:
                _open_pool()
    notify.assert_called_once()
    run_js.assert_not_called()


def test_enable_page_dark_mode_syncs_theme_changed() -> None:
    """Pool-style pages should follow ThemeChanged via NiceGUI dark mode."""
    app_config = AppConfig.ephemeral()
    app_config.data.dark_mode = False
    bus = EventBus()
    dark_mode_el = MagicMock()

    with patch('cloudscope.views.header_view.ui.dark_mode', return_value=dark_mode_el) as dark_mode_factory:
        subscription = enable_page_dark_mode(app_config, bus)

    dark_mode_factory.assert_called_once_with(value=False)
    bus.publish(ThemeChanged(dark_mode=True))
    assert dark_mode_el.value is True
    subscription.unsubscribe()
