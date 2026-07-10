"""Data models for paired reporter and diameter analysis."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True, slots=True)
class AnalysisSelection:
    """Identify one channel and ROI within per-file analysis sidecars.

    Args:
        channel: Zero-based channel index.
        roi_id: ROI identifier used by the source analyses.
    """

    channel: int
    roi_id: int


@dataclass(frozen=True, slots=True)
class DiameterFilterParams:
    """Parameters for filtering the raw diameter trace.

    Args:
        method: Filtering method. Supported values are ``"none"`` and
            ``"median"``.
        kernel_points: Odd median-filter window length in samples.
    """

    method: str = "median"
    kernel_points: int = 3

    def validate(self) -> None:
        """Validate filter parameters.

        Raises:
            ValueError: If the method or kernel size is invalid.
        """
        if self.method not in {"none", "median"}:
            raise ValueError(f"Unsupported diameter filter method: {self.method!r}")
        if self.kernel_points < 1:
            raise ValueError("kernel_points must be at least 1")
        if self.method == "median" and self.kernel_points % 2 == 0:
            raise ValueError("Median filter kernel_points must be odd")


@dataclass(frozen=True, slots=True)
class ReporterEvent:
    """One reporter event loaded from the per-file JSON sidecar.

    Args:
        peak_id: Event identifier assigned by upstream peak analysis.
        onset_index: Integer sample index of the detected onset.
        onset_time_sec: Onset time in seconds.
        onset_value: Reporter value at onset.
        peak_index: Integer sample index of the event peak.
        peak_time_sec: Peak time in seconds.
        peak_value: Reporter value at the peak.
        peak_amplitude: Upstream event amplitude measurement.
        status: Upstream event status.
        raw_event: Original structured event mapping for later feature access.
    """

    peak_id: int
    onset_index: int
    onset_time_sec: float
    onset_value: float
    peak_index: int
    peak_time_sec: float
    peak_value: float
    peak_amplitude: float
    status: str
    raw_event: dict[str, Any]


@dataclass(slots=True)
class Dff0DiameterDataset:
    """Validated data for one file, channel, and ROI.

    Args:
        source_name: Filename stem inferred from sidecar names or JSON metadata.
        selection: Selected channel and ROI.
        seconds_per_point: Sampling period in seconds.
        reporter: Selected sum-intensity trace table.
        diameter: Selected diameter trace table with locally filtered columns.
        events: Reporter events loaded from the JSON sidecar.
        analysis_json: Complete JSON document.
        diameter_csv_path: Source diameter CSV path.
        reporter_csv_path: Source sum-intensity CSV path.
        analysis_json_path: Source analysis JSON path.
    """

    source_name: str
    selection: AnalysisSelection
    seconds_per_point: float
    reporter: pd.DataFrame
    diameter: pd.DataFrame
    events: tuple[ReporterEvent, ...]
    analysis_json: dict[str, Any]
    diameter_csv_path: Path
    reporter_csv_path: Path
    analysis_json_path: Path
