"""ROI mode enum for batch analysis."""

from __future__ import annotations

from enum import StrEnum


class RoiBatchMode(StrEnum):
    """How a batch strategy chooses the ROI for each file."""

    ANALYZE_EXISTING_ROI = "analyze_existing_roi"
    ADD_NEW_ROI = "add_new_roi"
