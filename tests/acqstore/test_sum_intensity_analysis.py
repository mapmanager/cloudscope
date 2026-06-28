"""Tests for SumIntensityAnalysis BaseAnalysis wrapper."""

from __future__ import annotations

import numpy as np

from acqstore.acq_image.acq_analysis_set import AcqAnalysisSet
from acqstore.acq_image.analysis.model import AnalysisKey
from acqstore.acq_image.analysis.registry import get_analysis_registry
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_analysis import (
    SumIntensityAnalysis,
)


class FakeProvider:
    """Fake sum-intensity analysis data provider."""

    def get_roi_image(self, channel: int, roi_id: int) -> np.ndarray:
        """Return synthetic ROI kymograph data.

        Args:
            channel: Channel index.
            roi_id: ROI identifier.

        Returns:
            Synthetic two-dimensional ROI image.
        """
        _ = channel, roi_id
        trace = np.array([0, 0, 1, 2, 5, 2, 0, 0], dtype=float)
        return np.repeat(trace[:, np.newaxis], 4, axis=1)

    def get_image_physical_units(self) -> tuple[float, float]:
        """Return synthetic physical units.

        Returns:
            ``(seconds_per_line, um_per_pixel)``.
        """
        return (0.001, 0.25)


def _params() -> dict[str, object]:
    """Return deterministic wrapper-test detection params.

    Returns:
        Detection parameter mapping.
    """
    return {
        "filter_method": "none",
        "detrend_method": "none",
        "derivative_threshold": 500.0,
        "peak_search_window_ms": 5.0,
    }


def test_sum_intensity_schema_defaults_and_detection_method() -> None:
    """SumIntensityAnalysis should expose documented detection defaults."""
    analysis = SumIntensityAnalysis(channel=0, roi_id=1)

    assert analysis.detection_params["detection_method"] == "derivative_threshold"
    assert analysis.detection_params["detrend_method"] == "single_exponential"
    assert analysis.detection_params["filter_method"] == "median"
    assert SumIntensityAnalysis.exclusive_group is None


def test_sum_intensity_analysis_run_populates_result() -> None:
    """SumIntensityAnalysis should populate table, summary, plot, and events."""
    analysis = SumIntensityAnalysis(channel=0, roi_id=1, detection_params=_params())
    analysis.run(FakeProvider())

    assert analysis.is_dirty()
    assert "norm_sum_intensity" in analysis.get_table_columns()
    assert analysis.result.summary["num_peaks"] == 1
    assert len(analysis.get_peak_events()) == 1
    plot = analysis.get_plot_data()
    assert plot is not None
    assert plot.x_label == "Time (s)"
    assert plot.series_name == "Sum intensity"


def test_analysis_set_runs_sum_intensity() -> None:
    """AcqAnalysisSet should orchestrate SumIntensityAnalysis."""
    analysis_set = AcqAnalysisSet("fake.tif", data_provider=FakeProvider())
    analysis = analysis_set.create(
        "sum_intensity",
        channel=0,
        roi_id=1,
        detection_params=_params(),
    )
    assert isinstance(analysis, SumIntensityAnalysis)
    analysis_set.run_analysis(AnalysisKey("sum_intensity", 0, 1))
    assert analysis_set.is_dirty()
    assert analysis.get_column("time_sec")


def test_sum_intensity_is_registered_builtin() -> None:
    """Analysis registry should include sum_intensity as a builtin."""
    registry = get_analysis_registry()
    assert registry["sum_intensity"] is SumIntensityAnalysis
