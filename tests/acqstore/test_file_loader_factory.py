"""Tests for :func:`acqstore.acq_image.file_loaders.file_loader_factory.create_file_loader`."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.file_loaders.file_loader_factory import create_file_loader
from acqstore.acq_image.supported_import_extensions import (
    add_allowed_import_extension,
    get_allowed_import_extensions,
    remove_allowed_import_extension,
    set_allowed_import_extensions,
)
from acqstore.acq_image.file_loaders.tiff_file_loader import TiffFileLoader


def test_create_file_loader_rejects_unknown_suffix(tmp_path: Path) -> None:
    path = tmp_path / 'x.xyz'
    path.write_text('')
    with pytest.raises(ValueError, match='Unsupported acquisition file extension'):
        create_file_loader(str(path))


def test_create_file_loader_rejects_tiff_suffix(tmp_path: Path) -> None:
    path = tmp_path / 'x.tiff'
    path.write_text('')
    with pytest.raises(ValueError, match='Unsupported acquisition file extension'):
        create_file_loader(str(path))


def test_create_file_loader_tif_returns_tiff_loader(tmp_path: Path) -> None:
    path = tmp_path / 'a.tif'
    tifffile.imwrite(path, np.zeros((2, 2), dtype=np.uint8))
    loader = create_file_loader(str(path))
    assert isinstance(loader, TiffFileLoader)


def test_create_file_loader_uppercase_suffix_tif(tmp_path: Path) -> None:
    path = tmp_path / 'a.TIF'
    tifffile.imwrite(path, np.zeros((2, 2), dtype=np.uint8))
    loader = create_file_loader(str(path))
    assert isinstance(loader, TiffFileLoader)


def test_acq_image_rejects_unsupported_extension_via_factory(tmp_path: Path) -> None:
    path = tmp_path / 'x.tiff'
    path.write_text('')
    with pytest.raises(ValueError, match='Unsupported acquisition file extension'):
        AcqImage(str(path))


def test_factory_obeys_runtime_extension_set(tmp_path: Path) -> None:
    set_allowed_import_extensions(['abc'])
    assert get_allowed_import_extensions() == ('abc',)
    path = tmp_path / 'x.tif'
    path.write_text('')
    with pytest.raises(ValueError, match='Unsupported acquisition file extension'):
        create_file_loader(str(path))


def test_factory_respects_add_remove_extension_runtime(tmp_path: Path) -> None:
    remove_allowed_import_extension('tif')
    path = tmp_path / 'x.tif'
    path.write_text('')
    with pytest.raises(ValueError, match='Unsupported acquisition file extension'):
        create_file_loader(str(path))
    add_allowed_import_extension('tif')
    tifffile.imwrite(path, np.zeros((2, 2), dtype=np.uint8))
    loader = create_file_loader(str(path))
    assert isinstance(loader, TiffFileLoader)
