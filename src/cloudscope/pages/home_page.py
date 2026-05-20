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
    ResetHomeLayoutIntent,
    SetHomeViewVisibleIntent,
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
from cloudscope.views.view_ids import CONFIGURABLE_HOME_VIEW_IDS, ViewId
from cloudscope.views.splitter_handle import add_splitter_handle
from cloudscope.views.splitter_manager import HOME_SPLITTER_PRESETS, SplitterId, SplitterManager

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
        text_size = self.app_config.get_attribute('text_size')
        setUpGuiDefaults(text_size)

        self._install_shutdown_handlers()

        app.native.on('resized', self._native_resize)
        app.native.on('moved', self._native_moved)

        view_manager = ViewManager()
        splitter_manager = SplitterManager(self.app_config)
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

        def _home_view_visible(view_id: ViewId) -> bool:
            """Return startup visibility for one Home page view.

            Args:
                view_id: Home page view id.

            Returns:
                Configured visibility for configurable views; True for all
                non-configurable views.
            """
            return self.app_config.is_home_view_visible(view_id.value)

        file_list_panel = AcqImageListTableView(
            event_bus=self.event_bus,
            app_state=app_state,
            table_font_size_px=int(self.app_config.data.table_font_size_px),
            initially_visible=_home_view_visible(ViewId.FILE_LIST),
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
            initially_visible=_home_view_visible(ViewId.ACQ_ANALYSIS_PLOT),
        )
        reference_image = ReferenceImageView(
            self.event_bus,
            title='Reference image',
            initially_visible=_home_view_visible(ViewId.REFERENCE_IMAGE),
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
        left_toolbar_ref: dict[str, LeftToolbarView | None] = {'value': None}

        def _pane_classes(extra: str = '') -> str:
            """Return common splitter pane classes.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for splitter pane containers.
            """
            base = 'w-full h-full min-w-8 min-h-8 overflow-hidden'
            return f'{base} {extra}'.strip()

        def _content_column_classes(extra: str = '') -> str:
            """Return common content column classes.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for content columns.
            """
            base = 'w-full h-full min-h-0 gap-3 p-3 overflow-auto'
            return f'{base} {extra}'.strip()

        def _fill_column_classes(extra: str = '') -> str:
            """Return classes for splitter panes that should fill without page scroll.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for fill-layout columns.
            """
            base = 'w-full h-full min-h-0 gap-3 p-3 overflow-hidden flex flex-col'
            return f'{base} {extra}'.strip()

        def _capture(splitter_id: SplitterId) -> None:
            """Capture a user-adjusted splitter value in AppConfig memory.

            Args:
                splitter_id: Splitter that changed.

            Returns:
                None.
            """
            splitter_manager.capture_current_value(splitter_id)

        def _reset_home_layout(_event: ResetHomeLayoutIntent | None = None) -> None:
            """Reset Home page splitters and close the left toolbar panel.

            Args:
                _event: Reset intent, ignored.

            Returns:
                None.
            """
            left_toolbar = left_toolbar_ref['value']
            if left_toolbar is not None:
                left_toolbar.close_panel()
            splitter_manager.reset_all()
            ui.notify('View layout reset', type='positive')

        def _set_home_view_visible(event: SetHomeViewVisibleIntent) -> None:
            """Apply a Home page view visibility request.

            Args:
                event: Visibility-change request from AppConfigView.

            Returns:
                None.
            """
            if event.view_id not in CONFIGURABLE_HOME_VIEW_IDS:
                logger.warning('Ignoring visibility request for non-configurable view: %s', event.view_id)
                return
            view_id = ViewId(event.view_id)
            self.app_config.set_home_view_visible(event.view_id, event.visible)
            view_manager.set_visible(view_id, event.visible)

        self.event_bus.subscribe(ResetHomeLayoutIntent, _reset_home_layout)
        self.event_bus.subscribe(SetHomeViewVisibleIntent, _set_home_view_visible)

        ui.page_title('CloudScope')
        build_main_header(title='CloudScope', app_config=self.app_config)
        footer.build()
        view_manager.register(footer)
        task_progress_dialog.build()
        view_manager.register(task_progress_dialog)

        left_preset = HOME_SPLITTER_PRESETS[SplitterId.LEFT_TOOLBAR]
        with ui.splitter(
            value=splitter_manager.value_for(SplitterId.LEFT_TOOLBAR),
            limits=left_preset.limits,
        ).classes('w-full h-[calc(100vh-4rem)] min-h-0 overflow-hidden') as left_splitter:
            splitter_manager.register(SplitterId.LEFT_TOOLBAR, left_splitter)

            with left_splitter.before:
                left_toolbar = LeftToolbarView(
                    event_bus=self.event_bus,
                    app_state=app_state,
                    app_config=self.app_config,
                    view_manager=view_manager,
                    initially_visible=True,
                    on_panel_open_changed=splitter_manager.set_left_toolbar_open,
                )
                left_toolbar.build()
                left_toolbar_ref['value'] = left_toolbar
                view_manager.register(left_toolbar)

            with left_splitter.after:
                file_preset = HOME_SPLITTER_PRESETS[SplitterId.FILE_LIST]
                with ui.splitter(
                    value=splitter_manager.value_for(SplitterId.FILE_LIST),
                    limits=file_preset.limits,
                    horizontal=True,
                ).classes('w-full h-full min-h-0 overflow-hidden') as file_list_splitter:
                    splitter_manager.register(SplitterId.FILE_LIST, file_list_splitter)

                    with file_list_splitter.before:
                        with ui.column().classes(_content_column_classes()):
                            load_save_view.build()
                            view_manager.register(load_save_view)
                            file_list_panel.build()
                            view_manager.register(file_list_panel)

                    with file_list_splitter.after:
                        primary_preset = HOME_SPLITTER_PRESETS[SplitterId.PRIMARY_IMAGE]
                        with ui.splitter(
                            value=splitter_manager.value_for(SplitterId.PRIMARY_IMAGE),
                            limits=primary_preset.limits,
                            horizontal=True,
                        ).classes('w-full h-full min-h-0 mt-[6px]') as primary_splitter:
                            splitter_manager.register(SplitterId.PRIMARY_IMAGE, primary_splitter)

                            with primary_splitter.before:
                                with ui.column().classes(_fill_column_classes()):
                                    image_toolbar.build()
                                    view_manager.register(image_toolbar)
                                    primary_image.build()
                                    view_manager.register(primary_image)

                            with primary_splitter.after:
                                analysis_preset = HOME_SPLITTER_PRESETS[SplitterId.ANALYSIS_REFERENCE]
                                with ui.splitter(
                                    value=splitter_manager.value_for(SplitterId.ANALYSIS_REFERENCE),
                                    limits=analysis_preset.limits,
                                    horizontal=True,
                                ).classes('w-full h-full min-h-0 mt-[6px]') as analysis_reference_splitter:
                                    splitter_manager.register(SplitterId.ANALYSIS_REFERENCE, analysis_reference_splitter)

                                    with analysis_reference_splitter.before:
                                        with ui.column().classes(_fill_column_classes()):
                                            acq_analysis_plot.build()
                                            view_manager.register(acq_analysis_plot)

                                    with analysis_reference_splitter.after:
                                        with ui.column().classes(_fill_column_classes()):
                                            reference_image.build()
                                            view_manager.register(reference_image)

                                    add_splitter_handle(analysis_reference_splitter, orientation='horizontal')
                                    analysis_reference_splitter.on(
                                        'update:model-value',
                                        lambda _event=None: _capture(SplitterId.ANALYSIS_REFERENCE),
                                        throttle=0.2,
                                    )

                            add_splitter_handle(primary_splitter, orientation='horizontal')
                            primary_splitter.on(
                                'update:model-value',
                                lambda _event=None: _capture(SplitterId.PRIMARY_IMAGE),
                                throttle=0.2,
                            )

                    add_splitter_handle(file_list_splitter, orientation='horizontal')
                    file_list_splitter.on(
                        'update:model-value',
                        lambda _event=None: _capture(SplitterId.FILE_LIST),
                        throttle=0.2,
                    )

            add_splitter_handle(left_splitter, orientation='vertical', offset='after')
            left_splitter.on(
                'update:model-value',
                lambda _event=None: _capture(SplitterId.LEFT_TOOLBAR),
                throttle=0.2,
            )

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

