"""Schema-backed models for ΔF/F0 and diameter cross-analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any, Mapping

import pandas as pd


class EventDirection(StrEnum):
    """Expected direction of the analyzed response signal."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class SignalFilterMethod(StrEnum):
    """Supported preprocessing filters for triggered-event analysis."""

    NONE = "none"
    MEDIAN = "median"
    SAVGOL = "savgol"


class TriggeredEventStatus(StrEnum):
    """Overall measurement status for one seeded event."""

    OK = "ok"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AnalysisSelection:
    """Identify one channel and ROI within analysis outputs."""

    channel: int
    roi_id: int


@dataclass(frozen=True, slots=True)
class DiameterFilterParams:
    """Legacy local diameter filter parameters used by the sidecar loader."""

    method: str = "median"
    kernel_points: int = 3


@dataclass(frozen=True, slots=True)
class TriggeredEventParams:
    """Parameters for measuring one signal event per supplied seed index.

    All internal window parameters are expressed in sample points. The
    ``post_search_window_points`` limits the extremum search independently of
    the longer post-event window used to measure recovery and area. The next
    seed and end of signal always remain hard boundaries.
    """

    direction: EventDirection = EventDirection.NEGATIVE
    pre_points: int = 50
    post_points: int = 500
    post_search_window_points: int = 250
    baseline_start_offset_points: int = -50
    baseline_stop_offset_points: int = 0
    filter_method: SignalFilterMethod = SignalFilterMethod.MEDIAN
    median_kernel_points: int = 3
    savgol_window_points: int = 11
    savgol_polyorder: int = 3
    recovery_fraction: float = 0.9

    def to_dict(self) -> dict[str, object]:
        """Serialize parameters to JSON-compatible values."""
        data = asdict(self)
        data["direction"] = self.direction.value
        data["filter_method"] = self.filter_method.value
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "TriggeredEventParams":
        """Create parameters from serialized values."""
        values = dict(data)
        values["direction"] = EventDirection(str(values["direction"]))
        values["filter_method"] = SignalFilterMethod(str(values["filter_method"]))
        return cls(**values)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class ReporterEvent:
    """Upstream reporter event used as a seed for cross-analysis."""

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


@dataclass(frozen=True, slots=True)
class TriggeredEvent:
    """Measurements for one event anchored to a supplied seed index."""

    schema_version: int
    seed_id: int
    seed_index: int
    seed_time_sec: float
    window_start_index: int
    window_stop_index: int
    next_seed_index: int | None
    truncated_by_next_seed: bool
    truncated_by_signal_end: bool
    status: TriggeredEventStatus
    warnings: tuple[str, ...]
    baseline_start_index: int | None
    baseline_stop_index: int | None
    baseline_value: float | None
    baseline_std: float | None
    baseline_slope_per_sec: float | None
    pre_seed_value: float | None
    pre_seed_change: float | None
    extremum_index: int | None
    extremum_time_sec: float | None
    extremum_value: float | None
    time_to_extremum_from_seed_points: int | None
    time_to_extremum_from_seed_sec: float | None
    signed_amplitude: float | None
    amplitude: float | None
    fractional_amplitude: float | None
    percent_amplitude: float | None
    average_seed_to_extremum_slope_per_sec: float | None
    maximum_oriented_slope_per_sec: float | None
    recovery_detected: bool
    recovery_index: int | None
    recovery_time_sec: float | None
    extremum_to_recovery_sec: float | None
    seed_to_recovery_sec: float | None
    baseline_adjusted_auc_seed_to_stop: float | None

    def to_dict(self) -> dict[str, object]:
        """Serialize this event to a JSON-compatible dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        data["warnings"] = list(self.warnings)
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, object]) -> "TriggeredEvent":
        """Deserialize one event from :meth:`to_dict` output."""
        values = dict(data)
        values["status"] = TriggeredEventStatus(str(values["status"]))
        values["warnings"] = tuple(str(item) for item in values.get("warnings", ()))
        return cls(**values)  # type: ignore[arg-type]


@dataclass(slots=True)
class Dff0DiameterDataset:
    """Validated data for one file, channel, and ROI."""

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
