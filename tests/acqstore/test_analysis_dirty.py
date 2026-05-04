"""Tests for analysis dirty behavior."""

from acqstore.acq_image.acq_analysis_set import AcqAnalysisSet
from acqstore.acq_image.analysis.examples import VelocityAnalysis, VelocityEventAnalysis
from acqstore.acq_image.analysis.model import AnalysisKey


class FakeProvider:
    """Fake provider for dirty tests."""

    def get_roi_image(self, channel: int, roi_id: int):
        """Return fake ROI image."""
        import numpy as np

        return np.array([[1.0, 2.0]])

    def get_image_physical_units(self) -> tuple[float, float]:
        """Return fake physical units."""
        return (1.0, 1.0)


def test_analysis_starts_clean() -> None:
    """New analysis should start clean."""
    analysis = VelocityAnalysis(channel=0, roi_id=1)

    assert not analysis.is_dirty()


def test_event_crud_marks_analysis_dirty() -> None:
    """Velocity event CRUD APIs should mark analysis dirty."""
    analysis = VelocityEventAnalysis(channel=0, roi_id=1)

    analysis.add_event({"event_id": 1})

    assert analysis.is_dirty()


def test_analysis_set_dirty_reflects_child_dirty() -> None:
    """Analysis set should be dirty when a child is dirty."""
    analysis_set = AcqAnalysisSet("fake.tif")
    analysis = VelocityEventAnalysis(channel=0, roi_id=1)
    analysis_set.add(analysis)
    analysis_set.set_clean()

    analysis.add_event({"event_id": 1})

    assert analysis_set.is_dirty()


def test_run_analysis_marks_analysis_and_set_dirty() -> None:
    """Running analysis should mark both analysis and set dirty."""
    analysis_set = AcqAnalysisSet("fake.tif", data_provider=FakeProvider())
    analysis = VelocityAnalysis(channel=0, roi_id=1)
    analysis_set.add(analysis)
    analysis_set.set_clean()

    analysis_set.run_analysis(AnalysisKey("velocity", 0, 1))

    assert analysis.is_dirty()
    assert analysis_set.is_dirty()


def test_set_clean_cleans_children() -> None:
    """set_clean should clean set and child analyses."""
    analysis_set = AcqAnalysisSet("fake.tif", data_provider=FakeProvider())
    analysis = VelocityAnalysis(channel=0, roi_id=1)
    analysis_set.add(analysis)
    analysis.set_dirty()

    analysis_set.set_clean()

    assert not analysis.is_dirty()
    assert not analysis_set.is_dirty()
