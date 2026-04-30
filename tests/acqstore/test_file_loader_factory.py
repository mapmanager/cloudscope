"""Tests for :func:`acqstore.acq_image.file_loaders.file_loader_factory.create_file_loader`."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile
from dataclasses import replace

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


def test_acq_image_metadata_patch_marks_dirty_and_save_clears(tmp_path: Path) -> None:
    path = tmp_path / 'a.tif'
    tifffile.imwrite(path, np.zeros((2, 2), dtype=np.uint8))
    acq = AcqImage(str(path))
    assert acq.is_dirty is False
    acq.apply_metadata_patch('experiment_metadata', {'species': 'mouse'})
    assert acq.is_dirty is True
    acq.save()
    assert acq.is_dirty is False


def test_acq_image_metadata_patch_unknown_section_raises(tmp_path: Path) -> None:
    path = tmp_path / 'a.tif'
    tifffile.imwrite(path, np.zeros((2, 2), dtype=np.uint8))
    acq = AcqImage(str(path))
    with pytest.raises(ValueError, match='Unknown metadata section'):
        acq.apply_metadata_patch('bad_section', {'species': 'mouse'})


def test_replace_header_updates_loader_header(tmp_path: Path) -> None:
    path = tmp_path / 'a.tif'
    tifffile.imwrite(path, np.zeros((2, 2), dtype=np.uint8))
    loader = create_file_loader(str(path))
    h = loader.header
    new_h = replace(
        h,
        physical_units=(2.5, 3.5),
        physical_units_labels=('um', 'mm'),
    )
    loader.replace_header(new_h)
    assert loader.header.physical_units == (2.5, 3.5)
    assert loader.header.physical_units_labels == ('um', 'mm')


def test_replace_header_rejects_path_mismatch(tmp_path: Path) -> None:
    path = tmp_path / 'a.tif'
    tifffile.imwrite(path, np.zeros((2, 2), dtype=np.uint8))
    loader = create_file_loader(str(path))
    wrong = replace(loader.header, path='/other/file.tif')
    with pytest.raises(ValueError, match='does not match loader path'):
        loader.replace_header(wrong)


def test_acq_image_exposes_experiment_and_header_metadata_sections(tmp_path: Path) -> None:
    path = tmp_path / 'a.tif'
    tifffile.imwrite(path, np.zeros((2, 2), dtype=np.uint8))
    acq = AcqImage(str(path))
    ids = tuple(section.metadata_section_id for section in acq.get_metadata_sections())
    assert ids == ('experiment_metadata', 'acq_image_header')
