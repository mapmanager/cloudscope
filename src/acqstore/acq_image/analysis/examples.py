"""Example analysis plugins for tests and API exercises."""

from __future__ import annotations

from typing import Any

import pandas as pd

from acqstore.acq_image.analysis.data_provider import AnalysisDataProvider
from acqstore.acq_image.analysis.model import (
    AnalysisResult,
    AnalysisRunContext,
    BaseAnalysis,
    DetectionParamSchema,
    DetectionValueType,
)
from acqstore.acq_image.analysis.registry import register_analysis_class


@register_analysis_class
class DiameterAnalysis(BaseAnalysis):
    """Example diameter analysis with table output."""

    analysis_name = "diameter"
    detection_schema = (
        DetectionParamSchema(
            name="threshold",
            display_name="Threshold",
            value_type=DetectionValueType.FLOAT,
            default=0.5,
        ),
        DetectionParamSchema(
            name="min_diameter_px",
            display_name="Minimum Diameter",
            value_type=DetectionValueType.FLOAT,
            default=2.0,
            unit="px",
        ),
    )

    def run(
        self,
        data_provider: AnalysisDataProvider,
        *,
        context: AnalysisRunContext | None = None,
        dependencies: dict[str, BaseAnalysis] | None = None,
    ) -> AnalysisResult:
        """Run example diameter analysis.

        Args:
            data_provider: Analysis data provider.
            context: Optional progress/cancellation context.
            dependencies: Dependency analyses.

        Returns:
            Analysis result.
        """
        roi_image = data_provider.get_roi_image(
            channel=self.key.channel,
            roi_id=self.key.roi_id,
        )
        mean_value = float(roi_image.mean()) if roi_image.size else 0.0
        self.result.summary = {"mean_diameter": mean_value}
        self.result.table = pd.DataFrame(
            {
                "time_s": [0.0, 1.0],
                "diameter": [mean_value, mean_value + 0.5],
            }
        )
        self.set_dirty()
        return self.result


@register_analysis_class
class VelocityEventAnalysis(BaseAnalysis):
    """Example velocity-event analysis depending on velocity output."""

    analysis_name = "velocity_event"
    depends_on = ("radon_velocity",)
    detection_schema = ()

    def run(
        self,
        data_provider: AnalysisDataProvider,
        *,
        context: AnalysisRunContext | None = None,
        dependencies: dict[str, BaseAnalysis] | None = None,
    ) -> AnalysisResult:
        """Run example velocity-event analysis.

        Args:
            data_provider: Analysis data provider.
            context: Optional progress/cancellation context.
            dependencies: Dependency analyses. Must include ``"velocity"``.

        Returns:
            Analysis result.

        Raises:
            ValueError: If velocity dependency is missing.
        """
        dependencies = dependencies or {}
        velocity = dependencies.get("radon_velocity")
        if velocity is None:
            raise ValueError("VelocityEventAnalysis requires radon_velocity dependency")

        velocities = velocity.get_column("velocity")
        events = [
            {"event_id": i, "velocity": value}
            for i, value in enumerate(velocities)
            if float(value) > 2.0
        ]
        self.result.summary = {"events": events, "num_events": len(events)}
        self.result.table = None
        self.set_dirty()
        return self.result

    def add_event(self, event: dict[str, Any]) -> None:
        """Add one event to the summary event list.

        Args:
            event: Event dictionary to append.

        Returns:
            None.
        """
        events = list(self.result.summary.get("events", []))
        events.append(dict(event))
        self.result.summary["events"] = events
        self.result.summary["num_events"] = len(events)
        self.set_dirty()

    def delete_event(self, event_id: int) -> None:
        """Delete one event by event identifier.

        Args:
            event_id: Event identifier to remove.

        Returns:
            None.
        """
        events = [
            event
            for event in self.result.summary.get("events", [])
            if int(event.get("event_id", -1)) != event_id
        ]
        self.result.summary["events"] = events
        self.result.summary["num_events"] = len(events)
        self.set_dirty()

    def edit_event(self, event_id: int, patch: dict[str, Any]) -> None:
        """Edit one event by event identifier.

        Args:
            event_id: Event identifier to edit.
            patch: Values to merge into the matching event.

        Returns:
            None.

        Raises:
            KeyError: If no matching event exists.
        """
        events = list(self.result.summary.get("events", []))
        for event in events:
            if int(event.get("event_id", -1)) == event_id:
                event.update(patch)
                self.result.summary["events"] = events
                self.set_dirty()
                return
        raise KeyError(f"Event not found: {event_id}")


@register_analysis_class
class VelocityHeartRateAnalysis(BaseAnalysis):
    """Example heart-rate analysis depending on velocity output."""

    analysis_name = "velocity_heart_rate"
    depends_on = ("radon_velocity",)

    def run(
        self,
        data_provider: AnalysisDataProvider,
        *,
        context: AnalysisRunContext | None = None,
        dependencies: dict[str, BaseAnalysis] | None = None,
    ) -> AnalysisResult:
        """Run example heart-rate analysis.

        Args:
            data_provider: Analysis data provider.
            context: Optional progress/cancellation context.
            dependencies: Dependency analyses. Must include ``"velocity"``.

        Returns:
            Analysis result.
        """
        dependencies = dependencies or {}
        velocity = dependencies["radon_velocity"]
        values = velocity.get_column("velocity")
        self.result.summary = {"heart_rate_bpm": float(len(values) * 60)}
        self.result.table = None
        self.set_dirty()
        return self.result
