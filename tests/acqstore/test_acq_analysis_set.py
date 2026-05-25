"""Tests for AcqAnalysisSet dependency enforcement."""

from __future__ import annotations

from acqstore.acq_image.acq_analysis_set import AcqAnalysisSet
from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis
from acqstore.acq_image.analysis.model import AnalysisPlotData, AnalysisResult, BaseAnalysis


class DummyRadonAnalysis(BaseAnalysis):
    """Minimal Radon velocity dependency for event-analysis creation."""

    analysis_name = "radon_velocity"

    def run(self, data_provider, *, context=None, dependencies=None) -> AnalysisResult:
        """Return the existing empty result."""
        return self.result

    def get_plot_data(self) -> AnalysisPlotData:
        """Return simple velocity plot data."""
        return AnalysisPlotData(
            x=(0.0, 1.0),
            y=(1.0, 2.0),
            x_label="Time (s)",
            y_label="Velocity",
        )


def test_event_analysis_creation_requires_matching_radon_velocity() -> None:
    """Event analysis should not be created without its Radon dependency."""
    analysis_set = AcqAnalysisSet("example.tif")

    try:
        analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)
    except ValueError as exc:
        assert "requires 'radon_velocity'" in str(exc)
    else:  # pragma: no cover - defensive assertion branch
        raise AssertionError("event analysis created without Radon dependency")


def test_event_analysis_creation_succeeds_with_matching_radon_velocity() -> None:
    """Event analysis should be creatable when matching Radon exists."""
    analysis_set = AcqAnalysisSet("example.tif")
    analysis_set.add(DummyRadonAnalysis(channel=0, roi_id=1))

    analysis = analysis_set.create(EventAnalysis.analysis_name, channel=0, roi_id=1)

    assert isinstance(analysis, EventAnalysis)
