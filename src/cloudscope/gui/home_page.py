"""NiceGUI home page for CloudScope."""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from acqstore.acq_image.acq_image_list import AcqImageList
from cloudscope.core.controller import HomePageController
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import (
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
)
from cloudscope.gui.file_list_view import AcqImageListTableView, DEFAULT_ACQ_IMAGE_FOLDER
from cloudscope.gui.image_toolbar_view import ImageToolbarView
from cloudscope.gui.metadata_widget.metadata_view import MetadataView
from cloudscope.gui.header_view import build_main_header
from cloudscope.gui.selection_footer_view import SelectionFooterView


class PlotlyImagePanel:
    """Minimal Plotly-backed image panel."""

    def __init__(self, event_bus: EventBus, title: str) -> None:
        """Create the image panel.

        Args:
            event_bus: CloudScope event bus.
            title: Panel title.
        """
        self._event_bus = event_bus
        self._title = title
        self._plot = None
        self._summary = None
        self._file_id: str | None = None
        self._channel: int | None = None
        self._roi_id: int | None = None
        self._event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed)
        self._event_bus.subscribe(ChannelSelectionChanged, self._on_channel_selection_changed)
        self._event_bus.subscribe(RoiSelectionChanged, self._on_roi_selection_changed)

    def build(self) -> None:
        """Build the panel UI.

        Returns:
            None.
        """
        with ui.card().classes("w-full"):
            ui.label(self._title).classes("text-lg font-medium")
            self._summary = ui.label("No selection").classes("text-sm text-gray-600")
            self._plot = ui.plotly(
                self._make_figure(file_id=None, channel=None, roi_id=None)
            ).classes("w-full h-80")

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        """Reset tracked selection from a file change (includes default channel/ROI)."""
        self._file_id = event.file_id
        self._channel = event.channel
        self._roi_id = event.roi_id
        self._redraw()

    def _on_channel_selection_changed(self, event: ChannelSelectionChanged) -> None:
        """Patch channel from a narrow selection event."""
        self._channel = event.channel
        self._redraw()

    def _on_roi_selection_changed(self, event: RoiSelectionChanged) -> None:
        """Patch ROI from a narrow selection event."""
        self._roi_id = event.roi_id
        self._redraw()

    def _redraw(self) -> None:
        """Refresh summary and plot from cached selection."""
        if self._summary is not None:
            self._summary.text = (
                f"file={self._file_id!r}, channel={self._channel!r}, roi={self._roi_id!r}"
            )
        if self._plot is not None:
            self._plot.figure = self._make_figure(
                file_id=self._file_id,
                channel=self._channel,
                roi_id=self._roi_id,
            )
            self._plot.update()

    def _make_figure(self, file_id: str | None, channel: int | None, roi_id: int | None) -> dict:
        """Build a placeholder Plotly figure.

        Args:
            file_id: Selected file identifier.
            channel: Selected channel.
            roi_id: Selected ROI identifier.

        Returns:
            Plotly figure dictionary.
        """
        x_values = [0, 1, 2, 3, 4]
        base = 0 if channel is None else channel + 1
        y_values = [base, base + 1, base + 0.5, base + 1.5, base + 1]
        title = f"{self._title}: {file_id or 'no file'}"
        if roi_id is not None:
            title += f" / {roi_id}"
        return {
            "data": [
                {
                    "type": "scatter",
                    "mode": "lines+markers",
                    "x": x_values,
                    "y": y_values,
                    "name": file_id or "none",
                }
            ],
            "layout": {
                "title": {"text": title},
                "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
            },
        }


@dataclass(slots=True)
class HomePage:
    """Compose the home page and its per-page objects."""

    controller: HomePageController
    event_bus: EventBus

    def build(self) -> None:
        """Build the page UI and load initial AcqStore state.

        Returns:
            None.
        """
        acq_image_list = AcqImageList(DEFAULT_ACQ_IMAGE_FOLDER)

        file_list_panel = AcqImageListTableView(
            event_bus=self.event_bus,
            acq_image_list=acq_image_list,
        )
        image_toolbar = ImageToolbarView(event_bus=self.event_bus)
        metadata_view = MetadataView(event_bus=self.event_bus)
        primary_image = PlotlyImagePanel(self.event_bus, title="Primary image")
        reference_image = PlotlyImagePanel(self.event_bus, title="Reference image")
        selection_footer = SelectionFooterView(event_bus=self.event_bus)
        # KymFlow ``HomePage.render`` order: ``build_header``, ``_footer_view.render()``,
        # then main body (splitter/column). Header + footer must be top-level layout
        # elements before nested content — see NiceGUI page layout / Quasar ``q-layout``.
        ui.page_title("CloudScope")
        build_main_header(title="CloudScope")
        selection_footer.build()

        with ui.splitter(value=28).classes("w-full min-h-screen") as splitter:

            with splitter.before:
                with ui.column().classes("w-full gap-4 p-4"):
                    with ui.card().classes("w-full"):
                        metadata_view.build()

            with splitter.after:
                with ui.column().classes("w-full gap-4 p-4"):
                    ui.label("CloudScope").classes("text-2xl font-bold")

                    with ui.row().classes("w-full items-start gap-4"):
                        with ui.card().classes("w-1/2").style("height: 32rem;"):
                            ui.label("Files").classes("text-lg font-medium")
                            file_list_panel.build()

                        with ui.card().classes("w-1/2"):
                            image_toolbar.build()

                    primary_image.build()
                    reference_image.build()

        self.controller.bind()
        self.controller.load_acq_image_list(acq_image_list)


@ui.page("/")
def home_page() -> None:
    """Create all per-page objects for the CloudScope home page.

    Returns:
        None.
    """
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    page = HomePage(controller=controller, event_bus=event_bus)
    page.build()
