"""Run and plot one sum-intensity analysis from example data.

Edit the constants near the top of the file before running.

Run:

    uv run python scripts/acqstore/try_sum_intensity_analysis.py
"""

from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go

from acqstore.acq_image import AcqImage
from acqstore.acq_image.analysis.sum_intensity_analysis.sum_intensity_analysis import (
    SumIntensityAnalysis,
)
from acqstore.acq_image.analysis.model import AnalysisRunContext, BaseAnalysis
from acqstore.utils.logging import get_logger, setup_logging

logger = get_logger(__name__)
setup_logging()

# Edit this path locally. The ROI defaults to the full image.
SOURCE_PATH = Path("/Users/cudmore/Dropbox/data/rabbit-ca-variance/raw-data/jan-12-2022/Control/220110n_0003.tif.frames/220110n_0003.tif")

SUM_INTENSITY_PRESETS: dict[str, dict[str, object]] = {
    "fast": {
        "window_radius_points": 0,
        "filter_method": "median",
        "median_filter_kernel_points": 3,
        "detrend_method": "single_exponential",
        "baseline_method": "percentile",
        "baseline_percentile": 20.0,
        "baseline_min_value": 1e-12,
        "detection_method": "derivative_threshold",
        "derivative_threshold": 1.0,
        "refractory_period_ms": 10.0,
        "peak_search_window_ms": 50.0,
    },
    "slow": {
        "window_radius_points": 8,
        "filter_method": "median",
        "median_filter_kernel_points": 3,
        "detrend_method": "single_exponential",
        "baseline_method": "percentile",
        "baseline_percentile": 20.0,
        "baseline_min_value": 1e-12,
        "detection_method": "derivative_threshold",
        "derivative_threshold": 1.0,
        "refractory_period_ms": 500.0,
        "peak_search_window_ms": 250.0,
    },
}


def run_sum_intensity_analysis(acq_image: AcqImage, preset_name: str) -> SumIntensityAnalysis:
    """Create and run sum-intensity analysis on one file.

    Args:
        acq_image: Acquisition image.
        preset_name: Key in :data:`SUM_INTENSITY_PRESETS`.

    Returns:
        Completed sum-intensity analysis.

    Raises:
        KeyError: If preset name is unknown.
    """
    channel = 0
    roi = acq_image.rois.create_rect_roi(name="sum_intensity_test", note="sum intensity test")
    context = AnalysisRunContext(
        progress_callback=lambda fraction, message: print(f"  progress={fraction}: {message}")
    )
    analysis = acq_image.analysis_set.create_and_run(
        SumIntensityAnalysis,
        channel=channel,
        roi_id=roi.roi_id,
        detection_params=SUM_INTENSITY_PRESETS[preset_name],
        replace_existing=True,
        context=context,
    )
    if not isinstance(analysis, SumIntensityAnalysis):
        raise TypeError(f"Expected SumIntensityAnalysis, got {type(analysis).__name__}")
    return analysis


def plot_sum_intensity_results(analysis: BaseAnalysis) -> None:
    """Plot trace, derivative, onsets, and peaks with Plotly.

    Args:
        analysis: Completed sum-intensity analysis.
        output_html: HTML file to write.

    Returns:
        None.
    """
    if analysis.result.table is None:
        raise ValueError("analysis has no result table")

    table = analysis.result.table

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=table["time_sec"],
            y=table["norm_sum_intensity"],
            mode="lines",
            name="norm_sum_intensity",
            visible="legendonly",
        )
    )
    if "dff_signal" in table.columns:
        fig.add_trace(
            go.Scatter(
                x=table["time_sec"],
                y=table["dff_signal"],
                mode="lines",
                name="dff_signal",
                visible="legendonly",
            )
        )
    fig.add_trace(
        go.Scatter(
            x=table["time_sec"],
            y=table["detection_signal"],
            mode="lines",
            name="detection_signal",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=table["time_sec"],
            y=table["d_detection_signal"],
            mode="lines",
            name="d_detection_signal",
            yaxis="y2",
        )
    )

    onset_rows = table[table["is_onset"]]
    peak_rows = table[table["is_peak"]]
    fig.add_trace(
        go.Scatter(
            x=onset_rows["time_sec"],
            y=onset_rows["detection_signal"],
            mode="markers",
            name="onsets",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=peak_rows["time_sec"],
            y=peak_rows["detection_signal"],
            mode="markers",
            name="peaks",
        )
    )
    f0_baseline = analysis.result.summary.get("f0_baseline")
    baseline_method = analysis.result.summary.get("baseline_method")
    baseline_percentile = analysis.result.summary.get("baseline_percentile")
    annotation = (
        f"F0={float(f0_baseline):.6g} "
        f"({baseline_method}, p={float(baseline_percentile):.1f})"
        if f0_baseline is not None and baseline_percentile is not None
        else "F0 unavailable"
    )
    fig.update_layout(
        title="CloudScope sum intensity analysis",
        xaxis_title="Time (s)",
        yaxis_title="dF/F0",
        yaxis2={"title": "dF/F0/s", "overlaying": "y", "side": "right"},
        annotations=[
            {
                "text": annotation,
                "xref": "paper",
                "yref": "paper",
                "x": 0.01,
                "y": 0.99,
                "showarrow": False,
                "align": "left",
                "bgcolor": "rgba(255,255,255,0.7)",
            }
        ],
    )

    # fig.write_html(output_html)
    # print(f"wrote {output_html}")
    fig.show()


def main() -> None:
    """Run the manual single-file sum-intensity workflow.

    Returns:
        None.
    """
    print("Sum-intensity detection schema:")
    for field in SumIntensityAnalysis.get_detection_schema():
        print(
            f"  {field.name}: default={field.default!r}, "
            f"type={field.value_type.value}, unit={field.unit}, choices={field.choices}"
        )

    acq_image = AcqImage(SOURCE_PATH)
    analysis = run_sum_intensity_analysis(acq_image, preset_name="slow")
    print("Analysis key:", analysis.key)
    
    print("Summary:")
    from pprint import pprint
    pprint(analysis.result.summary)

    print("Columns:", analysis.get_table_columns())
    print("Detected peaks:", len(analysis.get_peak_events()))
    plot_sum_intensity_results(analysis)


if __name__ == "__main__":
    main()
