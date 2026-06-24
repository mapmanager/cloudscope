"""NiceGUI home page for CloudScope."""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import app, ui

from nicewidgets.gui_defaults import setUpGuiDefaults
from nicewidgets.smart_expansion_widget.smart_expansion import SmartExpansion

from cloudscope.app_config import AppConfig
from cloudscope.controllers.analysis_controller import AnalysisController
from cloudscope.controllers.contrast_controller import ContrastController
from cloudscope.controllers.event_analysis_controller import EventAnalysisController
from cloudscope.controllers.home_page_controller import HomePageController
from cloudscope.controllers.load_save_controller import LoadSaveController
from cloudscope.controllers.roi_controller import RoiController
from cloudscope.controllers.velocity_pool_controller import VelocityPoolController
from cloudscope.controllers.x_range_controller import XRangeController
from cloudscope.event_bus import EventBus
from cloudscope.runtime import get_current_runtime
from cloudscope.task_runner import TaskRunner
from cloudscope.user_context import UserContext
from cloudscope.events.layout import ResetHomeLayoutIntent
from cloudscope.views.file_list_tree_view import AcqImageListTreeView
from cloudscope.views.footer_view import FooterView
from cloudscope.views.header_view import build_main_header
from cloudscope.views.image_toolbar_view import ImageToolbarView
from cloudscope.views.acq_analysis_plot_view import AcqAnalysisPlotView
from cloudscope.views.left_toolbar_view import LeftToolbarView
from cloudscope.views.load_save_view import LoadSaveView
from cloudscope.views.primary_image_view import PrimaryImageView
from cloudscope.views.reference_image_view import ReferenceImageView
from cloudscope.views.task_progress_dialog_view import TaskProgressDialogView
from cloudscope.views.velocity_pool_view import VelocityPoolView
from cloudscope.views.view_manager import ViewManager
from cloudscope.views.splitter_handle import add_splitter_handle
from cloudscope.views.splitter_manager import HOME_SPLITTER_PRESETS, SplitterId, SplitterManager

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)

SHOW_EMBEDDED_VELOCITY_POOL = False


@dataclass(slots=True)
class HomePage:
    """Compose the home page and its per-page objects.

    Args:
        controller: Home page controller.
        load_save_controller: Load/save controller.
        event_bus: Shared runtime event bus.
        app_config: Shared app configuration.
        user_context: User/workspace context for config and storage paths.
        analysis_controller: Shared analysis controller.
        roi_controller: Shared ROI controller.
        event_analysis_controller: Shared event-analysis controller.
        velocity_pool_controller: Shared velocity-pool controller.
        task_runner: Shared background task runner.
    """

    controller: HomePageController
    load_save_controller: LoadSaveController
    event_bus: EventBus
    app_config: AppConfig
    user_context: UserContext
    analysis_controller: AnalysisController
    roi_controller: RoiController
    event_analysis_controller: EventAnalysisController
    velocity_pool_controller: VelocityPoolController
    task_runner: TaskRunner

    def build(self) -> None:
        """Build the page UI and load initial AcqStore state.

        Returns:
            None.
        """
        logger.info('!!! BUILDING HOME PAGE !!!')

        text_size = self.app_config.get_attribute('text_size')
        setUpGuiDefaults(text_size)

        self._install_shutdown_handlers()

        native = getattr(app, 'native', None)
        if native is not None and getattr(native, 'main_window', None) is not None:
            app.native.on('resized', self._native_resize)
            app.native.on('moved', self._native_moved)

        view_manager = ViewManager()
        splitter_manager = SplitterManager(self.app_config)
        contrast_controller = ContrastController(
            event_bus=self.event_bus,
            home_controller=self.controller,
        )
        x_range_controller = XRangeController(
            event_bus=self.event_bus,
            home_controller=self.controller,
        )
        app_state = self.controller.state
        dark_mode = bool(self.app_config.data.dark_mode)

        def _dark_mode() -> bool:
            """Return the current persisted application dark-mode state.

            Returns:
                True when dark mode is enabled.
            """
            return bool(self.app_config.data.dark_mode)

        file_list_panel = AcqImageListTreeView(
            event_bus=self.event_bus,
            app_state=app_state,
            table_font_size_px=int(self.app_config.data.table_font_size_px),
            initially_visible=False,
        )
        app_state.visible_file_ids_provider = file_list_panel.get_displayed_file_ids
        load_save_view = LoadSaveView(
            event_bus=self.event_bus,
            app_config=self.app_config,
            user_context=self.user_context,
            initially_visible=True,
        )
        image_toolbar = ImageToolbarView(
            event_bus=self.event_bus,
            initially_visible=True,
            app_config=self.app_config,
        )
        primary_image = PrimaryImageView(
            self.event_bus,
            title='Primary image',
            initially_visible=True,
            dark_mode=dark_mode,
            dark_mode_provider=_dark_mode,
            raster_display_cache=get_current_runtime().raster_display_cache,
        )
        acq_analysis_plot = AcqAnalysisPlotView(
            self.event_bus,
            app_state=app_state,
            title='Analysis plot',
            initially_visible=False,
        )
        reference_image = ReferenceImageView(
            self.event_bus,
            app_state=app_state,
            title='Reference image',
            initially_visible=False,
            dark_mode=dark_mode,
            dark_mode_provider=_dark_mode,
            raster_display_cache=get_current_runtime().raster_display_cache,
        )
        velocity_pool_view: VelocityPoolView | None = None
        if SHOW_EMBEDDED_VELOCITY_POOL:
            velocity_pool_view = VelocityPoolView(
                event_bus=self.event_bus,
                app_state=app_state,
                table_font_size_px=int(self.app_config.data.table_font_size_px),
                initially_visible=False,
                dark_mode=dark_mode,
                dark_mode_provider=_dark_mode,
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
        home_expansion_refs: dict[str, SmartExpansion | None] = {
            'file_list': None,
            'analysis_plot': None,
            'reference_image': None,
            'velocity_pool': None,
        }
        panel_open_state = {
            'file_list': True,
            'analysis_plot': True,
            'reference_image': False,
            'velocity_pool': True,
        }

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

        def _scrollable_fill_column_classes(extra: str = '') -> str:
            """Return classes for fill-layout panes with internal scrolling.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for scrollable fill-layout columns.
            """
            base = 'w-full h-full min-h-0 gap-3 p-3 overflow-auto flex flex-col flex-nowrap'
            return f'{base} {extra}'.strip()

        def _main_scroll_shell_classes(extra: str = '') -> str:
            """Return classes for the right-side page scroll owner.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for the single vertical scroll container on Home.
            """
            base = 'w-full h-full min-h-0 overflow-y-auto overflow-x-hidden'
            return f'{base} {extra}'.strip()

        def _main_scroll_content_classes(extra: str = '') -> str:
            """Return classes for natural-height Home page content.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for the vertical content column inside the scroll shell.
            """
            base = 'w-full min-h-full gap-3 p-3 flex flex-col flex-nowrap'
            return f'{base} {extra}'.strip()

        def _file_list_section_classes(extra: str = '') -> str:
            """Return classes for the file-list section in the scroll stack.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for the file-list section.
            """
            base = 'w-full h-[32vh] min-h-[300px] shrink-0 gap-3 overflow-hidden flex flex-col'
            return f'{base} {extra}'.strip()

        def _primary_image_section_classes(extra: str = '') -> str:
            """Return classes for the primary-image section in the scroll stack.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for the primary-image section.
            """
            base = 'w-full h-[58vh] min-h-[500px] shrink-0 gap-3 overflow-hidden flex flex-col'
            return f'{base} {extra}'.strip()

        def _analysis_plot_section_classes(extra: str = '') -> str:
            """Return classes for the analysis-plot section in the scroll stack.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for the analysis-plot section.
            """
            base = 'w-full h-[42vh] min-h-[360px] shrink-0 gap-3 overflow-hidden flex flex-col'
            return f'{base} {extra}'.strip()

        def _reference_section_classes(extra: str = '') -> str:
            """Return classes for natural-height expandable sections.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for SmartExpansion sections that must not create
                their own vertical scrollbar.
            """
            base = 'w-full shrink-0 overflow-visible'
            return f'{base} {extra}'.strip()

        def _capture(splitter_id: SplitterId) -> None:
            """Capture a user-adjusted splitter value in AppConfig memory.

            Args:
                splitter_id: Splitter that changed.

            Returns:
                None.
            """
            splitter_manager.capture_current_value(splitter_id)

        def _sync_analysis_reference_layout() -> None:
            """No-op placeholder for legacy analysis/reference splitter syncing.

            The Home page now uses a natural-height right-side scroll column.
            Analysis and reference sections no longer resize each other through
            nested vertical splitters.

            Returns:
                None.
            """
            return

        def _open_file_list_panel() -> None:
            """Show the file list view.

            Returns:
                None.
            """
            panel_open_state['file_list'] = True
            file_list_panel.show()

        def _close_file_list_panel() -> None:
            """Hide the file list view.

            Returns:
                None.
            """
            panel_open_state['file_list'] = False
            file_list_panel.hide()

        def _open_analysis_plot_panel() -> None:
            """Show the analysis plot view.

            Returns:
                None.
            """
            panel_open_state['analysis_plot'] = True
            acq_analysis_plot.show()

        def _close_analysis_plot_panel() -> None:
            """Hide the analysis plot view.

            Returns:
                None.
            """
            panel_open_state['analysis_plot'] = False
            acq_analysis_plot.hide()

        def _open_reference_image_panel() -> None:
            """Show the reference image view when its expansion opens.

            Returns:
                None.
            """
            panel_open_state['reference_image'] = True
            reference_image.show()

        def _close_reference_image_panel() -> None:
            """Hide the reference image view when its expansion closes.

            Returns:
                None.
            """
            panel_open_state['reference_image'] = False
            reference_image.hide()

        def _open_velocity_pool_panel() -> None:
            """Show velocity pool view.

            Returns:
                None.
            """
            if velocity_pool_view is None:
                return
            panel_open_state['velocity_pool'] = True
            velocity_pool_view.show()

        def _close_velocity_pool_panel() -> None:
            """Hide velocity pool view.

            Returns:
                None.
            """
            if velocity_pool_view is None:
                return
            panel_open_state['velocity_pool'] = False
            velocity_pool_view.hide()

        def _reset_home_expansions() -> None:
            """Restore Home page SmartExpansion panels to their default open state.

            Reference image stays collapsed; other panels are opened.

            Returns:
                None.
            """
            for key, expansion in home_expansion_refs.items():
                if expansion is None:
                    continue
                if key == 'reference_image':
                    expansion.close()
                else:
                    expansion.open()
            panel_open_state['file_list'] = True
            panel_open_state['analysis_plot'] = True
            panel_open_state['reference_image'] = False
            panel_open_state['velocity_pool'] = True

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
            _reset_home_expansions()
            ui.notify('View layout reset', type='positive')

        self.event_bus.subscribe(ResetHomeLayoutIntent, _reset_home_layout)

        ui.page_title('CloudScope')
        build_main_header(
            title='CloudScope',
            app_config=self.app_config,
            event_bus=self.event_bus,
            show_open_pool=True,
        )
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
                with ui.element('div').classes(_main_scroll_shell_classes()):
                    with ui.column().classes(_main_scroll_content_classes()):
                        with ui.column().classes(_file_list_section_classes()):
                            load_save_view.build()
                            view_manager.register(load_save_view)

                            file_list_panel.show()
                            file_list_panel.build()
                            view_manager.register(file_list_panel)

                        with ui.column().classes(_primary_image_section_classes()):
                            image_toolbar.build()
                            view_manager.register(image_toolbar)
                            primary_image.build()
                            view_manager.register(primary_image)

                        with ui.column().classes(_analysis_plot_section_classes()):
                            acq_analysis_plot.show()
                            acq_analysis_plot.build()
                            view_manager.register(acq_analysis_plot)

                        with ui.element('div').classes(_reference_section_classes()):
                            reference_image_expansion = SmartExpansion(
                                'Reference image',
                                icon='image',
                                initially_open=False,
                                on_open=_open_reference_image_panel,
                                on_close=_close_reference_image_panel,
                            )
                            home_expansion_refs['reference_image'] = reference_image_expansion
                            with reference_image_expansion:
                                reference_image.build()
                            reference_image_expansion.apply_initial_state()
                            view_manager.register(reference_image)

                        if SHOW_EMBEDDED_VELOCITY_POOL and velocity_pool_view is not None:
                            with ui.element('div').classes(_reference_section_classes()):
                                velocity_pool_expansion = SmartExpansion(
                                    'Velocity pool',
                                    icon='table_chart',
                                    initially_open=False,
                                    on_open=_open_velocity_pool_panel,
                                    on_close=_close_velocity_pool_panel,
                                )
                                home_expansion_refs['velocity_pool'] = velocity_pool_expansion
                                with velocity_pool_expansion:
                                    velocity_pool_view.build()
                                velocity_pool_expansion.apply_initial_state()
                                view_manager.register(velocity_pool_view)

            add_splitter_handle(left_splitter, orientation='vertical', offset='after')
            left_splitter.on(
                'update:model-value',
                lambda _event=None: _capture(SplitterId.LEFT_TOOLBAR),
                throttle=0.2,
            )

        contrast_controller.bind()
        x_range_controller.bind()

        def _on_client_disconnect() -> None:
            for view_id in view_manager.view_ids():
                view_manager.get(view_id).on_hide()

        ui.context.client.on_disconnect(_on_client_disconnect)

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
    runtime = get_current_runtime()
    runtime.initialize_once()
    page = HomePage(
        controller=runtime.home_page_controller,
        load_save_controller=runtime.load_save_controller,
        event_bus=runtime.event_bus,
        app_config=runtime.app_config,
        user_context=runtime.user_context,
        analysis_controller=runtime.analysis_controller,
        roi_controller=runtime.roi_controller,
        event_analysis_controller=runtime.event_analysis_controller,
        velocity_pool_controller=runtime.velocity_pool_controller,
        task_runner=runtime.task_runner,
    )
    page.build()

