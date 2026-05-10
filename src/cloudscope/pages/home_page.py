"""NiceGUI home page for CloudScope."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nicegui import app, ui

from nicewidgets.gui_defaults import setUpGuiDefaults

from cloudscope.app_config import AppConfig
from cloudscope.controllers.analysis_controller import AnalysisController
from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.controllers.load_save_controller import LoadSaveController
from cloudscope.controllers.roi_controller import RoiController
from cloudscope.event_bus import EventBus
from cloudscope.task_runner import TaskRunner
from cloudscope.events import (
    LoadPathKind,
    LoadPathIntent,
)
from cloudscope.views.file_list_view import AcqImageListTableView
from cloudscope.views.footer_view import FooterView
from cloudscope.views.header_view import build_main_header
from cloudscope.views.image_toolbar_view import ImageToolbarView
from cloudscope.views.acq_analysis_plot_view import AcqAnalysisPlotView
from cloudscope.views.left_toolbar_view import LeftToolbarView
from cloudscope.views.load_save_view import LoadSaveView
from cloudscope.views.primary_image_view import PrimaryImageView
from cloudscope.views.reference_image_view import ReferenceImageView
from cloudscope.views.task_progress_dialog_view import TaskProgressDialogView
from cloudscope.views.view_manager import ViewManager

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)


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
        task_runner = TaskRunner(self.event_bus)
        self.load_save_controller.task_runner = task_runner
        analysis_controller = AnalysisController(
            event_bus=self.event_bus,
            home_controller=self.controller,
            task_runner=task_runner,
        )
        roi_controller = RoiController(
            event_bus=self.event_bus,
            home_page_controller=self.controller,
        )
        app_state = self.controller.state

        file_list_panel = AcqImageListTableView(
            event_bus=self.event_bus,
            app_state=app_state,
            table_font_size_px=int(self.app_config.data.table_font_size_px),
            initially_visible=True,
        )
        load_save_view = LoadSaveView(
            event_bus=self.event_bus,
            app_config=self.app_config,
            initially_visible=True,
        )
        image_toolbar = ImageToolbarView(
            event_bus=self.event_bus,
            initially_visible=True,
        )
        primary_image = PrimaryImageView(
            self.event_bus,
            title='Primary image',
            initially_visible=True,
        )
        acq_analysis_plot = AcqAnalysisPlotView(
            self.event_bus,
            app_state=app_state,
            title='Velocity analysis plot',
            initially_visible=True,
        )
        reference_image = ReferenceImageView(
            self.event_bus,
            title='Reference image',
            initially_visible=True,
        )
        footer = FooterView(
            event_bus=self.event_bus,
            app_state=app_state,
            initially_visible=True,
        )
        task_progress_dialog = TaskProgressDialogView(
            event_bus=self.event_bus,
            initially_visible=True,
        )

        ui.page_title("CloudScope")
        build_main_header(title="CloudScope", app_config=self.app_config)
        footer.build()
        view_manager.register(footer)
        task_progress_dialog.build()
        view_manager.register(task_progress_dialog)

        with ui.splitter(value=8).classes("w-full min-h-screen") as splitter:
            with splitter.before:
                left_toolbar = LeftToolbarView(
                    event_bus=self.event_bus,
                    app_state=app_state,
                    app_config=self.app_config,
                    view_manager=view_manager,
                    initially_visible=True,
                )
                left_toolbar.build()
                view_manager.register(left_toolbar)

            with splitter.after:
                with ui.column().classes("w-full gap-4 p-4"):
                    load_save_view.build()
                    view_manager.register(load_save_view)

                    with ui.row().classes("w-full items-start gap-4"):
                        file_list_panel.build()
                    view_manager.register(file_list_panel)

                    with ui.row().classes("w-full items-start gap-4"):
                        image_toolbar.build()
                    view_manager.register(image_toolbar)

                    primary_image.build()
                    view_manager.register(primary_image)

                    acq_analysis_plot.build()
                    view_manager.register(acq_analysis_plot)

                    reference_image.build()
                    view_manager.register(reference_image)

        self.controller.bind()
        self.load_save_controller.bind()
        analysis_controller.bind()
        roi_controller.bind()
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

