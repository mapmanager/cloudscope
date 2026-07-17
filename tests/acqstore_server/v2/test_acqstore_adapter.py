"""Minimal real-AcqStore smoke tests for API-drift detection.

These tests intentionally use only tiny generated TIFFs. They verify that the
public AcqImage surface consumed by the server still works; they do not attempt
to prove TIFF, OIR, CZI, or ND2 decoding correctness.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile

from acqstore_server.v2.open_service import open_acquisition


def test_real_acqstore_adapter_opens_one_small_yx_tiff(tmp_path: Path) -> None:
    path = tmp_path / 'adapter-smoke.tif'
    source = np.arange(24, dtype=np.uint16).reshape(6, 4)
    tifffile.imwrite(path, source, metadata={'axes': 'YX'}, photometric='minisblack')

    opened = open_acquisition(str(path))

    assert opened.num_source_channels == 1
    assert opened.source_dtype == 'uint16'
    assert [axis.name for axis in opened.axes] == ['Y', 'X']
    assert [axis.size for axis in opened.axes] == [6, 4]
    np.testing.assert_array_equal(opened.channels[0].array, source)


def test_real_acqstore_adapter_preserves_channel_selection(tmp_path: Path) -> None:
    path = tmp_path / 'adapter-channels.tif'
    source = np.arange(3 * 6 * 4, dtype=np.uint16).reshape(3, 6, 4)
    tifffile.imwrite(path, source, metadata={'axes': 'CYX'}, photometric='minisblack')

    opened = open_acquisition(str(path), channel_indices=[2, 0])

    assert [channel.index for channel in opened.channels] == [2, 0]
    np.testing.assert_array_equal(opened.channels[0].array, source[2])
    np.testing.assert_array_equal(opened.channels[1].array, source[0])
