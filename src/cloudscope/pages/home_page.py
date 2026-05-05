"""NiceGUI home page for CloudScope."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nicegui import app, ui

from nicewidgets.gui_defaults import setUpGuiDefaults

from cloudscope.app_config import AppConfig
from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.controllers.load_save_controller import LoadSaveController
from cloudscope.event_bus import EventBus
from cloudscope.events import (
    ChannelSelectionChanged,
    FileSelectionChanged,
    LoadPathKind,
    LoadPathIntent,
    RoiSelectionChanged,
)
from cloudscope.views.app_config_view import AppConfigView
from cloudscope.views.file_list_view import AcqImageListTableView
from cloudscope.views.footer_view import FooterView
from cloudscope.views.header_view import build_main_header
from cloudscope.views.image_toolbar_view import ImageToolbarView
from cloudscope.views.left_toolbar_view import LeftToolbarView
from cloudscope.views.load_save_view import LoadSaveView
from cloudscope.views.metadata_widget.metadata_view import MetadataView
from cloudscope.views.primary_image_view import PrimaryImageView
from cloudscope.views.velocity_analysis_view import VelocityAnalysisView
from cloudscope.views.view_manager import ViewManager

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)

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
            ui.label(self._title)
            self._summary = ui.label("No selection")
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



def _infer_load_kind(path: str) -> LoadPathKind:
    """Infer load kind from path string."""
    if path.lower().endswith('.csv'):
        return LoadPathKind.CSV
    return LoadPathKind.FOLDER if Path(path).expanduser().is_dir() else LoadPathKind.FILE



@dataclass(slots=True)
class HomePage:
    """Compose the home page and its per-page objects.

    Args:
        controller: Home page controller.
        load_save_controller: Load/save controller.
        event_bus: Page-scoped event bus.
        app_config: Shared app configuration.
    """

    controller: HomePageController
    load_save_controller: LoadSaveController
    event_bus: EventBus
    app_config: AppConfig

    def build(self) -> None:
        """Build the page UI and load initial AcqStore state.

        Returns:
            None.
        """
        text_size = self.app_config.get_attribute("text_size")
        setUpGuiDefaults(text_size)

        self._install_shutdown_handlers()

        app.native.on('resized', self._native_resize)
        app.native.on('moved', self._native_moved)

        view_manager = ViewManager()
        app_state = self.controller.state

        file_list_panel = AcqImageListTableView(
            event_bus=self.event_bus,
            acq_image_list=None,
            app_config=self.app_config,
            app_state=app_state,
            initially_visible=True,
        )
        load_save_view = LoadSaveView(event_bus=self.event_bus, app_config=self.app_config)
        image_toolbar = ImageToolbarView(event_bus=self.event_bus)
        metadata_view = MetadataView(
            event_bus=self.event_bus,
            app_state=app_state,
            initially_visible=False,
        )
        velocity_analysis_view = VelocityAnalysisView(
            event_bus=self.event_bus,
            app_state=app_state,
            initially_visible=False,
        )
        app_config_view = AppConfigView(
            app_config=self.app_config,
            event_bus=self.event_bus,
            initially_visible=False,
        )
        primary_image = PrimaryImageView(self.event_bus, title='Primary image')
        reference_image = PlotlyImagePanel(self.event_bus, title="Reference image")
        footer = FooterView(
            event_bus=self.event_bus,
            app_state=app_state,
            initially_visible=True,
        )

        ui.page_title("CloudScope")
        build_main_header(title="CloudScope", app_config=self.app_config)
        footer.build()
        view_manager.register(footer)

        with ui.splitter(value=8).classes("w-full min-h-screen") as splitter:
            with splitter.before:
                with ui.row().classes("w-full h-full items-start gap-0"):
                    with ui.column().classes("h-full shrink-0") as toolbar_container:
                        pass
                    with ui.column().classes("h-full w-80 gap-3 p-3") as left_panel_root:
                        metadata_view.build()
                        velocity_analysis_view.build()
                        app_config_view.build()

                    view_manager.register(metadata_view)
                    view_manager.register(velocity_analysis_view)
                    view_manager.register(app_config_view)

                    left_toolbar = LeftToolbarView(
                        event_bus=self.event_bus,
                        view_manager=view_manager,
                        left_panel_root=left_panel_root,
                    )
                    left_toolbar.build(parent=toolbar_container)
                    view_manager.register(left_toolbar)

            with splitter.after:
                with ui.column().classes("w-full gap-4 p-4"):
                    load_save_view.build()

                    with ui.row().classes("w-full items-start gap-4"):
                        file_list_panel.build()
                    view_manager.register(file_list_panel)

                    with ui.row().classes("w-full items-start gap-4"):
                        image_toolbar.build()

                    primary_image.build()
                    reference_image.build()

        self.controller.bind()
        self.load_save_controller.bind()
        self.controller.load_demo_files([])

        last_path = self.app_config.get_last_path().strip()
        if last_path:
            kind = _infer_load_kind(last_path)
            self.event_bus.publish(LoadPathIntent(path=last_path, kind=kind))

    # abb 20260323 pywebview native save png (clipboard)
    def _native_resize(self, e):# we also can do this:
        """
        NativeEventArguments(type='resized', args={'width': 1221.0, 'height': 1538.0})
        """
        args = e.args
        
        # logger.info(f"  args is: {args}")

        # cfg = AppConfig.load()
        # logger.info(f"App config loaded from: {cfg.path}")

        x, y, w, h = self.app_config.get_window_rect()

        # logger.info(f"  old window size: w:{w}, h:{h}")
        w = args['width']
        h = args['height']  
        # logger.info(f"  new window size: w:{w}, h:{h}")

        self.app_config.set_window_rect(x, y, w, h)

    def _native_moved(self, e):
        """
        NativeEventArguments(type='moved', args={'x': 2365.0, 'y': 545.0})
        """
        args = e.args

        # logger.info(f"  args is: {args}")

        # cfg = AppConfig.load()
        # logger.info(f"App config loaded from: {cfg.path}")

        x, y, w, h = self.app_config.get_window_rect()

        # logger.info(f"  old window position: x:{x}, y:{y}")
        x = args['x']
        y = args['y']  
        # logger.info(f"  new window position: x:{x}, y:{y}")

        self.app_config.set_window_rect(x, y, w, h)

    def _install_shutdown_handlers(self) -> None:
        """Register app shutdown handlers for GUI v2.
        
        Only installs handlers when running in native mode (native=True).
        In browser mode, configs are saved via other mechanisms.
        """
        native = getattr(app, "native", None)
        if native is None:
            logger.debug("skipping (not native mode)")
            return
        
        # logger.info("installing (native mode detected)")

        async def _persist_on_shutdown() -> None:
            """Persist user and app config on shutdown without touching native window APIs."""
            self.app_config.save()

        app.on_shutdown(_persist_on_shutdown)


@ui.page("/")
def home_page() -> None:
    """Create all per-page objects for the CloudScope home page.

    Returns:
        None.
    """
    event_bus = EventBus()
    app_config = AppConfig.load(create_if_missing=False)
    controller = HomePageController(event_bus=event_bus)
    load_save_controller = LoadSaveController(
        event_bus=event_bus,
        home_controller=controller,
        app_config=app_config,
    )
    page = HomePage(
        controller=controller,
        load_save_controller=load_save_controller,
        event_bus=event_bus,
        app_config=app_config,
    )
    page.build()

