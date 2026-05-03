"""Tests for analysis dependencies."""

import pytest

from acqstore.acq_image.acq_analysis_set import AcqAnalysisSet
from acqstore.acq_image.analysis.examples import VelocityAnalysis, VelocityEventAnalysis


def test_require_dependencies_finds_same_channel_and_roi_dependency() -> None:
    """Dependencies should resolve by same channel and ROI."""
    analysis_set = AcqAnalysisSet("fake.tif")
    velocity = VelocityAnalysis(channel=1, roi_id=2)
    event = VelocityEventAnalysis(channel=1, roi_id=2)
    analysis_set.add(velocity)

    deps = analysis_set.require_dependencies(event)

    assert deps["velocity"] is velocity


def test_require_dependencies_raises_for_missing_dependency() -> None:
    """Missing dependency should raise ValueError."""
    analysis_set = AcqAnalysisSet("fake.tif")
    event = VelocityEventAnalysis(channel=1, roi_id=2)

    with pytest.raises(ValueError):
        analysis_set.require_dependencies(event)
