"""Minimal NiceGUI explorer for the paired sidecar analysis.

Run from the CloudScope repository root with::

    uv run python -m acqstore.common_analysis.dff0_diameter_analysis.app.main
"""

from __future__ import annotations

from pathlib import Path

from nicegui import ui

from ..analysis import Dff0DiameterAnalysis
from ..plotting import make_overview_figure


_SAMPLE_DIR = Path(
    "/Users/cudmore/Library/Application Support/cloudscope/sample-data/"
    "diameter-sample-data-v1/diameter-sample-data/Control/"
    "220110n_0005.tif.frames"
)
_DIAMETER_CSV = _SAMPLE_DIR / "220110n_0005.tif.diameter.csv"
_REPORTER_CSV = _SAMPLE_DIR / "220110n_0005.tif.sum_intensity.csv"
_ANALYSIS_JSON = _SAMPLE_DIR / "220110n_0005.tif.json"


@ui.page("/")
def index() -> None:
    """Build the standalone exploratory page."""
    ui.label("ΔF/F₀–Diameter Analysis Explorer").classes("text-h5")

    with ui.row().classes("items-end"):
        channel = ui.number("Channel", value=0, min=0, step=1)
        roi_id = ui.number("ROI", value=1, min=0, step=1)
        filter_method = ui.select(
            ["none", "median"], value="median", label="Diameter filter"
        )
        kernel_points = ui.number(
            "Kernel points", value=3, min=1, step=2
        )
        x_start = ui.number("X start (s)", value=0.0, min=0.0, step=0.1)
        x_stop = ui.number("X stop (s)", value=11.0, min=0.0, step=0.1)
        show_raw = ui.checkbox("Show raw diameter", value=True)

    status = ui.label()
    plot_container = ui.column().classes("w-full")

    def replot() -> None:
        """Reload sidecars and replace the complete Plotly figure."""
        try:
            analysis = Dff0DiameterAnalysis.from_sidecars(
                diameter_csv=_DIAMETER_CSV,
                reporter_csv=_REPORTER_CSV,
                analysis_json=_ANALYSIS_JSON,
                channel=int(channel.value or 0),
                roi_id=int(roi_id.value or 0),
                diameter_filter_method=str(filter_method.value),
                diameter_filter_kernel_points=int(kernel_points.value or 1),
            )
            figure = make_overview_figure(
                analysis.dataset,
                x_start_sec=float(x_start.value) if x_start.value is not None else None,
                x_stop_sec=float(x_stop.value) if x_stop.value is not None else None,
                show_raw_diameter=bool(show_raw.value),
            )
            plot_container.clear()
            with plot_container:
                ui.plotly(figure).classes("w-full")
            summary = analysis.get_alignment_summary()
            status.set_text(
                f"Loaded {summary['num_points']} points, "
                f"{summary['num_reporter_events']} reporter events, "
                f"dt={summary['seconds_per_point']:.7f} s"
            )
        except Exception as error:  # exploratory app: surface complete error text
            status.set_text(f"Error: {error}")

    ui.button("Replot", on_click=replot)
    replot()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="ΔF/F₀–Diameter Analysis")
