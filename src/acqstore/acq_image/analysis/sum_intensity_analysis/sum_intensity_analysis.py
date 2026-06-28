"""Public BaseAnalysis wrapper for sum-intensity peak detection."""

from __future__ import annotations

from acqstore.acq_image.analysis.data_provider import AnalysisDataProvider
from acqstore.acq_image.analysis.model import (
    AnalysisPlotData,
    AnalysisResult,
    AnalysisRunContext,
    BaseAnalysis,
    DetectionParamSchema,
    DetectionValueType,
)
from acqstore.acq_image.analysis.registry import register_analysis_class
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_core import (
    PeakEvent,
    run_sum_intensity,
)


@register_analysis_class
class SumIntensityAnalysis(BaseAnalysis):
    """Measure normalized line intensity and detect peaks/events.

    The analysis runs on a full-resolution rectangular ROI crop. Rows are
    interpreted as time and columns as distance. The raw row-sum trace is stored
    for debugging, but peak detection uses normalized intensity
    ``sum_intensity / image.shape[1]`` so ROIs with different spatial widths are
    more comparable.

    Args:
        channel: Zero-based channel index for analysis.
        roi_id: ROI identifier for analysis.
        detection_params: Optional detection parameters. Missing values are
            filled from ``detection_schema`` defaults.
    """

    analysis_name = "sum_intensity"
    analysis_version = 1
    summary_columns = (
        "analysis_date",
        "analysis_time",
        "analysis_version",
        "status",
        "num_timepoints",
        "num_peaks",
        "num_space_pixels",
        "seconds_per_line",
        "peak_amplitude_mean",
        "peak_amplitude_median",
    )
    detection_schema = (
        DetectionParamSchema(
            name="window_radius_points",
            display_name="Window Radius",
            value_type=DetectionValueType.INT,
            default=0,
            unit="points",
            description="Radius around each time row used for rolling row-sum averaging.",
        ),
        DetectionParamSchema(
            name="filter_method",
            display_name="Filter Method",
            value_type=DetectionValueType.ENUM,
            default="median",
            choices=("none", "median"),
            description="Optional pre-detection trace filter applied to normalized intensity.",
        ),
        DetectionParamSchema(
            name="median_filter_kernel_points",
            display_name="Median Filter Kernel",
            value_type=DetectionValueType.INT,
            default=3,
            unit="points",
            description="Median filter kernel size in time points. Even values are rounded up.",
            methods=("median",),
        ),
        DetectionParamSchema(
            name="detrend_method",
            display_name="Detrend Method",
            value_type=DetectionValueType.ENUM,
            default="single_exponential",
            choices=("none", "single_exponential"),
            description="Optional bleach-trend removal before detection.",
        ),
        DetectionParamSchema(
            name="detection_method",
            display_name="Detection Method",
            value_type=DetectionValueType.ENUM,
            default="derivative_threshold",
            choices=("derivative_threshold", "absolute_threshold"),
            description="Peak onset detector.",
        ),
        DetectionParamSchema(
            name="polarity",
            display_name="Polarity",
            value_type=DetectionValueType.ENUM,
            default="positive",
            choices=("positive", "negative"),
            description="Expected peak polarity in the detection signal.",
        ),
        DetectionParamSchema(
            name="absolute_threshold",
            display_name="Absolute Threshold",
            value_type=DetectionValueType.FLOAT,
            default=0.0,
            description="Detection-signal threshold used by absolute_threshold detection.",
            methods=("absolute_threshold",),
        ),
        DetectionParamSchema(
            name="derivative_threshold",
            display_name="Derivative Threshold",
            value_type=DetectionValueType.FLOAT,
            default=1.0,
            unit="signal/s",
            description="Derivative threshold used by derivative_threshold detection.",
            methods=("derivative_threshold",),
        ),
        DetectionParamSchema(
            name="refractory_period_ms",
            display_name="Refractory Period",
            value_type=DetectionValueType.FLOAT,
            default=10.0,
            unit="ms",
            description="Minimum accepted onset-to-onset interval.",
        ),
        DetectionParamSchema(
            name="peak_search_window_ms",
            display_name="Peak Search Window",
            value_type=DetectionValueType.FLOAT,
            default=50.0,
            unit="ms",
            description="Forward search window used to refine peak index after onset.",
        ),
        DetectionParamSchema(
            name="level_fractions",
            display_name="Level Fractions",
            value_type=DetectionValueType.STR,
            default="0.1,0.2,0.5,0.8,0.9",
            description="Comma-separated peak-amplitude fractions for width measurements.",
        ),
    )

    def __init__(
        self,
        *,
        channel: int,
        roi_id: int,
        detection_params: dict[str, object] | None = None,
    ) -> None:
        """Create a sum-intensity analysis instance.

        Args:
            channel: Channel index for analysis.
            roi_id: ROI identifier for analysis.
            detection_params: Optional detection parameters.
        """
        super().__init__(channel=channel, roi_id=roi_id, detection_params=detection_params)

    def run(
        self,
        data_provider: AnalysisDataProvider,
        *,
        context: AnalysisRunContext | None = None,
        dependencies: dict[str, BaseAnalysis] | None = None,
    ) -> AnalysisResult:
        """Run sum-intensity peak detection on one ROI crop.

        Args:
            data_provider: Provider for ROI image data and physical spacing.
                ``get_roi_image`` must return a 2D ``(time, space)`` array.
            context: Optional progress/cancellation context.
            dependencies: Unused for sum-intensity analysis.

        Returns:
            Populated analysis result. The result table includes normalized
            intensity, detection signal, onset mask, and peak mask columns.
        """
        _ = dependencies
        context = context or AnalysisRunContext()
        context.raise_if_cancelled()
        context.report_progress(0.0, "Loading ROI image")
        image = data_provider.get_roi_image(channel=self.key.channel, roi_id=self.key.roi_id)
        physical_units = data_provider.get_image_physical_units()
        context.report_progress(0.25, "Running sum intensity analysis")
        result = run_sum_intensity(
            image,
            detection_params=self.detection_params,
            physical_units=physical_units,
        )
        context.raise_if_cancelled()
        self.result.summary = self.finalize_summary(result.summary)
        self.result.table = result.table
        self.set_dirty()
        context.report_progress(1.0, "Sum intensity analysis complete")
        return self.result

    def get_peak_events(self) -> tuple[PeakEvent, ...]:
        """Return parsed peak-event records from the result summary.

        Returns:
            Tuple of peak events. Empty when analysis has not been run or when
            no peaks were detected.
        """
        records = self.result.summary.get("events", ())
        return tuple(PeakEvent.from_json_dict(dict(record)) for record in records)

    def get_plot_data(self) -> AnalysisPlotData | None:
        """Return canonical normalized-intensity plot data.

        Returns:
            Plot data using ``time_sec`` for the x axis and
            ``detection_signal`` for the y axis, or None when the analysis has
            no table output yet.

        Raises:
            KeyError: If the table is present but missing required columns.
        """
        if self.result.table is None:
            return None
        table = self.result.table
        if "time_sec" not in table.columns:
            raise KeyError("Sum intensity plot requires 'time_sec' column")
        if "detection_signal" not in table.columns:
            raise KeyError("Sum intensity plot requires 'detection_signal' column")
        return AnalysisPlotData(
            x=tuple(float(value) for value in table["time_sec"].tolist()),
            y=tuple(float(value) for value in table["detection_signal"].tolist()),
            x_label="Time (s)",
            y_label="Normalized intensity",
            series_name="Sum intensity",
        )
