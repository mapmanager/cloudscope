"""High-level paired reporter and diameter analysis interface."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .loading import load_sidecars
from .models import AnalysisSelection, DiameterFilterParams, Dff0DiameterDataset


class Dff0DiameterAnalysis:
    """Analyze paired reporter and diameter sidecar outputs.

    This first implementation establishes strict selection, loading,
    alignment, local diameter filtering, and reporter-event access. Triggered
    diameter response measurements are intentionally deferred until the traces
    and preprocessing can be inspected interactively.
    """

    def __init__(self, dataset: Dff0DiameterDataset) -> None:
        """Initialize from a validated dataset.

        Args:
            dataset: Validated paired dataset.
        """
        self._dataset = dataset

    @classmethod
    def from_sidecars(
        cls,
        *,
        diameter_csv: str | Path,
        reporter_csv: str | Path,
        analysis_json: str | Path,
        channel: int,
        roi_id: int,
        diameter_filter_method: str = "median",
        diameter_filter_kernel_points: int = 3,
    ) -> "Dff0DiameterAnalysis":
        """Create an analysis from the three per-file sidecars.

        No raw-data path or pooled peak CSV is required.

        Args:
            diameter_csv: Per-file diameter CSV.
            reporter_csv: Per-file sum-intensity CSV.
            analysis_json: Per-file structured analysis JSON.
            channel: Channel to select from all inputs.
            roi_id: ROI to select from all inputs.
            diameter_filter_method: Local raw-diameter filter method.
            diameter_filter_kernel_points: Odd filter width in points.

        Returns:
            Loaded analysis instance.
        """
        dataset = load_sidecars(
            diameter_csv=diameter_csv,
            reporter_csv=reporter_csv,
            analysis_json=analysis_json,
            selection=AnalysisSelection(channel=channel, roi_id=roi_id),
            diameter_filter=DiameterFilterParams(
                method=diameter_filter_method,
                kernel_points=diameter_filter_kernel_points,
            ),
        )
        return cls(dataset)

    @property
    def dataset(self) -> Dff0DiameterDataset:
        """Return the validated dataset."""
        return self._dataset

    def get_alignment_summary(self) -> dict[str, object]:
        """Return a compact diagnostic summary.

        Returns:
            Dictionary suitable for logging, display, or tests.
        """
        reporter = self._dataset.reporter
        diameter = self._dataset.diameter
        return {
            "source_name": self._dataset.source_name,
            "channel": self._dataset.selection.channel,
            "roi_id": self._dataset.selection.roi_id,
            "num_points": len(reporter),
            "seconds_per_point": self._dataset.seconds_per_point,
            "duration_sec": float(reporter["time_sec"].iloc[-1]),
            "num_reporter_events": len(self._dataset.events),
            "num_missing_reporter": int(reporter["df_f_signal"].isna().sum()),
            "num_missing_diameter_raw": int(diameter["diameter_um_raw"].isna().sum()),
            "num_missing_diameter_filtered": int(
                diameter["diameter_um_analysis"].isna().sum()
            ),
        }

    def get_reporter_events_dataframe(self) -> pd.DataFrame:
        """Return one flat row per selected reporter event.

        Returns:
            DataFrame containing stable event identity and core onset/peak
            measurements from the JSON sidecar.
        """
        return pd.DataFrame(
            [
                {
                    "peak_id": event.peak_id,
                    "status": event.status,
                    "onset_index": event.onset_index,
                    "onset_time_sec": event.onset_time_sec,
                    "onset_value": event.onset_value,
                    "peak_index": event.peak_index,
                    "peak_time_sec": event.peak_time_sec,
                    "peak_value": event.peak_value,
                    "peak_amplitude": event.peak_amplitude,
                }
                for event in self._dataset.events
            ]
        )
