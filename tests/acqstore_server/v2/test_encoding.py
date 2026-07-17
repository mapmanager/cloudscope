"""Tests for API v2 raw float32 transport encoding."""

from __future__ import annotations

import numpy as np
import pytest

from acqstore_server.v2.encoding import encode_raw_f32_le


def test_encode_raw_f32_le_is_row_major_little_endian() -> None:
    source = np.array([[1, 2], [3, 4]], dtype=np.uint16)
    payload = encode_raw_f32_le(source)
    decoded = np.frombuffer(payload, dtype='<f4').reshape(2, 2)
    np.testing.assert_array_equal(decoded, source.astype(np.float32))
    assert len(payload) == source.size * 4


def test_encode_rejects_non_2d_array() -> None:
    with pytest.raises(ValueError):
        encode_raw_f32_le(np.zeros((2, 3, 4), dtype=np.uint16))
