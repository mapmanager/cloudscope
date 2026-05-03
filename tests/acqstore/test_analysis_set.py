"""Tests for AcqAnalysisSet collection behavior."""

import pytest

from acqstore.acq_image.acq_analysis_set import AcqAnalysisSet
from acqstore.acq_image.analysis.examples import VelocityAnalysis
from acqstore.acq_image.analysis.model import AnalysisKey


def test_add_rejects_duplicate_key() -> None:
    """AcqAnalysisSet should reject duplicate analysis keys."""
    analysis_set = AcqAnalysisSet("fake.tif")
    analysis_set.add(VelocityAnalysis(channel=0, roi_id=1))

    with pytest.raises(ValueError):
        analysis_set.add(VelocityAnalysis(channel=0, roi_id=1))


def test_create_uses_registry() -> None:
    """create should instantiate registered analysis classes."""
    analysis_set = AcqAnalysisSet("fake.tif")

    analysis = analysis_set.create("velocity", channel=0, roi_id=1)

    assert analysis.key == AnalysisKey("velocity", 0, 1)


def test_get_required_raises_for_missing_key() -> None:
    """get_required should raise for missing analysis."""
    analysis_set = AcqAnalysisSet("fake.tif")

    with pytest.raises(KeyError):
        analysis_set.get_required(AnalysisKey("velocity", 0, 1))


def test_delete_roi_removes_matching_analyses_and_marks_dirty() -> None:
    """delete_roi should remove matching analyses and mark set dirty."""
    analysis_set = AcqAnalysisSet("fake.tif")
    analysis_set.add(VelocityAnalysis(channel=0, roi_id=1))
    analysis_set.add(VelocityAnalysis(channel=0, roi_id=2))
    analysis_set.set_clean()

    removed = analysis_set.delete_roi(1)

    assert removed == 1
    assert len(analysis_set.as_list()) == 1
    assert analysis_set.is_dirty()


def test_edit_roi_removes_matching_analyses() -> None:
    """edit_roi should remove matching analyses for v1."""
    analysis_set = AcqAnalysisSet("fake.tif")
    analysis_set.add(VelocityAnalysis(channel=0, roi_id=1))

    removed = analysis_set.edit_roi(1)

    assert removed == 1
    assert analysis_set.as_list() == []
