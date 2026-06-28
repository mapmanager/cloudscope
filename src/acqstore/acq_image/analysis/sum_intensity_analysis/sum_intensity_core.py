"""Pure sum-intensity and peak-detection algorithms.

The functions in this module operate on NumPy arrays and plain Python values.
They intentionally do not import from :mod:`acqstore` so they can be tested and
reused independently of acquisition-image persistence or GUI code.

Axis convention for line-scan kymographs:

* axis 0 is time, with spacing ``physical_units[0]`` in seconds per line.
* axis 1 is space, with spacing ``physical_units[1]`` in microns per pixel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd
from scipy.ndimage import median_filter
from scipy.optimize import curve_fit

Polarity = Literal["positive", "negative"]
DetectionMethod = Literal["derivative_threshold", "absolute_threshold"]
FilterMethod = Literal["none", "median"]
DetrendMethod = Literal["none", "single_exponential"]

SUM_INTENSITY_TABLE_COLUMNS: tuple[str, ...] = (
    "time_index",
    "time_sec",
    "sum_intensity",
    "norm_sum_intensity",
    "filtered_norm_sum_intensity",
    "detection_signal",
    "d_norm_sum_intensity",
    "is_onset",
    "is_peak",
    "onset_index",
    "peak_id",
)


@dataclass(frozen=True, slots=True)
class LevelCrossing:
    """Peak level-crossing measurement at one amplitude fraction.

    Args:
        fraction: Requested fraction of peak amplitude, for example ``0.5``.
        value: Signal value corresponding to the requested fraction, or None
            when the crossing could not be evaluated.
        left_index: Interpolated rising-side index, or None when unavailable.
        right_index: Interpolated falling-side index, or None when unavailable.
        width: ``right_index - left_index`` in points, or None when either side
            is unavailable.
        status: Measurement status. ``"ok"`` means width is valid; other
            values identify expected scientific failure modes.
    """

    fraction: float
    value: float | None
    left_index: float | None
    right_index: float | None
    width: float | None
    status: str = "ok"

    def to_json_dict(self) -> dict[str, object]:
        """Return a JSON-serializable level-crossing record.

        Returns:
            Dictionary with stable keys for sidecar JSON storage.
        """
        return {
            "fraction": float(self.fraction),
            "value": _optional_float(self.value),
            "left_index": _optional_float(self.left_index),
            "right_index": _optional_float(self.right_index),
            "width": _optional_float(self.width),
            "status": str(self.status),
        }

    @classmethod
    def from_json_dict(cls, record: dict[str, Any]) -> LevelCrossing:
        """Create a crossing record from JSON-like data.

        Args:
            record: JSON dictionary created by :meth:`to_json_dict`.

        Returns:
            Parsed crossing record.
        """
        return cls(
            fraction=float(record["fraction"]),
            value=_optional_float(record.get("value")),
            left_index=_optional_float(record.get("left_index")),
            right_index=_optional_float(record.get("right_index")),
            width=_optional_float(record.get("width")),
            status=str(record.get("status", "ok")),
        )


@dataclass(frozen=True, slots=True)
class PeakEvent:
    """One detected sum-intensity peak/event.

    Args:
        peak_id: Stable one-based event identifier within one analysis run.
        status: Event-level status string.
        warnings: Event-local warnings for measurements that failed normally.
        onset_index: Time index where the detector accepted event onset.
        onset_time_sec: Onset time in seconds.
        onset_value: Detection-signal value at onset.
        peak_index: Refined peak index, or None when peak refinement failed.
        peak_time_sec: Peak time in seconds, or None when unavailable.
        peak_value: Detection-signal value at the peak, or None when
            unavailable.
        peak_amplitude: Peak amplitude relative to onset, or None when
            unavailable.
        detection_method: Detection method used to accept the onset.
        level_crossings: Requested fractional width measurements.
        onset_to_onset_interval_sec: Interval from the previous accepted onset,
            or None for the first event.
        peak_to_peak_interval_sec: Interval from the previous refined peak, or
            None when unavailable.
    """

    peak_id: int
    status: str
    warnings: tuple[str, ...]
    onset_index: int
    onset_time_sec: float
    onset_value: float
    peak_index: int | None
    peak_time_sec: float | None
    peak_value: float | None
    peak_amplitude: float | None
    detection_method: str
    level_crossings: tuple[LevelCrossing, ...] = field(default_factory=tuple)
    onset_to_onset_interval_sec: float | None = None
    peak_to_peak_interval_sec: float | None = None

    def to_json_dict(self) -> dict[str, object]:
        """Return a JSON-serializable event record.

        Returns:
            Dictionary with stable keys for sidecar JSON storage.
        """
        return {
            "peak_id": int(self.peak_id),
            "status": str(self.status),
            "warnings": list(self.warnings),
            "onset": {
                "index": int(self.onset_index),
                "time_sec": float(self.onset_time_sec),
                "value": float(self.onset_value),
            },
            "peak": {
                "index": None if self.peak_index is None else int(self.peak_index),
                "time_sec": _optional_float(self.peak_time_sec),
                "value": _optional_float(self.peak_value),
                "amplitude": _optional_float(self.peak_amplitude),
            },
            "detection_method": str(self.detection_method),
            "level_crossings": [crossing.to_json_dict() for crossing in self.level_crossings],
            "intervals": {
                "onset_to_onset_interval_sec": _optional_float(
                    self.onset_to_onset_interval_sec
                ),
                "peak_to_peak_interval_sec": _optional_float(
                    self.peak_to_peak_interval_sec
                ),
            },
        }

    @classmethod
    def from_json_dict(cls, record: dict[str, Any]) -> PeakEvent:
        """Create an event from JSON-like data.

        Args:
            record: JSON dictionary created by :meth:`to_json_dict`.

        Returns:
            Parsed event.
        """
        onset = dict(record["onset"])
        peak = dict(record["peak"])
        intervals = dict(record.get("intervals", {}))
        return cls(
            peak_id=int(record["peak_id"]),
            status=str(record["status"]),
            warnings=tuple(str(item) for item in record.get("warnings", ())),
            onset_index=int(onset["index"]),
            onset_time_sec=float(onset["time_sec"]),
            onset_value=float(onset["value"]),
            peak_index=None if peak.get("index") is None else int(peak["index"]),
            peak_time_sec=_optional_float(peak.get("time_sec")),
            peak_value=_optional_float(peak.get("value")),
            peak_amplitude=_optional_float(peak.get("amplitude")),
            detection_method=str(record["detection_method"]),
            level_crossings=tuple(
                LevelCrossing.from_json_dict(dict(item))
                for item in record.get("level_crossings", ())
            ),
            onset_to_onset_interval_sec=_optional_float(
                intervals.get("onset_to_onset_interval_sec")
            ),
            peak_to_peak_interval_sec=_optional_float(
                intervals.get("peak_to_peak_interval_sec")
            ),
        )


@dataclass(frozen=True, slots=True)
class SumIntensityCoreResult:
    """Pure sum-intensity analysis output.

    Args:
        summary: JSON-serializable summary including events and warnings.
        table: Per-timepoint result table.
        events: Parsed event objects mirrored in ``summary``.
    """

    summary: dict[str, Any]
    table: pd.DataFrame
    events: tuple[PeakEvent, ...]


def run_sum_intensity(
    image: np.ndarray,
    *,
    detection_params: dict[str, Any],
    physical_units: tuple[float, float],
) -> SumIntensityCoreResult:
    """Run sum-intensity analysis on one ROI-cropped kymograph.

    Args:
        image: Two-dimensional image with shape ``(time, space)``.
        detection_params: Flat detection parameter mapping.
        physical_units: ``(seconds_per_line, um_per_pixel)``. Only seconds per
            line is used by this first-pass analysis; the spatial unit is kept
            as explicit input for consistency with other kymograph analyses.

    Returns:
        Summary, table, and parsed peak events.

    Raises:
        ValueError: If image, physical units, or detection parameters are
            invalid.
    """
    arr = np.asarray(image, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"image must be 2D (time, space), got shape={arr.shape!r}")
    if arr.shape[0] < 1 or arr.shape[1] < 1:
        raise ValueError(f"image must be non-empty in both axes, got shape={arr.shape!r}")

    seconds_per_line, um_per_pixel = (float(physical_units[0]), float(physical_units[1]))
    if seconds_per_line <= 0 or um_per_pixel <= 0:
        raise ValueError("physical_units must be strictly positive")

    params = _validated_detection_params(detection_params)
    warnings: list[str] = []
    errors: list[str] = []

    n_time, n_space = arr.shape
    time_index = np.arange(n_time, dtype=int)
    time_sec = time_index.astype(float) * seconds_per_line

    row_sum = np.sum(arr, axis=1, dtype=float)
    sum_intensity = _rolling_mean_clipped(row_sum, radius=int(params["window_radius_points"]))
    norm_sum_intensity = sum_intensity / float(n_space)

    filtered_norm = _filter_trace(
        norm_sum_intensity,
        filter_method=str(params["filter_method"]),
        median_kernel_points=int(params["median_filter_kernel_points"]),
        warnings=warnings,
    )
    detection_signal = _detrend_trace(
        filtered_norm,
        time_sec=time_sec,
        detrend_method=str(params["detrend_method"]),
        warnings=warnings,
        errors=errors,
    )
    d_norm_sum_intensity = np.gradient(detection_signal, time_sec)

    onset_indices = _detect_onsets(
        detection_signal=detection_signal,
        derivative_signal=d_norm_sum_intensity,
        method=str(params["detection_method"]),
        polarity=str(params["polarity"]),
        absolute_threshold=float(params["absolute_threshold"]),
        derivative_threshold=float(params["derivative_threshold"]),
    )
    refractory_points = _duration_ms_to_points(
        float(params["refractory_period_ms"]), seconds_per_line
    )
    accepted_onsets = _apply_refractory(onset_indices, refractory_points=refractory_points)

    peak_search_window_points = _duration_ms_to_points(
        float(params["peak_search_window_ms"]), seconds_per_line
    )
    level_fractions = _parse_level_fractions(str(params["level_fractions"]))
    events = _build_events(
        detection_signal=detection_signal,
        time_sec=time_sec,
        onset_indices=accepted_onsets,
        detection_method=str(params["detection_method"]),
        polarity=str(params["polarity"]),
        peak_search_window_points=peak_search_window_points,
        level_fractions=level_fractions,
    )

    table = _build_table(
        time_index=time_index,
        time_sec=time_sec,
        sum_intensity=sum_intensity,
        norm_sum_intensity=norm_sum_intensity,
        filtered_norm_sum_intensity=filtered_norm,
        detection_signal=detection_signal,
        d_norm_sum_intensity=d_norm_sum_intensity,
        events=events,
    )
    summary = _build_summary(
        table=table,
        events=events,
        warnings=warnings,
        errors=errors,
        params=params,
        seconds_per_line=seconds_per_line,
        n_space=n_space,
    )
    return SumIntensityCoreResult(summary=summary, table=table, events=events)


def _validated_detection_params(params: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize core detection parameters.

    Args:
        params: Flat detection parameter mapping.

    Returns:
        Normalized copy of ``params``.

    Raises:
        ValueError: If any parameter value is invalid.
    """
    normalized = dict(params)
    if int(normalized["window_radius_points"]) < 0:
        raise ValueError("window_radius_points must be >= 0")
    if normalized["filter_method"] not in {"none", "median"}:
        raise ValueError("filter_method must be 'none' or 'median'")
    kernel = int(normalized["median_filter_kernel_points"])
    if kernel < 1:
        raise ValueError("median_filter_kernel_points must be >= 1")
    if normalized["detrend_method"] not in {"none", "single_exponential"}:
        raise ValueError("detrend_method must be 'none' or 'single_exponential'")
    if normalized["detection_method"] not in {"derivative_threshold", "absolute_threshold"}:
        raise ValueError("detection_method must be 'derivative_threshold' or 'absolute_threshold'")
    if normalized["polarity"] not in {"positive", "negative"}:
        raise ValueError("polarity must be 'positive' or 'negative'")
    if float(normalized["refractory_period_ms"]) < 0:
        raise ValueError("refractory_period_ms must be >= 0")
    if float(normalized["peak_search_window_ms"]) <= 0:
        raise ValueError("peak_search_window_ms must be > 0")
    _parse_level_fractions(str(normalized["level_fractions"]))
    return normalized


def _rolling_mean_clipped(values: np.ndarray, *, radius: int) -> np.ndarray:
    """Return clipped-edge rolling mean for a one-dimensional trace.

    Args:
        values: One-dimensional input trace.
        radius: Number of samples on each side of the center point.

    Returns:
        Rolling mean with the same length as ``values``.
    """
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        raise ValueError("values must be 1D")
    if radius < 0:
        raise ValueError("radius must be >= 0")
    if radius == 0 or arr.size == 0:
        return arr.copy()

    indices = np.arange(arr.size)
    starts = np.maximum(0, indices - radius)
    stops = np.minimum(arr.size, indices + radius + 1)
    cumsum = np.concatenate(([0.0], np.cumsum(arr, dtype=float)))
    totals = cumsum[stops] - cumsum[starts]
    counts = stops - starts
    return totals / counts.astype(float)


def _filter_trace(
    values: np.ndarray,
    *,
    filter_method: str,
    median_kernel_points: int,
    warnings: list[str],
) -> np.ndarray:
    """Filter a one-dimensional normalized intensity trace.

    Args:
        values: Trace to filter.
        filter_method: ``"none"`` or ``"median"``.
        median_kernel_points: Median-filter kernel size in points.
        warnings: Mutable list receiving non-fatal warnings.

    Returns:
        Filtered trace.
    """
    if filter_method == "none":
        return np.asarray(values, dtype=float).copy()

    kernel = int(median_kernel_points)
    if kernel <= 1:
        return np.asarray(values, dtype=float).copy()
    if kernel % 2 == 0:
        kernel += 1
        warnings.append(
            f"median_filter_kernel_points was even; using {kernel} points instead"
        )
    return np.asarray(median_filter(values, size=kernel, mode="nearest"), dtype=float)


def _single_exponential(time_sec: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """Evaluate ``a * exp(-b * t) + c``.

    Args:
        time_sec: Time axis in seconds.
        a: Exponential amplitude.
        b: Exponential decay rate.
        c: Constant offset.

    Returns:
        Exponential trace.
    """
    return a * np.exp(-b * time_sec) + c


def _detrend_trace(
    values: np.ndarray,
    *,
    time_sec: np.ndarray,
    detrend_method: str,
    warnings: list[str],
    errors: list[str],
) -> np.ndarray:
    """Optionally remove a slow trend from a trace.

    Args:
        values: Input trace after filtering.
        time_sec: Time axis in seconds.
        detrend_method: ``"none"`` or ``"single_exponential"``.
        warnings: Mutable list receiving non-fatal warnings.
        errors: Mutable list receiving algorithm-step failures.

    Returns:
        Detrended trace, or the original values when detrending is disabled or
        expected fitting failure occurs.
    """
    trace = np.asarray(values, dtype=float)
    if detrend_method == "none":
        return trace.copy()
    if trace.size < 4 or np.allclose(trace, trace[0]):
        warnings.append("single_exponential_detrend skipped; trace is too short or constant")
        return trace.copy()

    try:
        amplitude_guess = float(trace[0] - trace[-1])
        decay_guess = 1.0 / max(float(time_sec[-1] - time_sec[0]), np.finfo(float).eps)
        offset_guess = float(trace[-1])
        params, _cov = curve_fit(
            _single_exponential,
            time_sec,
            trace,
            p0=(amplitude_guess, decay_guess, offset_guess),
            maxfev=10_000,
        )
        fitted = _single_exponential(time_sec, *params)
        return trace - fitted + float(fitted[0])
    except (RuntimeError, ValueError, FloatingPointError, OverflowError) as exc:
        message = (
            "single_exponential_detrend failed; using filtered_norm_sum_intensity "
            f"instead ({type(exc).__name__}: {exc})"
        )
        errors.append(message)
        return trace.copy()


def _detect_onsets(
    *,
    detection_signal: np.ndarray,
    derivative_signal: np.ndarray,
    method: str,
    polarity: str,
    absolute_threshold: float,
    derivative_threshold: float,
) -> list[int]:
    """Detect candidate onset indices before refractory filtering.

    Args:
        detection_signal: Trace used for absolute-threshold detection.
        derivative_signal: Trace derivative used for derivative-threshold
            detection.
        method: Detection method name.
        polarity: ``"positive"`` or ``"negative"``.
        absolute_threshold: Absolute signal threshold.
        derivative_threshold: Derivative threshold in signal units per second.

    Returns:
        Candidate onset indices.
    """
    trace = derivative_signal if method == "derivative_threshold" else detection_signal
    threshold = derivative_threshold if method == "derivative_threshold" else absolute_threshold
    if polarity == "negative":
        above = trace <= -abs(float(threshold))
    else:
        above = trace >= float(threshold)
    if above.size == 0:
        return []
    starts = np.flatnonzero(above & np.concatenate(([True], ~above[:-1])))
    return [int(index) for index in starts]


def _apply_refractory(indices: list[int], *, refractory_points: int) -> list[int]:
    """Reject candidate onsets inside the onset-to-onset refractory period.

    Args:
        indices: Candidate onset indices in ascending order.
        refractory_points: Minimum accepted onset-to-onset spacing in points.

    Returns:
        Accepted onset indices.
    """
    accepted: list[int] = []
    last_accepted: int | None = None
    for index in indices:
        if last_accepted is None or index > last_accepted + refractory_points:
            accepted.append(index)
            last_accepted = index
    return accepted


def _duration_ms_to_points(duration_ms: float, seconds_per_line: float) -> int:
    """Convert a duration in milliseconds to nearest sample count.

    Args:
        duration_ms: Duration in milliseconds.
        seconds_per_line: Sampling interval in seconds.

    Returns:
        Non-negative sample count.
    """
    return max(0, int(round((duration_ms / 1000.0) / seconds_per_line)))


def _parse_level_fractions(value: str) -> tuple[float, ...]:
    """Parse comma-separated level fractions.

    Args:
        value: Comma-separated fractions such as ``"0.1,0.5,0.9"``.

    Returns:
        Fractions as floats.

    Raises:
        ValueError: If no valid fractions are supplied or a value is outside
            the open interval ``(0, 1)``.
    """
    fractions: list[float] = []
    for part in value.split(","):
        stripped = part.strip()
        if not stripped:
            continue
        fraction = float(stripped)
        if fraction <= 0.0 or fraction >= 1.0:
            raise ValueError("level_fractions values must be between 0 and 1")
        fractions.append(fraction)
    if not fractions:
        raise ValueError("level_fractions must include at least one fraction")
    return tuple(fractions)


def _build_events(
    *,
    detection_signal: np.ndarray,
    time_sec: np.ndarray,
    onset_indices: list[int],
    detection_method: str,
    polarity: str,
    peak_search_window_points: int,
    level_fractions: tuple[float, ...],
) -> tuple[PeakEvent, ...]:
    """Build event records from accepted onsets.

    Args:
        detection_signal: Trace used for feature extraction.
        time_sec: Time axis in seconds.
        onset_indices: Accepted onset indices.
        detection_method: Detection method used for onset detection.
        polarity: Peak polarity.
        peak_search_window_points: Forward peak search window in points.
        level_fractions: Requested amplitude fractions for width measures.

    Returns:
        Peak events with interval statistics.
    """
    events: list[PeakEvent] = []
    previous_onset_time: float | None = None
    previous_peak_time: float | None = None
    for zero_based, onset_index in enumerate(onset_indices):
        next_onset = onset_indices[zero_based + 1] if zero_based + 1 < len(onset_indices) else None
        event = _build_one_event(
            detection_signal=detection_signal,
            time_sec=time_sec,
            peak_id=zero_based + 1,
            onset_index=onset_index,
            next_onset_index=next_onset,
            detection_method=detection_method,
            polarity=polarity,
            peak_search_window_points=peak_search_window_points,
            level_fractions=level_fractions,
            previous_onset_time=previous_onset_time,
            previous_peak_time=previous_peak_time,
        )
        events.append(event)
        previous_onset_time = event.onset_time_sec
        if event.peak_time_sec is not None:
            previous_peak_time = event.peak_time_sec
    return tuple(events)


def _build_one_event(
    *,
    detection_signal: np.ndarray,
    time_sec: np.ndarray,
    peak_id: int,
    onset_index: int,
    next_onset_index: int | None,
    detection_method: str,
    polarity: str,
    peak_search_window_points: int,
    level_fractions: tuple[float, ...],
    previous_onset_time: float | None,
    previous_peak_time: float | None,
) -> PeakEvent:
    """Build one event record.

    Args:
        detection_signal: Trace used for feature extraction.
        time_sec: Time axis in seconds.
        peak_id: One-based event identifier.
        onset_index: Accepted onset index.
        next_onset_index: Next accepted onset index, if available.
        detection_method: Detection method name.
        polarity: Peak polarity.
        peak_search_window_points: Forward peak search window in points.
        level_fractions: Requested amplitude fractions.
        previous_onset_time: Previous event onset time for interval stats.
        previous_peak_time: Previous event peak time for interval stats.

    Returns:
        Event record.
    """
    n_time = detection_signal.size
    onset_value = float(detection_signal[onset_index])
    onset_time = float(time_sec[onset_index])
    search_stop = min(n_time, onset_index + max(1, peak_search_window_points) + 1)
    search_values = detection_signal[onset_index:search_stop]
    warnings: list[str] = []

    if search_values.size == 0:
        warnings.append("No samples available for peak refinement")
        peak_index = None
        peak_value = None
        peak_time = None
        amplitude = None
        crossings = tuple(
            LevelCrossing(
                fraction=fraction,
                value=None,
                left_index=None,
                right_index=None,
                width=None,
                status="peak_not_found",
            )
            for fraction in level_fractions
        )
        status = "peak_not_found"
    else:
        local_index = int(np.argmin(search_values) if polarity == "negative" else np.argmax(search_values))
        peak_index = onset_index + local_index
        peak_value = float(detection_signal[peak_index])
        peak_time = float(time_sec[peak_index])
        amplitude = float(onset_value - peak_value if polarity == "negative" else peak_value - onset_value)
        if amplitude <= 0:
            warnings.append("Peak amplitude was not positive after refinement")
            status = "non_positive_amplitude"
        else:
            status = "ok"
        crossings = tuple(
            _measure_level_crossing(
                detection_signal=detection_signal,
                onset_index=onset_index,
                peak_index=peak_index,
                next_onset_index=next_onset_index,
                fraction=fraction,
                onset_value=onset_value,
                peak_value=peak_value,
                polarity=polarity,
            )
            for fraction in level_fractions
        )

    onset_interval = None if previous_onset_time is None else onset_time - previous_onset_time
    peak_interval = (
        None
        if previous_peak_time is None or peak_time is None
        else peak_time - previous_peak_time
    )
    return PeakEvent(
        peak_id=peak_id,
        status=status,
        warnings=tuple(warnings),
        onset_index=onset_index,
        onset_time_sec=onset_time,
        onset_value=onset_value,
        peak_index=peak_index,
        peak_time_sec=peak_time,
        peak_value=peak_value,
        peak_amplitude=amplitude,
        detection_method=detection_method,
        level_crossings=crossings,
        onset_to_onset_interval_sec=onset_interval,
        peak_to_peak_interval_sec=peak_interval,
    )


def _measure_level_crossing(
    *,
    detection_signal: np.ndarray,
    onset_index: int,
    peak_index: int,
    next_onset_index: int | None,
    fraction: float,
    onset_value: float,
    peak_value: float,
    polarity: str,
) -> LevelCrossing:
    """Measure one peak width fraction.

    Args:
        detection_signal: Trace used for feature extraction.
        onset_index: Event onset index.
        peak_index: Event peak index.
        next_onset_index: Next event onset index, if available.
        fraction: Requested amplitude fraction.
        onset_value: Signal value at onset.
        peak_value: Signal value at peak.
        polarity: Peak polarity.

    Returns:
        Level-crossing measurement with local failure status when needed.
    """
    level_value = onset_value + float(fraction) * (peak_value - onset_value)
    left = _find_crossing(
        detection_signal,
        start=onset_index,
        stop=peak_index,
        level_value=level_value,
        polarity=polarity,
        direction="rising",
    )
    right_stop = next_onset_index if next_onset_index is not None else detection_signal.size - 1
    right = _find_crossing(
        detection_signal,
        start=peak_index,
        stop=right_stop,
        level_value=level_value,
        polarity=polarity,
        direction="falling",
    )
    if left is not None and right is not None:
        return LevelCrossing(
            fraction=float(fraction),
            value=float(level_value),
            left_index=float(left),
            right_index=float(right),
            width=float(right - left),
            status="ok",
        )
    if left is None and right is None:
        status = "both_not_found"
    elif left is None:
        status = "left_not_found"
    else:
        status = "right_not_found"
    return LevelCrossing(
        fraction=float(fraction),
        value=float(level_value),
        left_index=_optional_float(left),
        right_index=_optional_float(right),
        width=None,
        status=status,
    )


def _find_crossing(
    values: np.ndarray,
    *,
    start: int,
    stop: int,
    level_value: float,
    polarity: str,
    direction: Literal["rising", "falling"],
) -> float | None:
    """Find an interpolated level crossing.

    Args:
        values: One-dimensional trace.
        start: First index to search.
        stop: Last index to search.
        level_value: Requested crossing value.
        polarity: Peak polarity.
        direction: Rising-side or falling-side crossing.

    Returns:
        Interpolated crossing index, or None when unavailable.
    """
    if stop <= start:
        return None
    indices = range(start, stop)
    for i in indices:
        y0 = float(values[i])
        y1 = float(values[i + 1])
        if _segment_crosses(y0, y1, level_value=level_value, polarity=polarity, direction=direction):
            if y1 == y0:
                return float(i)
            return float(i) + (float(level_value) - y0) / (y1 - y0)
    return None


def _segment_crosses(
    y0: float,
    y1: float,
    *,
    level_value: float,
    polarity: str,
    direction: Literal["rising", "falling"],
) -> bool:
    """Return whether one segment crosses a requested level.

    Args:
        y0: Segment start value.
        y1: Segment end value.
        level_value: Requested crossing value.
        polarity: Peak polarity.
        direction: Rising-side or falling-side crossing.

    Returns:
        True when the segment crosses the level in the expected direction.
    """
    if polarity == "negative":
        if direction == "rising":
            return y0 >= level_value and y1 <= level_value
        return y0 <= level_value and y1 >= level_value
    if direction == "rising":
        return y0 <= level_value and y1 >= level_value
    return y0 >= level_value and y1 <= level_value


def _build_table(
    *,
    time_index: np.ndarray,
    time_sec: np.ndarray,
    sum_intensity: np.ndarray,
    norm_sum_intensity: np.ndarray,
    filtered_norm_sum_intensity: np.ndarray,
    detection_signal: np.ndarray,
    d_norm_sum_intensity: np.ndarray,
    events: tuple[PeakEvent, ...],
) -> pd.DataFrame:
    """Build the per-timepoint result table.

    Args:
        time_index: Integer time indices.
        time_sec: Time in seconds.
        sum_intensity: Raw or windowed row-sum intensity.
        norm_sum_intensity: Sum intensity divided by spatial pixel count.
        filtered_norm_sum_intensity: Filtered normalized trace.
        detection_signal: Final trace used for detection.
        d_norm_sum_intensity: Derivative of ``detection_signal``.
        events: Detected peak events.

    Returns:
        Result table with stable columns.
    """
    table = pd.DataFrame(
        {
            "time_index": time_index.astype(int),
            "time_sec": time_sec.astype(float),
            "sum_intensity": sum_intensity.astype(float),
            "norm_sum_intensity": norm_sum_intensity.astype(float),
            "filtered_norm_sum_intensity": filtered_norm_sum_intensity.astype(float),
            "detection_signal": detection_signal.astype(float),
            "d_norm_sum_intensity": d_norm_sum_intensity.astype(float),
            "is_onset": np.zeros(time_index.size, dtype=bool),
            "is_peak": np.zeros(time_index.size, dtype=bool),
            "onset_index": np.full(time_index.size, np.nan),
            "peak_id": np.full(time_index.size, np.nan),
        },
        columns=SUM_INTENSITY_TABLE_COLUMNS,
    )
    for event in events:
        table.loc[event.onset_index, "is_onset"] = True
        table.loc[event.onset_index, "onset_index"] = int(event.onset_index)
        table.loc[event.onset_index, "peak_id"] = int(event.peak_id)
        if event.peak_index is not None:
            table.loc[event.peak_index, "is_peak"] = True
            table.loc[event.peak_index, "onset_index"] = int(event.onset_index)
            table.loc[event.peak_index, "peak_id"] = int(event.peak_id)
    return table


def _build_summary(
    *,
    table: pd.DataFrame,
    events: tuple[PeakEvent, ...],
    warnings: list[str],
    errors: list[str],
    params: dict[str, Any],
    seconds_per_line: float,
    n_space: int,
) -> dict[str, Any]:
    """Build the JSON summary for one analysis run.

    Args:
        table: Per-timepoint result table.
        events: Detected peak events.
        warnings: Analysis-level warnings.
        errors: Analysis-level non-fatal errors.
        params: Validated detection parameters.
        seconds_per_line: Time spacing in seconds.
        n_space: Number of spatial pixels in the ROI image.

    Returns:
        JSON-serializable summary dictionary.
    """
    amplitudes = [event.peak_amplitude for event in events if event.peak_amplitude is not None]
    status = "ok"
    if errors:
        status = "ok_with_errors"
    elif warnings or any(event.status != "ok" for event in events):
        status = "ok_with_warnings"
    return {
        "status": status,
        "num_timepoints": int(len(table)),
        "num_peaks": int(len(events)),
        "num_space_pixels": int(n_space),
        "seconds_per_line": float(seconds_per_line),
        "peak_amplitude_mean": _nanmean_or_none(amplitudes),
        "peak_amplitude_median": _nanmedian_or_none(amplitudes),
        "warnings": list(warnings),
        "errors": list(errors),
        "detrend_method": str(params["detrend_method"]),
        "detection_method": str(params["detection_method"]),
        "events": [event.to_json_dict() for event in events],
    }


def _nanmean_or_none(values: list[float]) -> float | None:
    """Return mean or None for empty input.

    Args:
        values: Numeric values.

    Returns:
        Mean, or None when no values exist.
    """
    if not values:
        return None
    return float(np.nanmean(np.asarray(values, dtype=float)))


def _nanmedian_or_none(values: list[float]) -> float | None:
    """Return median or None for empty input.

    Args:
        values: Numeric values.

    Returns:
        Median, or None when no values exist.
    """
    if not values:
        return None
    return float(np.nanmedian(np.asarray(values, dtype=float)))


def _optional_float(value: object) -> float | None:
    """Return a float or None.

    Args:
        value: Numeric value or None-like value.

    Returns:
        Float value, or None when input is None or NaN.
    """
    if value is None:
        return None
    numeric = float(value)
    if np.isnan(numeric):
        return None
    return numeric
