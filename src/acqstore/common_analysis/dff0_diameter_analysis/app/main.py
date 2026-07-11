"""Standalone NiceGUI app for interactive triggered-event exploration."""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from nicegui import ui

from acqstore.acq_image.acq_image_list import AcqImageList
from acqstore.common_analysis.dff0_diameter_analysis.analysis import (
    Dff0DiameterAnalysis,
)
from acqstore.common_analysis.dff0_diameter_analysis.app.analysis_hits import (
    find_analysis_hits,
)
from acqstore.common_analysis.dff0_diameter_analysis.app.app_state import AppState
from acqstore.common_analysis.dff0_diameter_analysis.app.left_control_panel import (
    LeftControlPanel,
)
from acqstore.common_analysis.dff0_diameter_analysis.app.plot_panel import PlotPanel


# SOURCE_PATH = Path(
#     "/Users/cudmore/Library/Application Support/cloudscope/sample-data/"
#     "diameter-sample-data-v1/diameter-sample-data"
# )

SOURCE_PATH = Path(
    "/Users/cudmore/Sites/cloudscope-data/data-samples/diameter-sample-data"
)

NATIVE = False
NATIVE_WINDOW_SIZE = (1000, 800)


@dataclass(slots=True)
class PageContext:
    """Bind page state to reusable controls and plots for callbacks.

    Args:
        state: Mutable analysis state for one page instance.
    """

    state: AppState
    controls: LeftControlPanel | None = None
    plots: PlotPanel | None = None


def handle_hit_row_clicked(event: Any, *, context: PageContext) -> None:
    """Update app state and controls after an AG Grid row click.

    Args:
        event: NiceGUI event containing the selected row's ``data`` mapping.
        context: Page-local state and component references.
    """
    if context.controls is None:
        return

    row_data = event.args.get("data") if isinstance(event.args, dict) else None
    if not isinstance(row_data, dict):
        ui.notify("The selected grid row did not contain row data.", type="warning")
        return

    hit_id = row_data.get("hit_id")
    if not isinstance(hit_id, str):
        ui.notify("The selected grid row did not contain a hit identifier.", type="warning")
        return

    try:
        hit = context.state.select_hit(hit_id)
    except KeyError:
        ui.notify("The selected analysis hit is no longer available.", type="negative")
        return

    context.controls.set_selected_hit(hit)


def handle_plot_requested(*, context: PageContext) -> None:
    """Run and plot the currently selected AcqImage analysis hit.

    Args:
        context: Page-local state and component references.
    """
    controls = context.controls
    plots = context.plots
    if controls is None or plots is None:
        return

    hit = context.state.selected_hit
    if hit is None:
        ui.notify("Select an analysis row before plotting.", type="warning")
        return

    try:
        analysis = Dff0DiameterAnalysis.from_acq_image(
            acq_image=hit.acq_image,
            channel=hit.channel,
            roi_id=hit.roi_id,
            triggered_event_params=controls.get_triggered_event_params(),
        )
        if not analysis.triggered_events:
            raise ValueError("The selected analysis contains no reporter seed events.")

        max_event_index = len(analysis.triggered_events) - 1
        event_index = min(max(controls.get_event_index(), 0), max_event_index)
        controls.set_event_index(event_index)

        context.state.analysis = analysis
        plots.show_analysis(
            analysis,
            event_index=event_index,
            metric_name=controls.get_metric_name(),
        )
    except (TypeError, ValueError, KeyError) as exc:
        context.state.analysis = None
        plots.show_error(str(exc))
        ui.notify(str(exc), type="negative")


def load_app_state(source_path: Path) -> AppState:
    """Load acquisitions and discover all paired analysis hits.

    Args:
        source_path: Folder containing acquisition files and analysis sidecars.

    Returns:
        Initialized page state.
    """
    acq_image_list = AcqImageList(
        str(source_path),
        load_images=False,
        load_analysis_csv=True,
    )
    return AppState(
        acq_image_list=acq_image_list,
        analysis_hits=find_analysis_hits(acq_image_list),
    )


@ui.page("/")
def home_page() -> None:
    """Build the standalone two-pane analysis page."""
    
    from nicewidgets.gui_defaults import setUpGuiDefaults
    setUpGuiDefaults(text_size='text-xs')

    try:
        state = load_app_state(SOURCE_PATH)
    except (OSError, RuntimeError, ValueError) as exc:
        ui.label("Unable to load acquisition folder").classes("text-h5 text-negative")
        ui.label(str(exc))
        ui.label(str(SOURCE_PATH)).classes("text-caption")
        return

    context = PageContext(state=state)

    ui.label("DFF0 / Diameter Triggered Event Analysis").classes("text-h5 px-3 pt-3")
    ui.label(f"Source: {SOURCE_PATH}").classes("text-caption px-3")
    ui.label(f"Paired analysis hits: {len(state.analysis_hits)}").classes("text-caption px-3")

    with ui.splitter(value=32).classes("w-full h-[calc(100vh-90px)]") as splitter:
        with splitter.before:
            context.controls = LeftControlPanel(
                hits=state.analysis_hits,
                on_row_clicked=partial(handle_hit_row_clicked, context=context),
                on_plot_requested=partial(handle_plot_requested, context=context),
            )

        with splitter.after:
            context.plots = PlotPanel()


def run_app(*, native: bool = NATIVE) -> None:
    """Run the NiceGUI app in browser or native desktop mode.

    Args:
        native: When true, launch a native window with the configured size.
    """
    run_kwargs: dict[str, object] = {}
    if native:
        run_kwargs.update(native=True, window_size=NATIVE_WINDOW_SIZE)
    ui.run(**run_kwargs)


if __name__ in {"__main__", "__mp_main__"}:
    run_app()
