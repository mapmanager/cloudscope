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
from cloudscope.events.layout import ResetHomeLayoutIntent
from cloudscope.runtime import get_current_runtime
from cloudscope.task_runner import TaskRunner
from cloudscope.user_context import UserContext
from cloudscope.views.acq_analysis_plot_view import AcqAnalysisPlotView
from cloudscope.views.file_list_tree_view import AcqImageListTreeView
from cloudscope.views.footer_view import FooterView
from cloudscope.views.header_view import build_main_header
from cloudscope.views.image_toolbar_view import ImageToolbarView
from cloudscope.views.left_toolbar_view import LeftToolbarView
from cloudscope.views.load_save_view import LoadSaveView
from cloudscope.views.primary_image_view import PrimaryImageView
from cloudscope.views.reference_image_view import ReferenceImageView
from cloudscope.views.splitter_handle import add_splitter_handle
from cloudscope.views.splitter_manager import HOME_SPLITTER_PRESETS, SplitterId, SplitterManager
from cloudscope.views.task_progress_dialog_view import TaskProgressDialogView
from cloudscope.views.velocity_pool_view import VelocityPoolView
from cloudscope.views.view_manager import ViewManager

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)

SHOW_EMBEDDED_VELOCITY_POOL = False


@dataclass(slots=True)
class HomePageViews:
    """Container for Home page view instances.

    Args:
        file_list_panel: File list tree view.
        load_save_view: Load/save toolbar view.
        image_toolbar: Primary-image toolbar view.
        primary_image: Primary image raster view.
        acq_analysis_plot: Analysis plot view.
        reference_image: Reference image raster view.
        velocity_pool_view: Optional embedded velocity-pool view.
        footer: Footer view.
        task_progress_dialog: Background task progress dialog.
    """

    file_list_panel: AcqImageListTreeView
    load_save_view: LoadSaveView
    image_toolbar: ImageToolbarView
    primary_image: PrimaryImageView
    acq_analysis_plot: AcqAnalysisPlotView
    reference_image: ReferenceImageView
    velocity_pool_view: VelocityPoolView | None
    footer: FooterView
    task_progress_dialog: TaskProgressDialogView


@dataclass(slots=True)
class HomePageLayoutState:
    """Mutable UI references used by Home page layout callbacks.

    Args:
        left_toolbar: Left-toolbar view after it is built.
        expansions: SmartExpansion instances keyed by logical panel name.
        panel_open: Current open state for managed Home panels.
    """

    left_toolbar: LeftToolbarView | None
    expansions: dict[str, SmartExpansion | None]
    panel_open: dict[str, bool]

    @classmethod
    def create(cls) -> HomePageLayoutState:
        """Create the default Home page layout state.

        Returns:
            New mutable layout state.
        """
        return cls(
            left_toolbar=None,
            expansions={
                'reference_image': None,
                'velocity_pool': None,
            },
            panel_open={
                'file_list': True,
                'analysis_plot': True,
                'reference_image': False,
                'velocity_pool': True,
            },
        )


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

        setUpGuiDefaults(self.app_config.get_attribute('text_size'))
        self._install_shutdown_handlers()
        self._install_native_window_handlers()

        view_manager = ViewManager()
        splitter_manager = SplitterManager(self.app_config)
        layout_state = HomePageLayoutState.create()
        app_state = self.controller.state
        views = self._create_views()
        app_state.visible_file_ids_provider = views.file_list_panel.get_displayed_file_ids

        self._subscribe_layout_reset(splitter_manager, layout_state)
        self._build_page_chrome(views, view_manager)
        self._build_workspace(views, view_manager, splitter_manager, layout_state)
        self._bind_controllers()
        self._install_disconnect_handler(view_manager)

    def _create_views(self) -> HomePageViews:
        """Create all Home page views.

        Returns:
            Home page view container.
        """
        app_state = self.controller.state
        dark_mode = bool(self.app_config.data.dark_mode)
        raster_display_cache = get_current_runtime().raster_display_cache

        velocity_pool_view: VelocityPoolView | None = None
        if SHOW_EMBEDDED_VELOCITY_POOL:
            velocity_pool_view = VelocityPoolView(
                event_bus=self.event_bus,
                app_state=app_state,
                table_font_size_px=int(self.app_config.data.table_font_size_px),
                initially_visible=False,
                dark_mode=dark_mode,
                dark_mode_provider=self._dark_mode,
            )

        return HomePageViews(
            file_list_panel=AcqImageListTreeView(
                event_bus=self.event_bus,
                app_state=app_state,
                table_font_size_px=int(self.app_config.data.table_font_size_px),
                initially_visible=False,
            ),
            load_save_view=LoadSaveView(
                event_bus=self.event_bus,
                app_config=self.app_config,
                user_context=self.user_context,
                initially_visible=True,
            ),
            image_toolbar=ImageToolbarView(
                event_bus=self.event_bus,
                initially_visible=True,
                app_config=self.app_config,
            ),
            primary_image=PrimaryImageView(
                self.event_bus,
                title='Primary image',
                initially_visible=True,
                dark_mode=dark_mode,
                dark_mode_provider=self._dark_mode,
                raster_display_cache=raster_display_cache,
            ),
            acq_analysis_plot=AcqAnalysisPlotView(
                self.event_bus,
                app_state=app_state,
                title='Analysis plot',
                initially_visible=False,
            ),
            reference_image=ReferenceImageView(
                self.event_bus,
                app_state=app_state,
                title='Reference image',
                initially_visible=False,
                dark_mode=dark_mode,
                dark_mode_provider=self._dark_mode,
                raster_display_cache=raster_display_cache,
            ),
            velocity_pool_view=velocity_pool_view,
            footer=FooterView(
                event_bus=self.event_bus,
                app_state=app_state,
                initially_visible=True,
            ),
            task_progress_dialog=TaskProgressDialogView(
                event_bus=self.event_bus,
                initially_visible=True,
            ),
        )

    def _dark_mode(self) -> bool:
        """Return the current persisted application dark-mode state.

        Returns:
            True when dark mode is enabled.
        """
        return bool(self.app_config.data.dark_mode)

    def _build_page_chrome(self, views: HomePageViews, view_manager: ViewManager) -> None:
        """Build page title, header, footer, and global dialog.

        Args:
            views: Home page view instances.
            view_manager: View lifecycle registry.

        Returns:
            None.
        """
        ui.page_title('CloudScope')
        build_main_header(
            title='CloudScope',
            app_config=self.app_config,
            event_bus=self.event_bus,
            show_open_pool=True,
        )
        views.footer.build()
        view_manager.register(views.footer)
        views.task_progress_dialog.build()
        view_manager.register(views.task_progress_dialog)

    def _build_workspace(
        self,
        views: HomePageViews,
        view_manager: ViewManager,
        splitter_manager: SplitterManager,
        layout_state: HomePageLayoutState,
    ) -> None:
        """Build the main Home page workspace.

        The left toolbar remains pinned in the splitter ``before`` pane. The
        splitter tree in the ``after`` pane is wrapped in a vertical scroll shell
        so short desktop windows can reach the Reference Image SmartExpansion.

        Args:
            views: Home page view instances.
            view_manager: View lifecycle registry.
            splitter_manager: Splitter state manager.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        left_preset = HOME_SPLITTER_PRESETS[SplitterId.LEFT_TOOLBAR]
        with ui.splitter(
            value=splitter_manager.value_for(SplitterId.LEFT_TOOLBAR),
            limits=left_preset.limits,
        ).classes('w-full h-[calc(100vh-4rem)] min-h-0 overflow-hidden') as left_splitter:
            splitter_manager.register(SplitterId.LEFT_TOOLBAR, left_splitter)

            with left_splitter.before:
                layout_state.left_toolbar = self._build_left_toolbar(view_manager, splitter_manager)

            with left_splitter.after:
                with ui.element('div').classes(self._main_scroll_shell_classes()):
                    with ui.element('div').classes(self._main_scroll_content_classes()):
                        self._build_content_splitters(views, view_manager, splitter_manager, layout_state)

            add_splitter_handle(left_splitter, orientation='vertical', offset='after')
            left_splitter.on(
                'update:model-value',
                lambda _event=None: self._capture_splitter(splitter_manager, SplitterId.LEFT_TOOLBAR),
                throttle=0.2,
            )

    def _build_left_toolbar(
        self,
        view_manager: ViewManager,
        splitter_manager: SplitterManager,
    ) -> LeftToolbarView:
        """Build and register the pinned left toolbar.

        Args:
            view_manager: View lifecycle registry.
            splitter_manager: Splitter state manager.

        Returns:
            Built left toolbar view.
        """
        left_toolbar = LeftToolbarView(
            event_bus=self.event_bus,
            app_state=self.controller.state,
            app_config=self.app_config,
            view_manager=view_manager,
            initially_visible=True,
            on_panel_open_changed=splitter_manager.set_left_toolbar_open,
        )
        left_toolbar.build()
        view_manager.register(left_toolbar)
        return left_toolbar

    def _build_content_splitters(
        self,
        views: HomePageViews,
        view_manager: ViewManager,
        splitter_manager: SplitterManager,
        layout_state: HomePageLayoutState,
    ) -> None:
        """Build the nested Home content splitters.

        Args:
            views: Home page view instances.
            view_manager: View lifecycle registry.
            splitter_manager: Splitter state manager.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        file_preset = HOME_SPLITTER_PRESETS[SplitterId.FILE_LIST]
        with ui.splitter(
            value=splitter_manager.value_for(SplitterId.FILE_LIST),
            limits=file_preset.limits,
            horizontal=True,
        ).classes('w-full h-full min-h-0 overflow-hidden') as file_list_splitter:
            splitter_manager.register(SplitterId.FILE_LIST, file_list_splitter)

            with file_list_splitter.before:
                self._build_file_list_pane(views, view_manager)

            with file_list_splitter.after:
                self._build_primary_and_analysis_splitters(views, view_manager, splitter_manager, layout_state)

            add_splitter_handle(file_list_splitter, orientation='horizontal')
            file_list_splitter.on(
                'update:model-value',
                lambda _event=None: self._capture_splitter(splitter_manager, SplitterId.FILE_LIST),
                throttle=0.2,
            )

    def _build_file_list_pane(self, views: HomePageViews, view_manager: ViewManager) -> None:
        """Build the file-list pane without SmartExpansion.

        Args:
            views: Home page view instances.
            view_manager: View lifecycle registry.

        Returns:
            None.
        """
        with ui.column().classes(self._content_column_classes()):
            views.load_save_view.build()
            view_manager.register(views.load_save_view)
            views.file_list_panel.show()
            views.file_list_panel.build()
            view_manager.register(views.file_list_panel)

    def _build_primary_and_analysis_splitters(
        self,
        views: HomePageViews,
        view_manager: ViewManager,
        splitter_manager: SplitterManager,
        layout_state: HomePageLayoutState,
    ) -> None:
        """Build primary-image and analysis/reference splitters.

        Args:
            views: Home page view instances.
            view_manager: View lifecycle registry.
            splitter_manager: Splitter state manager.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        primary_preset = HOME_SPLITTER_PRESETS[SplitterId.PRIMARY_IMAGE]
        with ui.splitter(
            value=splitter_manager.value_for(SplitterId.PRIMARY_IMAGE),
            limits=primary_preset.limits,
            horizontal=True,
        ).classes('w-full h-full min-h-0 mt-[6px]') as primary_splitter:
            splitter_manager.register(SplitterId.PRIMARY_IMAGE, primary_splitter)

            with primary_splitter.before:
                self._build_primary_image_pane(views, view_manager)

            with primary_splitter.after:
                self._build_analysis_reference_splitter(views, view_manager, splitter_manager, layout_state)

            add_splitter_handle(primary_splitter, orientation='horizontal')
            primary_splitter.on(
                'update:model-value',
                lambda _event=None: self._capture_splitter(splitter_manager, SplitterId.PRIMARY_IMAGE),
                throttle=0.2,
            )

    def _build_primary_image_pane(self, views: HomePageViews, view_manager: ViewManager) -> None:
        """Build the primary image pane.

        Args:
            views: Home page view instances.
            view_manager: View lifecycle registry.

        Returns:
            None.
        """
        with ui.column().classes(self._fill_column_classes()):
            views.image_toolbar.build()
            view_manager.register(views.image_toolbar)
            views.primary_image.build()
            view_manager.register(views.primary_image)

    def _build_analysis_reference_splitter(
        self,
        views: HomePageViews,
        view_manager: ViewManager,
        splitter_manager: SplitterManager,
        layout_state: HomePageLayoutState,
    ) -> None:
        """Build the analysis plot and reference image panes.

        Args:
            views: Home page view instances.
            view_manager: View lifecycle registry.
            splitter_manager: Splitter state manager.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        analysis_preset = HOME_SPLITTER_PRESETS[SplitterId.ANALYSIS_REFERENCE]
        with ui.splitter(
            value=splitter_manager.value_for(SplitterId.ANALYSIS_REFERENCE),
            limits=analysis_preset.limits,
            horizontal=True,
        ).classes('w-full h-full min-h-0 mt-[6px]') as analysis_reference_splitter:
            splitter_manager.register(SplitterId.ANALYSIS_REFERENCE, analysis_reference_splitter)

            with analysis_reference_splitter.before:
                self._build_analysis_plot_pane(views, view_manager)

            with analysis_reference_splitter.after:
                self._build_reference_pane(views, view_manager, splitter_manager, layout_state)

            add_splitter_handle(analysis_reference_splitter, orientation='horizontal')
            analysis_reference_splitter.on(
                'update:model-value',
                lambda _event=None: self._capture_splitter(splitter_manager, SplitterId.ANALYSIS_REFERENCE),
                throttle=0.2,
            )

    def _build_analysis_plot_pane(self, views: HomePageViews, view_manager: ViewManager) -> None:
        """Build the analysis plot pane without SmartExpansion.

        Args:
            views: Home page view instances.
            view_manager: View lifecycle registry.

        Returns:
            None.
        """
        with ui.column().classes(self._fill_column_classes()):
            views.acq_analysis_plot.show()
            views.acq_analysis_plot.build()
            view_manager.register(views.acq_analysis_plot)

    def _build_reference_pane(
        self,
        views: HomePageViews,
        view_manager: ViewManager,
        splitter_manager: SplitterManager,
        layout_state: HomePageLayoutState,
    ) -> None:
        """Build the Reference Image SmartExpansion pane.

        Args:
            views: Home page view instances.
            view_manager: View lifecycle registry.
            splitter_manager: Splitter state manager.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        with ui.column().classes(self._scrollable_fill_column_classes()):
            reference_image_expansion = SmartExpansion(
                'Reference image',
                icon='image',
                initially_open=False,
                on_open=lambda: self._open_reference_image_panel(views, splitter_manager, layout_state),
                on_close=lambda: self._close_reference_image_panel(views, splitter_manager, layout_state),
            )
            layout_state.expansions['reference_image'] = reference_image_expansion
            with reference_image_expansion:
                views.reference_image.build()
            reference_image_expansion.apply_initial_state()
            view_manager.register(views.reference_image)

            if SHOW_EMBEDDED_VELOCITY_POOL and views.velocity_pool_view is not None:
                velocity_pool_expansion = SmartExpansion(
                    'Velocity pool',
                    icon='table_chart',
                    initially_open=False,
                    on_open=lambda: self._open_velocity_pool_panel(views, layout_state),
                    on_close=lambda: self._close_velocity_pool_panel(views, layout_state),
                )
                layout_state.expansions['velocity_pool'] = velocity_pool_expansion
                with velocity_pool_expansion:
                    views.velocity_pool_view.build()
                velocity_pool_expansion.apply_initial_state()
                view_manager.register(views.velocity_pool_view)

    def _subscribe_layout_reset(
        self,
        splitter_manager: SplitterManager,
        layout_state: HomePageLayoutState,
    ) -> None:
        """Subscribe the Home layout reset handler.

        Args:
            splitter_manager: Splitter state manager.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """

        def _reset_home_layout(_event: ResetHomeLayoutIntent | None = None) -> None:
            """Reset Home page splitters and close the left toolbar panel.

            Args:
                _event: Reset intent, ignored.

            Returns:
                None.
            """
            if layout_state.left_toolbar is not None:
                layout_state.left_toolbar.close_panel()
            splitter_manager.reset_all()
            self._reset_home_expansions(layout_state)
            splitter_manager.restore_open_value(SplitterId.FILE_LIST)
            splitter_manager.restore_open_value(SplitterId.PRIMARY_IMAGE)
            splitter_manager.restore_open_value(SplitterId.ANALYSIS_REFERENCE)
            ui.notify('View layout reset', type='positive')

        self.event_bus.subscribe(ResetHomeLayoutIntent, _reset_home_layout)

    def _reset_home_expansions(self, layout_state: HomePageLayoutState) -> None:
        """Restore Home page SmartExpansion panels to their default state.

        Reference image stays collapsed. The optional embedded velocity pool is
        opened only when it exists.

        Args:
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        for key, expansion in layout_state.expansions.items():
            if expansion is None:
                continue
            if key == 'reference_image':
                expansion.close()
            else:
                expansion.open()
        layout_state.panel_open['file_list'] = True
        layout_state.panel_open['analysis_plot'] = True
        layout_state.panel_open['reference_image'] = False
        layout_state.panel_open['velocity_pool'] = True

    def _open_reference_image_panel(
        self,
        views: HomePageViews,
        splitter_manager: SplitterManager,
        layout_state: HomePageLayoutState,
    ) -> None:
        """Show reference image view and apply shared splitter layout.

        Args:
            views: Home page view instances.
            splitter_manager: Splitter state manager.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        layout_state.panel_open['reference_image'] = True
        views.reference_image.show()
        self._sync_analysis_reference_layout(splitter_manager, layout_state)

    def _close_reference_image_panel(
        self,
        views: HomePageViews,
        splitter_manager: SplitterManager,
        layout_state: HomePageLayoutState,
    ) -> None:
        """Hide reference image view and apply shared splitter layout.

        Args:
            views: Home page view instances.
            splitter_manager: Splitter state manager.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        layout_state.panel_open['reference_image'] = False
        views.reference_image.hide()
        self._sync_analysis_reference_layout(splitter_manager, layout_state)

    def _open_velocity_pool_panel(self, views: HomePageViews, layout_state: HomePageLayoutState) -> None:
        """Show the optional embedded velocity pool.

        Args:
            views: Home page view instances.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        if views.velocity_pool_view is None:
            return
        layout_state.panel_open['velocity_pool'] = True
        views.velocity_pool_view.show()

    def _close_velocity_pool_panel(self, views: HomePageViews, layout_state: HomePageLayoutState) -> None:
        """Hide the optional embedded velocity pool.

        Args:
            views: Home page view instances.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        if views.velocity_pool_view is None:
            return
        layout_state.panel_open['velocity_pool'] = False
        views.velocity_pool_view.hide()

    def _sync_analysis_reference_layout(
        self,
        splitter_manager: SplitterManager,
        layout_state: HomePageLayoutState,
    ) -> None:
        """Apply splitter layout for analysis/reference expansion state.

        Args:
            splitter_manager: Splitter state manager.
            layout_state: Mutable layout references and open flags.

        Returns:
            None.
        """
        analysis_open = layout_state.panel_open['analysis_plot']
        reference_open = layout_state.panel_open['reference_image']
        if analysis_open or reference_open:
            splitter_manager.restore_open_value(SplitterId.PRIMARY_IMAGE)
        else:
            splitter_manager.collapse_pane(SplitterId.PRIMARY_IMAGE, 'after')
            return

        if analysis_open and reference_open:
            splitter_manager.restore_open_value(SplitterId.ANALYSIS_REFERENCE)
        elif analysis_open:
            splitter_manager.collapse_pane(SplitterId.ANALYSIS_REFERENCE, 'after')
        else:
            splitter_manager.collapse_pane(SplitterId.ANALYSIS_REFERENCE, 'before')

    def _bind_controllers(self) -> None:
        """Bind page-level controllers after views have been built.

        Returns:
            None.
        """
        ContrastController(
            event_bus=self.event_bus,
            home_controller=self.controller,
        ).bind()
        XRangeController(
            event_bus=self.event_bus,
            home_controller=self.controller,
        ).bind()

    def _install_disconnect_handler(self, view_manager: ViewManager) -> None:
        """Disconnect all registered views when the browser client disconnects.

        Args:
            view_manager: View lifecycle registry.

        Returns:
            None.
        """

        def _on_client_disconnect() -> None:
            for view_id in view_manager.view_ids():
                view_manager.get(view_id).on_hide()

        ui.context.client.on_disconnect(_on_client_disconnect)

    def _install_native_window_handlers(self) -> None:
        """Install native window move/resize handlers when available.

        Returns:
            None.
        """
        native = getattr(app, 'native', None)
        if native is not None and getattr(native, 'main_window', None) is not None:
            app.native.on('resized', self._native_resize)
            app.native.on('moved', self._native_moved)

    def _capture_splitter(self, splitter_manager: SplitterManager, splitter_id: SplitterId) -> None:
        """Capture a user-adjusted splitter value in AppConfig memory.

        Args:
            splitter_manager: Splitter state manager.
            splitter_id: Splitter that changed.

        Returns:
            None.
        """
        splitter_manager.capture_current_value(splitter_id)

    def _content_column_classes(self, extra: str = '') -> str:
        """Return common content column classes.

        Args:
            extra: Extra Tailwind/NiceGUI classes.

        Returns:
            Class string for content columns.
        """
        base = 'w-full h-full min-h-0 gap-3 p-3 overflow-auto'
        return f'{base} {extra}'.strip()

    def _fill_column_classes(self, extra: str = '') -> str:
        """Return classes for splitter panes that should fill without page scroll.

        Args:
            extra: Extra Tailwind/NiceGUI classes.

        Returns:
            Class string for fill-layout columns.
        """
        base = 'w-full h-full min-h-0 gap-3 p-3 overflow-hidden flex flex-col'
        return f'{base} {extra}'.strip()

    def _scrollable_fill_column_classes(self, extra: str = '') -> str:
        """Return classes for fill-layout panes with internal scrolling.

        Args:
            extra: Extra Tailwind/NiceGUI classes.

        Returns:
            Class string for scrollable fill-layout columns.
        """
        base = 'w-full h-full min-h-0 gap-3 p-3 overflow-auto flex flex-col flex-nowrap'
        return f'{base} {extra}'.strip()

    def _main_scroll_shell_classes(self) -> str:
        """Return classes for the right-side Home workspace scroll shell.

        Returns:
            Class string for the scroll shell around the right-side splitters.
        """
        return 'w-full h-full min-h-0 overflow-y-auto overflow-x-hidden'

    def _main_scroll_content_classes(self) -> str:
        """Return classes for the scrollable right-side splitter content.

        The minimum height preserves the splitter-driven layout while making the
        full stack reachable on short desktop windows.

        Returns:
            Class string for the right-side splitter content.
        """
        return 'w-full h-full min-h-[900px]'

    # abb 20260323 pywebview native save png (clipboard)
    def _native_resize(self, e):  # we also can do this:
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
        native = getattr(app, 'native', None)
        if native is None:
            logger.debug('skipping (not native mode)')
            return

        # logger.info("installing (native mode detected)")

        async def _persist_on_shutdown() -> None:
            """Persist user and app config on shutdown without touching native window APIs."""
            self.app_config.save()

        app.on_shutdown(_persist_on_shutdown)


@ui.page('/')
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
