"""AcqStore wrapper for diameter analysis."""

from __future__ import annotations

from acqstore.acq_image.analysis.data_provider import AnalysisDataProvider
from acqstore.acq_image.analysis.diameter_analysis.diameter_core import (
    DiameterCancelled,
    run_diameter,
)
from acqstore.acq_image.analysis.model import (
    AnalysisCancelled,
    AnalysisOverlayTraceData,
    AnalysisPlotData,
    AnalysisResult,
    AnalysisRunContext,
    BaseAnalysis,
    DetectionParamSchema,
    DetectionValueType,
)
from acqstore.acq_image.analysis.registry import register_analysis_class

_SHARED: tuple[str, ...] = ("threshold_width", "gradient_edges")


@register_analysis_class
class DiameterAnalysis(BaseAnalysis):
    """Diameter analysis for one channel/ROI on a line-scan kymograph."""

    analysis_name = "diameter"
    detection_schema = (
        DetectionParamSchema(
            name="window_rows_odd",
            display_name="Window Rows (Odd)",
            value_type=DetectionValueType.INT,
            default=5,
            description="Odd number of time rows aggregated into each spatial profile.",
            methods=_SHARED,
        ),
        DetectionParamSchema(
            name="stride",
            display_name="Stride",
            value_type=DetectionValueType.INT,
            default=1,
            description="Center-row increment between successive measurements.",
            methods=_SHARED,
        ),
        DetectionParamSchema(
            name="binning_method",
            display_name="Binning Method",
            value_type=DetectionValueType.ENUM,
            default="mean",
            choices=("mean", "median"),
            description="Window reducer across rows before edge detection.",
            methods=_SHARED,
        ),
        DetectionParamSchema(
            name="polarity",
            display_name="Polarity",
            value_type=DetectionValueType.ENUM,
            default="bright_on_dark",
            choices=("bright_on_dark", "dark_on_bright"),
            description="Intensity polarity; dark_on_bright inverts the profile.",
            methods=_SHARED,
        ),
        DetectionParamSchema(
            name="diameter_method",
            display_name="Detection Method",
            value_type=DetectionValueType.ENUM,
            default="threshold_width",
            choices=("threshold_width", "gradient_edges"),
            description="Core detector implementation.",
        ),
        DetectionParamSchema(
            name="post_filter_kernel_size",
            display_name="Post-Filter Kernel Size",
            value_type=DetectionValueType.INT,
            default=3,
            description=(
                "Odd median kernel applied to diameter after detection. "
                "Post-detection smoothing; re-run analysis to apply changes."
            ),
        ),
        DetectionParamSchema(
            name="threshold_mode",
            display_name="Threshold Mode",
            value_type=DetectionValueType.ENUM,
            default="half_max",
            choices=("half_max", "absolute"),
            description="Threshold rule for threshold_width.",
            methods=("threshold_width",),
        ),
        DetectionParamSchema(
            name="threshold_value",
            display_name="Threshold Value",
            value_type=DetectionValueType.FLOAT,
            default=0.0,
            description="Absolute threshold when threshold_mode='absolute'.",
            methods=("threshold_width",),
        ),
        DetectionParamSchema(
            name="gradient_sigma",
            display_name="Gradient Sigma",
            value_type=DetectionValueType.FLOAT,
            default=1.5,
            description="Gaussian smoothing sigma for gradient edge finding.",
            methods=("gradient_edges",),
        ),
        DetectionParamSchema(
            name="gradient_kernel",
            display_name="Gradient Kernel",
            value_type=DetectionValueType.ENUM,
            default="central_diff",
            choices=("central_diff",),
            description="Derivative kernel for gradient_edges.",
            methods=("gradient_edges",),
        ),
        DetectionParamSchema(
            name="gradient_min_edge_strength",
            display_name="Min Edge Strength",
            value_type=DetectionValueType.FLOAT,
            default=0.02,
            description="Minimum derivative magnitude for a confident edge.",
            methods=("gradient_edges",),
        ),
        DetectionParamSchema(
            name="enable_motion_gating",
            display_name="Enable Motion Gating",
            value_type=DetectionValueType.BOOL,
            default=True,
            description="Apply frame-to-frame motion constraints for gradient_edges.",
            methods=("gradient_edges",),
        ),
        DetectionParamSchema(
            name="max_edge_shift_um",
            display_name="Max Edge Shift (um)",
            value_type=DetectionValueType.FLOAT,
            default=2.0,
            description="Maximum allowed per-frame left/right edge shift.",
            methods=("gradient_edges",),
        ),
        DetectionParamSchema(
            name="max_diameter_change_um",
            display_name="Max Diameter Change (um)",
            value_type=DetectionValueType.FLOAT,
            default=2.0,
            description="Maximum allowed per-frame diameter jump.",
            methods=("gradient_edges",),
        ),
        DetectionParamSchema(
            name="max_center_shift_um",
            display_name="Max Center Shift (um)",
            value_type=DetectionValueType.FLOAT,
            default=2.0,
            description="Maximum allowed per-frame center shift.",
            methods=("gradient_edges",),
        ),
    )

    def __init__(
        self,
        *,
        channel: int,
        roi_id: int,
        detection_params: dict[str, object] | None = None,
    ) -> None:
        """Create a diameter analysis instance.

        Args:
            channel: Channel index for analysis.
            roi_id: ROI identifier for analysis.
            detection_params: Optional detection parameters.
        """
        super().__init__(channel=channel, roi_id=roi_id, detection_params=detection_params)
        self._use_threads = True
        self._max_workers: int | None = None

    def set_execution_options(
        self,
        *,
        use_threads: bool = True,
        max_workers: int | None = None,
    ) -> None:
        """Set runtime execution options for the next run.

        Args:
            use_threads: Whether to use a thread pool for per-row analysis.
            max_workers: Optional worker count. ``None`` uses executor default.

        Returns:
            None.
        """
        self._use_threads = bool(use_threads)
        self._max_workers = None if max_workers is None else int(max_workers)

    def run(
        self,
        data_provider: AnalysisDataProvider,
        *,
        context: AnalysisRunContext | None = None,
        dependencies: dict[str, BaseAnalysis] | None = None,
    ) -> AnalysisResult:
        """Run diameter analysis on one ROI crop.

        Args:
            data_provider: Provider for ROI image data and physical units.
            context: Optional progress/cancellation context.
            dependencies: Unused for diameter analysis.

        Returns:
            Populated analysis result.

        Raises:
            AnalysisCancelled: If the run is cancelled.
        """
        _ = dependencies
        context = context or AnalysisRunContext()
        context.raise_if_cancelled()
        image = data_provider.get_roi_image(channel=self.key.channel, roi_id=self.key.roi_id)
        physical_units = data_provider.get_image_physical_units()

        try:
            result = run_diameter(
                image,
                detection_params=dict(self.detection_params),
                physical_units=physical_units,
                progress_callback=context.report_progress,
                cancel_callback=context.is_cancelled,
                use_threads=self._use_threads,
                max_workers=self._max_workers,
            )
        except DiameterCancelled as exc:
            raise AnalysisCancelled(str(exc)) from exc

        self.result.summary = result.summary
        self.result.table = result.table
        self.set_dirty()
        return self.result

    def get_plot_data(self) -> AnalysisPlotData | None:
        """Return diameter-vs-time plot data in ROI-local coordinates.

        Returns:
            Plot data for filtered diameter versus time, or None when empty.
        """
        if self.result.table is None or self.result.table.empty:
            return None
        table = self.result.table
        y_col = (
            "diameter_um_filt"
            if "diameter_um_filt" in table.columns
            and table["diameter_um_filt"].notna().any()
            else "diameter_um"
        )
        mask = table["time_s"].notna() & table[y_col].notna()
        if not mask.any():
            return None
        return AnalysisPlotData(
            x=tuple(float(v) for v in table.loc[mask, "time_s"]),
            y=tuple(float(v) for v in table.loc[mask, y_col]),
            x_label="Time (s)",
            y_label="Diameter (um)",
            series_name="Diameter",
        )

    def get_overlay_traces(self) -> tuple[AnalysisOverlayTraceData, ...]:
        """Return left/right edge traces in ROI-local physical coordinates.

        Returns:
            Overlay traces for left and right vessel edges.
        """
        if self.result.table is None or self.result.table.empty:
            return ()
        table = self.result.table
        mask = table["time_s"].notna()
        if not mask.any():
            return ()

        def _trace(trace_id: str, y_col: str, name: str, color: str) -> AnalysisOverlayTraceData | None:
            if y_col not in table.columns:
                return None
            row_mask = mask & table[y_col].notna()
            if not row_mask.any():
                return None
            return AnalysisOverlayTraceData(
                trace_id=trace_id,
                x=tuple(float(v) for v in table.loc[row_mask, "time_s"]),
                y=tuple(float(v) for v in table.loc[row_mask, y_col]),
                color=color,
                name=name,
            )

        traces: list[AnalysisOverlayTraceData] = []
        left = _trace("diameter_left_edge", "left_edge_um", "Left edge", "cyan")
        right = _trace("diameter_right_edge", "right_edge_um", "Right edge", "magenta")
        if left is not None:
            traces.append(left)
        if right is not None:
            traces.append(right)
        return tuple(traces)
