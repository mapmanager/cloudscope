"""Tests for Option C desktop launcher helpers."""

from __future__ import annotations

import os


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
