"""Plotly figures for paired reporter and diameter inspection."""

from __future__ import annotations

from plotly import graph_objects as go
from plotly.subplots import make_subplots

from .models import Dff0DiameterDataset


def make_overview_figure(
    dataset: Dff0DiameterDataset,
    *,
    x_start_sec: float | None = None,
    x_stop_sec: float | None = None,
    show_raw_diameter: bool = True,
) -> go.Figure:
    """Build linked reporter and diameter traces with reporter onsets.

    Args:
        dataset: Loaded paired dataset.
        x_start_sec: Optional visible x-axis start in seconds.
        x_stop_sec: Optional visible x-axis stop in seconds.
        show_raw_diameter: Include raw diameter beneath the filtered trace.

    Returns:
        New Plotly figure. The figure is rebuilt on every call.
    """
    reporter = dataset.reporter
    diameter = dataset.diameter
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("Reporter ΔF/F₀", "Diameter"),
    )
    figure.add_trace(
        go.Scatter(
            x=reporter["time_sec"],
            y=reporter["df_f_signal"],
            mode="lines",
            name="df/f0",
        ),
        row=1,
        col=1,
    )
    if show_raw_diameter:
        figure.add_trace(
            go.Scatter(
                x=diameter["time_s"],
                y=diameter["diameter_um_raw"],
                mode="lines",
                name="diameter raw",
                opacity=0.45,
            ),
            row=2,
            col=1,
        )
    figure.add_trace(
        go.Scatter(
            x=diameter["time_s"],
            y=diameter["diameter_um_analysis"],
            mode="lines",
            name="diameter filtered",
        ),
        row=2,
        col=1,
    )

    onset_times = [event.onset_time_sec for event in dataset.events]
    onset_values = [event.onset_value for event in dataset.events]
    onset_diameter = [
        float(diameter.iloc[event.onset_index]["diameter_um_analysis"])
        for event in dataset.events
    ]
    figure.add_trace(
        go.Scatter(
            x=onset_times,
            y=onset_values,
            mode="markers",
            name="reporter onset",
            marker={"size": 9, "symbol": "circle-open"},
        ),
        row=1,
        col=1,
    )
    figure.add_trace(
        go.Scatter(
            x=onset_times,
            y=onset_diameter,
            mode="markers",
            name="onset projected to diameter",
            marker={"size": 9, "symbol": "circle-open"},
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    figure.update_yaxes(title_text="ΔF/F₀", row=1, col=1)
    figure.update_yaxes(title_text="Diameter (µm)", row=2, col=1)
    figure.update_xaxes(title_text="Time (s)", row=2, col=1)
    if x_start_sec is not None or x_stop_sec is not None:
        start = 0.0 if x_start_sec is None else x_start_sec
        stop = float(reporter["time_sec"].iloc[-1]) if x_stop_sec is None else x_stop_sec
        figure.update_xaxes(range=[start, stop])

    figure.update_layout(
        title=(
            f"{dataset.source_name} — channel {dataset.selection.channel}, "
            f"ROI {dataset.selection.roi_id}"
        ),
        height=750,
        hovermode="x unified",
    )
    return figure
