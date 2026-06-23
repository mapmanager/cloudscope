"""Tests for OIR reference-image loader helpers."""

from __future__ import annotations

import numpy as np

from acqstore.acq_image.file_loaders.oir_file_loader import _reference_snapshot_from_oir_reference


class _FakeOirReference:
    """Minimal OIR reference object used by ``_reference_snapshot_from_oir_reference``."""

    dims = ("C", "Y", "X")
    sizes = {"C": 1, "Y": 8, "X": 9}
    line_roi = (1.0, 2.0, 7.0, 6.0)
    coord_units = {"X": "um", "Y": "um"}
    coord_scales = {"X": 0.25, "Y": 0.5}
    coords = {}

    def asarray(self) -> np.ndarray:
        """Return a fake channel-first OIR reference image."""
        return np.zeros((1, 8, 9), dtype=np.uint8)


def test_oir_reference_image_populates_scan_path_from_line_roi() -> None:
    """OIR explicit line ROI endpoints are exposed through ReferenceImage scan path."""
    reference = _reference_snapshot_from_oir_reference(_FakeOirReference())

    assert reference.line_roi == (1.0, 2.0, 7.0, 6.0)
    assert reference.has_scan_path() is True
    scan_path = reference.get_scan_path()
    assert scan_path is not None
    np.testing.assert_array_equal(scan_path, np.asarray([[1.0, 7.0], [2.0, 6.0]]))
    x_pixels, y_pixels = reference.get_scan_path_plot()
    np.testing.assert_array_equal(x_pixels, np.asarray([1.0, 7.0]))
    np.testing.assert_array_equal(y_pixels, np.asarray([2.0, 6.0]))
