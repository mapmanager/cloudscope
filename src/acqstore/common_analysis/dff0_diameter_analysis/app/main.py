"""Standalone NiceGUI app for interactive triggered-event exploration."""

from __future__ import annotations

from pathlib import Path

from nicegui import ui

# from ..analysis import Dff0DiameterAnalysis
# from ..models import EventDirection, SignalFilterMethod, TriggeredEventParams
# from ..plotting import build_event_figure, build_metric_vs_time_figure, build_overview_figure

from acqstore.common_analysis.dff0_diameter_analysis.analysis import (
    Dff0DiameterAnalysis,
)
from acqstore.common_analysis.dff0_diameter_analysis.models import (
    EventDirection,
    SignalFilterMethod,
    TriggeredEventParams,
)
from acqstore.common_analysis.dff0_diameter_analysis.plotting import (
    build_event_figure,
    build_metric_vs_time_figure,
    build_overview_figure,
)


DEFAULT_BASE_DIR = Path(
    "/Users/cudmore/Library/Application Support/cloudscope/sample-data/"
    "diameter-sample-data-v1/diameter-sample-data/Control"
)
DEFAULT_FILE_NAME = "220110n_0005.tif"


class AppState:
    """Mutable app state kept separate from scientific analysis models."""

    def __init__(self) -> None:
        self.analysis: Dff0DiameterAnalysis | None = None
        self.plot_container = None


state = AppState()


def _sidecar_paths(base_dir: Path, file_name: str) -> tuple[Path, Path, Path]:
    frames_dir = base_dir / f"{file_name}.frames"
    return (
        frames_dir / f"{file_name}.diameter.csv",
        frames_dir / f"{file_name}.sum_intensity.csv",
        frames_dir / f"{file_name}.json",
    )


def _replot() -> None:
    """Rebuild the analysis and all Plotly figures from current controls."""
    assert state.plot_container is not None
    diameter_csv, reporter_csv, analysis_json = _sidecar_paths(
        Path(base_dir_input.value), str(file_name_input.value)
    )
    params = TriggeredEventParams(
        direction=EventDirection(direction_select.value),
        pre_points=int(pre_points_input.value),
        post_points=int(post_points_input.value),
        post_search_window_points=int(post_search_points_input.value),
        baseline_start_offset_points=int(baseline_start_input.value),
        baseline_stop_offset_points=int(baseline_stop_input.value),
        filter_method=SignalFilterMethod(filter_select.value),
        median_kernel_points=int(median_kernel_input.value),
        savgol_window_points=int(savgol_window_input.value),
        savgol_polyorder=int(savgol_order_input.value),
        recovery_fraction=float(recovery_fraction_input.value),
    )
    state.analysis = Dff0DiameterAnalysis.from_sidecars(
        diameter_csv=diameter_csv,
        reporter_csv=reporter_csv,
        analysis_json=analysis_json,
        channel=int(channel_input.value),
        roi_id=int(roi_input.value),
        triggered_event_params=params,
    )
    max_event = max(0, len(state.analysis.triggered_events) - 1)
    event_index_input.set_value(min(int(event_index_input.value), max_event))

    state.plot_container.clear()
    with state.plot_container:
        ui.label(str(state.analysis.get_alignment_summary()))
        ui.plotly(build_overview_figure(state.analysis)).classes("w-full")
        ui.plotly(
            build_event_figure(state.analysis, int(event_index_input.value))
        ).classes("w-full")
        ui.plotly(
            build_metric_vs_time_figure(
                state.analysis, str(metric_select.value)
            )
        ).classes("w-full")


ui.label("DFF0 / Diameter Triggered Event Analysis").classes("text-h5")
with ui.column().classes("w-full gap-2"):
    base_dir_input = ui.input("Base data folder", value=str(DEFAULT_BASE_DIR)).classes("w-full")
    file_name_input = ui.input("Raw file name", value=DEFAULT_FILE_NAME)
    with ui.row():
        channel_input = ui.number("Channel", value=0, min=0, precision=0)
        roi_input = ui.number("ROI", value=1, min=0, precision=0)
        event_index_input = ui.number("Event index", value=0, min=0, precision=0)
    with ui.row():
        direction_select = ui.select([item.value for item in EventDirection], value=EventDirection.NEGATIVE.value, label="Direction")
        filter_select = ui.select([item.value for item in SignalFilterMethod], value=SignalFilterMethod.MEDIAN.value, label="Filter")
        median_kernel_input = ui.number("Median kernel points", value=3, min=1, precision=0)
        savgol_window_input = ui.number("Sav-Gol window points", value=11, min=3, precision=0)
        savgol_order_input = ui.number("Sav-Gol order", value=3, min=0, precision=0)
    with ui.row():
        pre_points_input = ui.number("Pre points", value=50, min=0, precision=0)
        post_points_input = ui.number("Post points", value=500, min=1, precision=0)
        post_search_points_input = ui.number("Extremum search points", value=250, min=1, precision=0)
        baseline_start_input = ui.number("Baseline start offset", value=-50, precision=0)
        baseline_stop_input = ui.number("Baseline stop offset", value=0, precision=0)
        recovery_fraction_input = ui.number("Recovery fraction", value=0.9, min=0.01, max=1.0, step=0.05)
    metric_select = ui.select(
        [
            "baseline_value",
            "baseline_slope_per_sec",
            "amplitude",
            "time_to_extremum_from_seed_sec",
            "extremum_to_recovery_sec",
            "baseline_adjusted_auc_seed_to_stop",
        ],
        value="time_to_extremum_from_seed_sec",
        label="Metric versus recording time",
    )
    ui.button("Replot", on_click=_replot)
    state.plot_container = ui.column().classes("w-full")

ui.run()
