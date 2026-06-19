"""Tests for desktop pywebview detection in clipboard helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from nicewidgets.utils import clipboard as clipboard_mod


def test_is_pywebview_desktop_true_for_nicegui_native_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        clipboard_mod.app,
        'native',
        SimpleNamespace(main_window=object()),
        raising=False,
    )

    assert clipboard_mod.is_pywebview_desktop() is True


def test_is_pywebview_desktop_true_for_option_c_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clipboard_mod.app, 'native', SimpleNamespace(main_window=None), raising=False)

    fake_webview = SimpleNamespace(windows=[object()])
    monkeypatch.setitem(__import__('sys').modules, 'webview', fake_webview)

    assert clipboard_mod.is_pywebview_desktop() is True


def test_is_pywebview_desktop_false_for_browser(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(clipboard_mod.app, 'native', SimpleNamespace(main_window=None), raising=False)

    fake_webview = SimpleNamespace(windows=[])
    monkeypatch.setitem(__import__('sys').modules, 'webview', fake_webview)

    assert clipboard_mod.is_pywebview_desktop() is False
