"""Tests for Home page splitter handle helper."""

from __future__ import annotations

from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from cloudscope.views.splitter_handle import add_splitter_handle


def _fake_splitter() -> SimpleNamespace:
    """Return a minimal splitter stand-in with a separator context manager."""
    return SimpleNamespace(separator=nullcontext())


def test_add_splitter_handle_creates_handle_elements_by_default() -> None:
    """Default calls should add wrap and handle elements inside the separator."""
    splitter = _fake_splitter()
    created: list[str] = []

    def _element(tag: str) -> MagicMock:
        created.append(tag)
        element = MagicMock()
        element.classes = MagicMock(side_effect=lambda *_args, **_kwargs: element)
        element.on = MagicMock()
        return element

    with patch('cloudscope.views.splitter_handle.ui') as mock_ui:
        mock_ui.element = _element
        mock_ui.add_css = MagicMock()
        add_splitter_handle(splitter, orientation='vertical', offset='after')

    assert created == ['div', 'div']


def test_add_splitter_handle_show_false_skips_handle_elements() -> None:
    """Toolbar splitters may hide the custom pill while keeping native drag."""
    splitter = _fake_splitter()
    created: list[str] = []

    def _element(tag: str) -> MagicMock:
        created.append(tag)
        element = MagicMock()
        element.classes = MagicMock(side_effect=lambda *_args, **_kwargs: element)
        return element

    with patch('cloudscope.views.splitter_handle.ui') as mock_ui:
        mock_ui.element = _element
        mock_ui.add_css = MagicMock()
        add_splitter_handle(splitter, show_handle=False)

    assert created == []
