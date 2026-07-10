"""Preprocessing helpers for diameter traces."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .models import DiameterFilterParams


def filter_diameter(
    diameter: pd.Series,
    params: DiameterFilterParams,
) -> pd.Series:
    """Filter a raw diameter trace without mutating the source series.

    Missing samples remain missing. For median filtering, each output sample is
    calculated from the centered finite values available inside the requested
    odd-width window.

    Args:
        diameter: Raw diameter values in physical units.
        params: Filtering configuration.

    Returns:
        New floating-point Series with the same index as ``diameter``.
    """
    params.validate()
    values = pd.to_numeric(diameter, errors="coerce").astype(float)
    if params.method == "none" or params.kernel_points == 1:
        return values.copy()

    filtered = values.rolling(
        window=params.kernel_points,
        center=True,
        min_periods=1,
    ).median()
    filtered[values.isna()] = np.nan
    return filtered
