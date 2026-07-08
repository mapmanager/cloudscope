"""Tests for cloudscope.utils.utils helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from cloudscope.utils import utils as utils_mod
from cloudscope.utils.utils import (
    _format_native_window_title,
    _path_display,
    set_native_main_window_title,
)


def test_path_display_shortens_home_relative_path() -> None:
    """Paths under the user home should display as ``~/...``."""
    home = Path.home()
    target = home / 'scratch' / 'x.tif'
    out = _path_display(str(target))
    assert out.startswith('~')
    assert 'scratch' in out


def test_path_display_returns_path_unchanged_outside_home() -> None:
    """Paths outside the user home should round-trip unchanged."""
    target = '/var/tmp/some/file.tif'
    assert _path_display(target) == target


def test_format_native_window_title_default_when_empty() -> None:
    """Unset path should use the static application title."""
    assert _format_native_window_title(None) == 'CloudScope'
    assert _format_native_window_title('') == 'CloudScope'
    assert _format_native_window_title('   ') == 'CloudScope'


def test_format_native_window_title_includes_display_path(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loaded paths should use the CloudScope prefix and shortened display path."""
    monkeypatch.setattr(utils_mod, '_path_display', lambda _path: '~/data/myfolder')
    assert _format_native_window_title('/Users/me/data/myfolder') == 'CloudScope — ~/data/myfolder'


def test_set_native_main_window_title_noop_without_main_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Browser mode should not attempt a native title update."""
    monkeypatch.setattr(utils_mod.app, 'native', SimpleNamespace(main_window=None), raising=False)
    set_native_main_window_title('/tmp/example.tif')


def test_set_native_main_window_title_calls_set_title(monkeypatch: pytest.MonkeyPatch) -> None:
    """Single-window native mode should update the NiceGUI WindowProxy title."""
    main_window = MagicMock()
    monkeypatch.setattr(
        utils_mod.app,
        'native',
        SimpleNamespace(main_window=main_window),
        raising=False,
    )
    set_native_main_window_title('/tmp/example.tif')
    main_window.set_title.assert_called_once_with('CloudScope — /tmp/example.tif')
