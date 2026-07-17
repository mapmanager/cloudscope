"""Binary transport encoding for AcqStore Server API v2."""

from __future__ import annotations

import numpy as np


def encode_raw_f32_le(array: np.ndarray) -> bytes:
    """Encode a two-dimensional array as contiguous row-major little-endian float32."""
    plane = np.asarray(array)
    if plane.ndim != 2:
        raise ValueError(f'Expected a 2-D plane, got shape {plane.shape}')
    encoded = np.asarray(plane, dtype='<f4', order='C')
    return encoded.tobytes(order='C')
