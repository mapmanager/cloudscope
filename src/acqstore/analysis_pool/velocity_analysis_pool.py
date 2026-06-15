"""Velocity-oriented analysis pool for AcqImageList collections."""

from __future__ import annotations

from acqstore.acq_image.analysis.event_analysis.event_analysis import EventAnalysis
from acqstore.acq_image.analysis.heart_rate_analysis.heart_rate_analysis import HeartRateAnalysis
from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import (
    RadonVelocityAnalysis,
)
from acqstore.analysis_pool.base_analysis_pool import AnalysisPool


class VelocityAnalysisPool(AnalysisPool):
    """Flat pool for velocity, heart-rate, and event summaries.

    The table has one row per loaded ``AcqImage``/channel/ROI selection. Base
    acquisition columns are followed by ``velocity_*``, ``hr_*``, and
    ``event_*`` columns. Missing analyses leave their columns as ``pandas.NA``.
    """

    analysis_specs = (
        ("velocity", RadonVelocityAnalysis),
        ("hr", HeartRateAnalysis),
        ("event", EventAnalysis),
    )
