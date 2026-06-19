"""Tests for :class:`CziFileLoader` header normalization."""

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader
from acqstore.acq_image.file_loaders.czi_file_loader import CziFileLoader


def _czi_header(
    *,
    dims: tuple[str, ...],
    shape: tuple[int, ...] | None = None,
    physical_units_labels: tuple[str, ...] | None = None,
) -> ImageHeader:
    """Build a minimal CZI-like header for unit tests."""
    if shape is None:
        shape = tuple(2 if dim == 'C' else 10 for dim in dims)
    sizes = {dim: shape[i] for i, dim in enumerate(dims)}
    num_channels = int(sizes['C']) if 'C' in sizes else 1
    n = len(dims)
    if physical_units_labels is None:
        physical_units_labels = dims
    return ImageHeader(
        path='/tmp/linescan.czi',
        shape=shape,
        dims=dims,
        sizes=sizes,
        dtype=np.dtype(np.uint16),
        num_channels=num_channels,
        num_scenes=1,
        physical_units=tuple(1.0 for _ in range(n)),
        physical_units_labels=physical_units_labels,
    )


@contextmanager
def _fake_open_czi(_self: CziFileLoader):
    """Yield a minimal czifile-like object with one scene."""
    czi_file = MagicMock()
    czi_file.scenes = [MagicMock()]
    yield czi_file


def _read_header_with_patch(raw_header: ImageHeader) -> ImageHeader:
    """Call :meth:`CziFileLoader._read_czi_header` without touching disk."""
    loader = CziFileLoader('/tmp/linescan.czi', header=raw_header)
    with patch.object(CziFileLoader, '_open_czi', _fake_open_czi):
        with patch(
            'acqstore.acq_image.file_loaders.czi_file_loader._image_header_from_scene',
            return_value=raw_header,
        ):
            return loader._read_czi_header()


def test_read_czi_header_remaps_linescan_t_to_y(caplog: pytest.LogCaptureFixture) -> None:
    """('C', 'T', 'X') line-scan headers gain a Y axis label."""
    raw = _czi_header(dims=('C', 'T', 'X'), shape=(2, 30000, 24))
    header = _read_header_with_patch(raw)

    assert header.dims == ('C', 'Y', 'X')
    assert header.sizes == {'C': 2, 'Y': 30000, 'X': 24}
    assert header.physical_units_labels == ('C', 'Y', 'X')
    assert 'remapping \'T\' axis to \'Y\'' in caplog.text


@pytest.mark.parametrize(
    'dims',
    [
        ('C', 'T', 'Y', 'X'),
        ('C', 'Y', 'X'),
    ],
)
def test_read_czi_header_leaves_existing_y_dims_unchanged(
    dims: tuple[str, ...],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Frame stacks and 2D CZI layouts must not remap T when Y exists."""
    raw = _czi_header(dims=dims)
    header = _read_header_with_patch(raw)

    assert header.dims == dims
    assert header.sizes == raw.sizes
    assert 'remapping \'T\' axis to \'Y\'' not in caplog.text
