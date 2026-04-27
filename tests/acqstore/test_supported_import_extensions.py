"""Tests for runtime supported import extension configuration."""

from __future__ import annotations

import pytest

from acqstore.acq_image.supported_import_extensions import (
    DEFAULT_IMPORT_EXTENSIONS,
    add_allowed_import_extension,
    get_allowed_import_extensions,
    remove_allowed_import_extension,
    set_allowed_import_extensions,
)


def test_defaults_exposed_in_sorted_runtime_snapshot() -> None:
    assert get_allowed_import_extensions() == tuple(sorted(DEFAULT_IMPORT_EXTENSIONS))


def test_set_allowed_import_extensions_normalizes_values() -> None:
    set_allowed_import_extensions(['.TIF', ' OIR ', 'czi'])
    assert get_allowed_import_extensions() == ('czi', 'oir', 'tif')


def test_set_allowed_import_extensions_rejects_empty_set() -> None:
    with pytest.raises(ValueError, match='must not be empty'):
        set_allowed_import_extensions(['', '   '])


def test_add_and_remove_allowed_import_extension() -> None:
    add_allowed_import_extension('.NEW')
    assert 'new' in get_allowed_import_extensions()
    remove_allowed_import_extension('new')
    assert 'new' not in get_allowed_import_extensions()
