"""NiceGUI home page for CloudScope."""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from cloudscope.core.controller import HomePageController
from cloudscope.core.event_bus import EventBus
from cloudscope.core.events import FileListChanged, PrimarySelectionChanged, SelectChannelIntent, SelectFileIntent, SelectRoiIntent


class FileListPanel:
    """Simple file list view that emits file-selection intents."""

    _my_name = 'FileListPanel'

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._select: ui.select | None = None
        self._event_bus.subscribe(FileListChanged, self._on_file_list_changed)
        self._event_bus.subscribe(PrimarySelectionChanged, self._on_selection_changed)

    def build(self) -> None:
        with ui.card().classes('w-72'):
            ui.label(self._my_name).classes('text-lg font-medium')
            self._select = ui.select(
                options={},
                label='Selected file',
                on_change=lambda e: self._event_bus.publish(SelectFileIntent(file_id=e.value)),
            ).classes('w-full')

    def _on_file_list_changed(self, event: FileListChanged) -> None:
        if self._select is None:
            return
        self._select.options = {file_id: file_id for file_id in event.file_ids}
        self._select.update()

    def _on_selection_changed(self, event: PrimarySelectionChanged) -> None:
        if self._select is None:
            return
        self._select.value = event.file_id
        self._select.update()


class SelectionToolbar:
    """Toolbar for channel and ROI selections."""

    _my_name = 'SelectionToolbar'

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._channel: ui.radio | None = None
        self._roi: ui.select | None = None
        self._event_bus.subscribe(PrimarySelectionChanged, self._on_selection_changed)

    def build(self) -> None:
        with ui.card().classes('w-full'):
            ui.label(self._my_name).classes('text-lg font-medium')
            with ui.row().classes('items-center gap-6 w-full'):
                self._channel = ui.radio(
                    options={0: '1', 1: '2', 2: '3'},
                    value=0,
                    on_change=lambda e: self._event_bus.publish(SelectChannelIntent(channel=e.value)),
                )
                self._roi = ui.select(
                    options={'roi-1': 'ROI 1', 'roi-2': 'ROI 2', None: 'None'},
                    label='ROI',
                    value=None,
                    on_change=lambda e: self._event_bus.publish(SelectRoiIntent(roi_id=e.value)),
                ).classes('w-48')

    def _on_selection_changed(self, event: PrimarySelectionChanged) -> None:
        if self._channel is not None:
            self._channel.value = event.channel
            self._channel.update()
        if self._roi is not None:
            self._roi.value = event.roi_id
            self._roi.update()


class PlotlyImagePanel:
    """Minimal Plotly-backed image panel."""

    def __init__(self, event_bus: EventBus, title: str) -> None:
        self._event_bus = event_bus
        self._title = title
        self._plot = None
        self._summary = None
        self._event_bus.subscribe(PrimarySelectionChanged, self._on_selection_changed)

    def build(self) -> None:
        with ui.card().classes('w-full'):
            ui.label(self._title).classes('text-lg font-medium')
            self._summary = ui.label('No selection').classes('text-sm text-gray-600')
            self._plot = ui.plotly(self._make_figure(file_id=None, channel=None, roi_id=None)).classes('w-full h-80')

    def _on_selection_changed(self, event: PrimarySelectionChanged) -> None:
        if self._summary is not None:
            self._summary.text = (
                f'file={event.file_id!r}, channel={event.channel!r}, roi={event.roi_id!r}'
            )
        if self._plot is not None:
            self._plot.figure = self._make_figure(
                file_id=event.file_id,
                channel=event.channel,
                roi_id=event.roi_id,
            )
            self._plot.update()

    def _make_figure(self, file_id: str | None, channel: int | None, roi_id: str | None) -> dict:
        x_values = [0, 1, 2, 3, 4]
        base = 0 if channel is None else channel + 1
        y_values = [base, base + 1, base + 0.5, base + 1.5, base + 1]
        title = f'{self._title}: {file_id or "no file"}'
        if roi_id is not None:
            title += f' / {roi_id}'
        return {
            'data': [
                {
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'x': x_values,
                    'y': y_values,
                    'name': file_id or 'none',
                }
            ],
            'layout': {
                'title': {'text': title},
                'margin': {'l': 40, 'r': 20, 't': 40, 'b': 40},
            },
        }


@dataclass(slots=True)
class HomePage:
    """Compose the home page and its per-page objects."""

    controller: HomePageController
    event_bus: EventBus

    def build(self) -> None:
        """Build the page UI and load initial demo state."""
        file_list_panel = FileListPanel(self.event_bus)
        selection_toolbar = SelectionToolbar(self.event_bus)
        primary_image = PlotlyImagePanel(self.event_bus, title='Primary image')
        reference_image = PlotlyImagePanel(self.event_bus, title='Reference image')

        with ui.column().classes('w-full gap-4 p-4'):
            ui.label('CloudScope').classes('text-2xl font-bold')
            with ui.row().classes('w-full items-start gap-4'):
                file_list_panel.build()
                with ui.column().classes('flex-1 gap-4'):
                    selection_toolbar.build()
                    primary_image.build()
                    reference_image.build()

        self.controller.bind()
        self.controller.load_demo_files(['file-001', 'file-002', 'file-003'])


@ui.page('/')
def home_page() -> None:
    """Create all per-page objects for the CloudScope home page."""
    event_bus = EventBus()
    controller = HomePageController(event_bus=event_bus)
    page = HomePage(controller=controller, event_bus=event_bus)
    page.build()
