"""Reference-image tests for the API v2 open service."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile

from acqstore.acq_image.file_loaders.base_file_loader import BaseFileLoader, ReferenceImage
from acqstore_server.v2.open_service import open_acquisition


def _write_yx_tif(path: Path) -> None:
    tifffile.imwrite(
        path,
        np.arange(6 * 5, dtype=np.uint16).reshape(6, 5),
        metadata={'axes': 'YX'},
        photometric='minisblack',
    )


def test_reference_channels_and_coordinates_remain_acqstore_native(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / 'reference.tif'
    _write_yx_tif(path)

    channel_0 = np.arange(4 * 5, dtype=np.float32).reshape(4, 5)
    channel_1 = channel_0 + 100.0
    reference = ReferenceImage(
        array=np.stack([channel_0, channel_1], axis=0),
        dims=('C', 'Y', 'X'),
        num_channels=2,
        line_roi=(1.0, 2.0, 4.0, 3.0),
        coord_units=(('X', 'um'), ('Y', 'um')),
        coord_scales=(('X', 0.25), ('Y', 0.5)),
        coords=(),
        scan_path=np.asarray([[1.0, 4.0], [2.0, 3.0]], dtype=float),
    )
    monkeypatch.setattr(BaseFileLoader, 'has_reference_image', property(lambda self: True))
    monkeypatch.setattr(BaseFileLoader, 'reference_image', property(lambda self: reference))

    opened = open_acquisition(str(path))

    assert opened.reference is not None
    assert [channel.index for channel in opened.reference.channels] == [0, 1]
    np.testing.assert_array_equal(opened.reference.channels[0].array, channel_0)
    np.testing.assert_array_equal(opened.reference.channels[1].array, channel_1)
    assert [axis.name for axis in opened.reference.axes] == ['Y', 'X']
    assert [axis.size for axis in opened.reference.axes] == [4, 5]
    assert [axis.step for axis in opened.reference.axes] == pytest.approx([0.5, 0.25])
    assert [axis.unit for axis in opened.reference.axes] == ['um', 'um']
    assert opened.reference.line_roi == (1.0, 2.0, 4.0, 3.0)
    assert opened.reference.scan_path is not None
    assert opened.reference.scan_path.x == (1.0, 4.0)
    assert opened.reference.scan_path.y == (2.0, 3.0)
