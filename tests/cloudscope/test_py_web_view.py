"""Tests for Option C and legacy native file picker wiring."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from cloudscope import _py_web_view


def test_prompt_for_path_uses_launcher_main_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Option C should open dialogs on the launcher main pywebview window."""
    main_window = MagicMock()
    main_window.create_file_dialog.return_value = ('/tmp/data',)
    launcher = SimpleNamespace(main_window=main_window)

    monkeypatch.setattr(_py_web_view.app, 'native', SimpleNamespace(main_window=None), raising=False)
    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: launcher)

    async def fake_io_bound(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(_py_web_view.run, 'io_bound', fake_io_bound)

    result = asyncio.run(_py_web_view._prompt_for_path(Path('/tmp'), dialog_type='folder'))

    assert result == '/tmp/data'
    main_window.create_file_dialog.assert_called_once()


def test_prompt_for_path_uses_nicegui_proxy_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Legacy single-window native mode should keep using the NiceGUI WindowProxy."""
    proxy = AsyncMock()
    proxy.create_file_dialog.return_value = ('/tmp/file.tif',)

    monkeypatch.setattr(_py_web_view.app, 'native', SimpleNamespace(main_window=proxy), raising=False)
    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: None)

    result = asyncio.run(
        _py_web_view._prompt_for_path(Path('/tmp'), dialog_type='file', file_extension='.tif')
    )

    assert result == '/tmp/file.tif'
    proxy.create_file_dialog.assert_awaited_once()
    _, kwargs = proxy.create_file_dialog.call_args
    assert kwargs['file_types'] == ('TIF files (*.tif)',)


def test_prompt_for_path_builds_multi_extension_file_filter(monkeypatch: pytest.MonkeyPatch) -> None:
    """Open-file dialogs should support one filter with multiple acquisition suffixes."""
    proxy = AsyncMock()
    proxy.create_file_dialog.return_value = ('/tmp/file.oir',)

    monkeypatch.setattr(_py_web_view.app, 'native', SimpleNamespace(main_window=proxy), raising=False)
    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: None)

    result = asyncio.run(
        _py_web_view._prompt_for_path(
            Path('/tmp'),
            dialog_type='file',
            file_extensions=('.tif', '.oir', '.czi', '.ome.zarr'),
            file_type_label='Acquisition files',
        )
    )

    assert result == '/tmp/file.oir'
    _, kwargs = proxy.create_file_dialog.call_args
    assert kwargs['file_types'] == ('Acquisition files (*.tif;*.oir;*.czi;*.ome.zarr)',)


def test_prompt_for_path_returns_none_without_desktop_window(monkeypatch: pytest.MonkeyPatch) -> None:
    """Browser mode should not attempt a native dialog when no desktop shell exists."""
    monkeypatch.setattr(_py_web_view.app, 'native', SimpleNamespace(main_window=None), raising=False)
    monkeypatch.setattr('cloudscope.desktop_launcher.get_pool_launcher', lambda: None)

    result = asyncio.run(_py_web_view._prompt_for_path(Path('/tmp'), dialog_type='folder'))

    assert result is None
