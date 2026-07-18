"""Tests for native dialog helpers (no GUI)."""

from __future__ import annotations

from acqstore_server.dialogs import default_extensions, normalize_extensions


def test_default_extensions_include_common_types() -> None:
    exts = default_extensions()
    assert all(e.startswith('.') for e in exts)
    assert '.tif' in exts or '.tiff' in exts
    assert '.oir' in exts


def test_normalize_extensions_adds_dots() -> None:
    assert normalize_extensions(['oir', '.CZI', 'tif']) == ['.oir', '.czi', '.tif']


def test_normalize_extensions_none_uses_defaults() -> None:
    assert normalize_extensions(None) == default_extensions()
