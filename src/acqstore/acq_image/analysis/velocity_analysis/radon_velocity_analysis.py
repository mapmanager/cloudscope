"""AcqStore wrapper for Radon velocity analysis."""

from __future__ import annotations

from acqstore.acq_image.analysis.data_provider import AnalysisDataProvider
from acqstore.acq_image.analysis.model import (
    AnalysisCancelled,
    AnalysisResult,
    AnalysisRunContext,
    BaseAnalysis,
    DetectionParamSchema,
    DetectionValueType,
)
from acqstore.acq_image.analysis.registry import register_analysis_class
from acqstore.acq_image.analysis.velocity_analysis.radon_core import (
    RadonVelocityCancelled,
    run_radon_velocity,
)


@register_analysis_class
class RadonVelocityAnalysis(BaseAnalysis):
    """Radon-transform velocity analysis for one channel/ROI."""

    def __init__(
        self,
        *,
        channel: int,
        roi_id: int,
        detection_params: dict[str, object] | None = None,
    ) -> None:
        """Create a Radon velocity analysis instance.

        Args:
            channel: Channel index for analysis.
            roi_id: ROI identifier for analysis.
            detection_params: Optional detection parameters.
        """
        super().__init__(
            channel=channel,
            roi_id=roi_id,
            detection_params=detection_params,
        )
        self._use_multiprocessing = True
        self._processes: int | None = None

    def set_execution_options(
        self,
        *,
        use_multiprocessing: bool = True,
        processes: int | None = None,
    ) -> None:
        """Set runtime execution options for the next run.

        These options are not detection parameters and are not serialized. They
        control how the current Python process executes the expensive Radon
        computation.

        Args:
            use_multiprocessing: Whether to use multiprocessing for Radon
                windows.
            processes: Optional number of worker processes. ``None`` lets the
                core algorithm choose a CPU-count based default.

        Returns:
            None.
        """
        self._use_multiprocessing = bool(use_multiprocessing)
        self._processes = None if processes is None else int(processes)

    analysis_name = "radon_velocity"
    detection_schema = (
        DetectionParamSchema(
            name="window_width",
            display_name="Window Width",
            value_type=DetectionValueType.INT,
            default=64,
            description="Number of time samples per Radon analysis window.",
            choices=(16, 64, 128),
            visible=True,
            editable=True,
        ),
    )

    def run(
        self,
        data_provider: AnalysisDataProvider,
        *,
        context: AnalysisRunContext | None = None,
        dependencies: dict[str, BaseAnalysis] | None = None,
    ) -> AnalysisResult:
        """Run Radon velocity analysis.

        Args:
            data_provider: Analysis data provider for ROI image data and image
                physical units.
            context: Optional progress/cancellation context.
            dependencies: Dependency analyses. This analysis does not require
                dependencies.

        Returns:
            Analysis result populated with summary dict and result table.

        Raises:
            AnalysisCancelled: If the run is cancelled.
        """
        context = context or AnalysisRunContext()
        context.raise_if_cancelled()
        image = data_provider.get_roi_image(channel=self.key.channel, roi_id=self.key.roi_id)
        physical_units = data_provider.get_image_physical_units()
        window_width = int(self.detection_params["window_width"])

        try:
            result = run_radon_velocity(
                image,
                window_width=window_width,
                physical_units=physical_units,
                progress_callback=context.report_progress,
                cancel_callback=context.is_cancelled,
                use_multiprocessing=self._use_multiprocessing,
                processes=self._processes,
            )
        except RadonVelocityCancelled as exc:
            raise AnalysisCancelled(str(exc)) from exc

        self.result.summary = result.summary
        self.result.table = result.table
        self.set_dirty()
        return self.result
