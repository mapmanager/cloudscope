"""Tests for pure sum-intensity analysis core."""

from __future__ import annotations

import numpy as np
import pytest

from acqstore.acq_image.analysis.sum_intensity_analysis import sum_intensity_core
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_core import (
    PeakEvent,
    SUM_INTENSITY_TABLE_COLUMNS,
    run_sum_intensity,
)


def _params(**overrides: object) -> dict[str, object]:
    """Return complete detection params for core tests.

    Args:
        overrides: Parameter values to override.

    Returns:
        Detection parameter mapping.
    """
    params: dict[str, object] = {
        "window_radius_points": 0,
        "filter_method": "none",
        "median_filter_kernel_points": 3,
        "detrend_method": "none",
        "detection_method": "derivative_threshold",
        "polarity": "positive",
        "absolute_threshold": 1.0,
        "derivative_threshold": 500.0,
        "refractory_period_ms": 2.0,
        "peak_search_window_ms": 10.0,
        "level_fractions": "0.1,0.2,0.5,0.8,0.9",
    }
    params.update(overrides)
    return params


def test_window_radius_uses_vectorized_row_sum_equivalence() -> None:
    """Window radius should rolling-average row sums before normalization."""
    image = np.array(
        [
            [0.0, 0.0],
            [10.0, 10.0],
            [20.0, 20.0],
            [30.0, 30.0],
        ]
    )
    result = run_sum_intensity(
        image,
        detection_params=_params(window_radius_points=1, detection_method="absolute_threshold", absolute_threshold=999.0),
        physical_units=(0.001, 0.25),
    )

    assert result.table.columns.tolist() == list(SUM_INTENSITY_TABLE_COLUMNS)
    assert result.table["sum_intensity"].tolist() == [10.0, 20.0, 40.0, 50.0]
    assert result.table["norm_sum_intensity"].tolist() == [5.0, 10.0, 20.0, 25.0]
    assert result.summary["num_space_pixels"] == 2


def test_derivative_threshold_detects_onset_and_refines_peak() -> None:
    """Derivative detection should produce onset and peak event records."""
    trace = np.array([0, 0, 1, 2, 5, 3, 1, 0, 0], dtype=float)
    image = np.repeat(trace[:, np.newaxis], 4, axis=1)

    result = run_sum_intensity(
        image,
        detection_params=_params(derivative_threshold=500.0, peak_search_window_ms=5.0),
        physical_units=(0.001, 0.25),
    )

    events = result.events
    assert len(events) == 1
    assert events[0].onset_index == 1
    assert events[0].peak_index == 4
    assert events[0].peak_value == 5.0
    assert bool(result.table.loc[events[0].onset_index, "is_onset"]) is True
    assert bool(result.table.loc[events[0].peak_index, "is_peak"]) is True


def test_level_crossing_failure_is_recorded_as_data() -> None:
    """Missing decay side of a peak should be stored as crossing status."""
    trace = np.array([0, 0, 1, 2, 3, 4, 5], dtype=float)
    image = np.repeat(trace[:, np.newaxis], 3, axis=1)

    result = run_sum_intensity(
        image,
        detection_params=_params(derivative_threshold=500.0, peak_search_window_ms=10.0),
        physical_units=(0.001, 0.25),
    )

    event = result.events[0]
    assert event.status == "ok"
    assert any(crossing.status == "right_not_found" for crossing in event.level_crossings)
    assert result.summary["events"][0]["level_crossings"][0]["status"] in {
        "ok",
        "right_not_found",
    }


def test_detrend_failure_falls_back_without_runtime_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """curve_fit failure should be encoded in summary errors and continue."""

    def _raise_runtime_error(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("synthetic fit failure")

    monkeypatch.setattr(sum_intensity_core, "curve_fit", _raise_runtime_error)
    trace = np.array([10, 9, 8, 7, 6, 8, 6, 5], dtype=float)
    image = np.repeat(trace[:, np.newaxis], 2, axis=1)

    result = run_sum_intensity(
        image,
        detection_params=_params(
            detrend_method="single_exponential",
            detection_method="absolute_threshold",
            absolute_threshold=7.5,
        ),
        physical_units=(0.001, 0.25),
    )

    assert result.summary["status"] == "ok_with_errors"
    assert result.summary["errors"]
    assert "single_exponential_detrend failed" in result.summary["errors"][0]
    np.testing.assert_allclose(
        result.table["detection_signal"].to_numpy(),
        result.table["filtered_norm_sum_intensity"].to_numpy(),
    )


def test_peak_event_json_round_trip() -> None:
    """PeakEvent JSON abstraction should round-trip without GUI parsing."""
    trace = np.array([0, 0, 1, 3, 1, 0], dtype=float)
    image = np.repeat(trace[:, np.newaxis], 2, axis=1)
    result = run_sum_intensity(
        image,
        detection_params=_params(derivative_threshold=500.0, peak_search_window_ms=5.0),
        physical_units=(0.001, 0.25),
    )

    record = result.events[0].to_json_dict()
    parsed = PeakEvent.from_json_dict(record)

    assert parsed.peak_id == result.events[0].peak_id
    assert parsed.onset_index == result.events[0].onset_index
    assert parsed.peak_index == result.events[0].peak_index
    assert len(parsed.level_crossings) == 5
