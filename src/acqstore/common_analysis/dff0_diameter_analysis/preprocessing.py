"""Signal preprocessing for triggered-event analysis."""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.signal import medfilt, savgol_filter

from .models import DiameterFilterParams, SignalFilterMethod, TriggeredEventParams


def filter_signal(signal: np.ndarray, params: TriggeredEventParams) -> np.ndarray:
    """Return a filtered copy of one signal.

    Args:
        signal: One-dimensional numeric signal.
        params: Triggered-event parameters selecting the filter.

    Returns:
        Filtered floating-point array.
    """
    values = np.asarray(signal, dtype=float)
    if values.ndim != 1:
        raise ValueError("signal must be one-dimensional")
    if np.isnan(values).any():
        raise ValueError("signal contains NaN values; interpolation is not implicit")

    if params.filter_method is SignalFilterMethod.NONE:
        return values.copy()
    if params.filter_method is SignalFilterMethod.MEDIAN:
        kernel = params.median_kernel_points
        if kernel < 1 or kernel % 2 == 0:
            raise ValueError("median_kernel_points must be a positive odd integer")
        return medfilt(values, kernel_size=kernel)
    if params.filter_method is SignalFilterMethod.SAVGOL:
        window = params.savgol_window_points
        if window < 3 or window % 2 == 0:
            raise ValueError("savgol_window_points must be an odd integer >= 3")
        if params.savgol_polyorder < 0 or params.savgol_polyorder >= window:
            raise ValueError("savgol_polyorder must be >= 0 and less than window")
        if window > len(values):
            raise ValueError("savgol_window_points cannot exceed signal length")
        return savgol_filter(values, window_length=window, polyorder=params.savgol_polyorder)
    raise ValueError(f"Unsupported filter method: {params.filter_method}")


def filter_diameter(series: pd.Series, params: DiameterFilterParams) -> pd.Series:
    """Compatibility wrapper used by the sidecar loader."""
    if params.method == "none":
        return pd.to_numeric(series, errors="coerce").astype(float)
    values = pd.to_numeric(series, errors="coerce").to_numpy(dtype=float)
    trigger_params = TriggeredEventParams(
        filter_method=SignalFilterMethod(params.method),
        median_kernel_points=params.kernel_points,
    )
    return pd.Series(filter_signal(values, trigger_params), index=series.index)
