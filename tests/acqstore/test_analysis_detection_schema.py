"""Tests for detection parameter schema behavior."""

import pytest

from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import DiameterAnalysis
from acqstore.acq_image.analysis.examples import ExampleDiameterAnalysis
from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import RadonVelocityAnalysis
from acqstore.acq_image.analysis.model import DetectionParamSchema, DetectionValueType


def test_detection_schema_correctness_velocity() -> None:
    """RadonVelocityAnalysis schema should match the ticket spec."""
    schema = RadonVelocityAnalysis.get_detection_schema()
    assert isinstance(schema, tuple)
    assert schema == (
        DetectionParamSchema(
            name="window_width",
            display_name="Window Width",
            value_type=DetectionValueType.INT,
            default=64,
            description="Number of time samples per Radon analysis window.",
            visible=True,
            editable=True,
            choices=(16, 64, 128),
            unit=None,
        ),
    )


def test_defaults_velocity() -> None:
    """RadonVelocityAnalysis should set defaults when params missing."""
    analysis = RadonVelocityAnalysis(channel=0, roi_id=1)
    assert analysis.detection_params == {"window_width": 64}


def test_defaults_diameter() -> None:
    """DiameterAnalysis should set defaults when params missing."""
    analysis = DiameterAnalysis(channel=0, roi_id=1)
    assert analysis.detection_params["diameter_method"] == "threshold_width"
    assert analysis.detection_params["post_filter_kernel_size"] == 3


def test_defaults_example_diameter() -> None:
    """ExampleDiameterAnalysis should keep legacy example defaults."""
    analysis = ExampleDiameterAnalysis(channel=0, roi_id=1)
    assert analysis.detection_params == {"threshold": 0.5, "min_diameter_px": 2.0}


def test_valid_patch_updates_values() -> None:
    """Valid patches should be accepted and merged onto defaults."""
    analysis = RadonVelocityAnalysis(channel=0, roi_id=1, detection_params={"window_width": 16})
    assert analysis.detection_params == {"window_width": 16}


def test_unknown_key_raises_key_error() -> None:
    """Unknown keys should be rejected."""
    with pytest.raises(KeyError):
        RadonVelocityAnalysis(channel=0, roi_id=1, detection_params={"nope": 1})


def test_wrong_type_raises_type_error() -> None:
    """Wrong types should be rejected."""
    with pytest.raises(TypeError):
        RadonVelocityAnalysis(channel=0, roi_id=1, detection_params={"window_width": "64"})


def test_invalid_choice_raises_value_error() -> None:
    """Choices should be enforced when present."""
    with pytest.raises(ValueError):
        RadonVelocityAnalysis(channel=0, roi_id=1, detection_params={"window_width": 32})


def test_bool_vs_int_is_rejected() -> None:
    """Bool must not be accepted where int is required."""
    with pytest.raises(TypeError):
        RadonVelocityAnalysis(channel=0, roi_id=1, detection_params={"window_width": True})


def test_float_rules_accept_int_and_reject_bool() -> None:
    """Float params accept int/float but reject bool."""
    ok = ExampleDiameterAnalysis(channel=0, roi_id=1, detection_params={"threshold": 1})
    assert ok.detection_params["threshold"] == 1

    with pytest.raises(TypeError):
        ExampleDiameterAnalysis(channel=0, roi_id=1, detection_params={"threshold": True})

