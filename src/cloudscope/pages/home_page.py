"""NiceGUI home page for CloudScope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
SHOW_VELOCITY_POOL_RIGHT_PANEL = True

# HOME_WORKSPACE_CLOSED_HEIGHT_CSS = 'calc(100vh - 4rem)'
# HOME_WORKSPACE_REFERENCE_OPEN_HEIGHT_CSS = 'calc(100vh - 4rem + 420px)'
HOME_WORKSPACE_CLOSED_HEIGHT_CSS = 'calc(100vh - 4rem + 120px)'
HOME_WORKSPACE_REFERENCE_OPEN_HEIGHT_CSS = 'calc(100vh - 4rem + 520px)'


@dataclass(slots=True)
class HomePage:
    """Compose the home page and its per-page objects.

    Args:
        controller: Home page controller.
        load_save_controller: Load/save controller.
        event_bus: Share d runtime event bus.
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
        self._register_native_geometry_handlers()

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
        right_panel_velocity_pool_view: VelocityPoolView | None = None
        if SHOW_VELOCITY_POOL_RIGHT_PANEL:
            right_panel_velocity_pool_view = VelocityPoolView(
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
        right_pool_toggle_ref: dict[str, Any | None] = {'value': None}
        right_pool_column_ref: dict[str, ui.element | None] = {'value': None}
        workspace_frame_ref: dict[str, Any | None] = {'value': None}
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
            """Return classes for the right-side Home page scroll owner.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for the single vertical scroll shell.
            """
            base = 'w-full h-full min-h-0 overflow-y-auto overflow-x-hidden'
            return f'{base} {extra}'.strip()

        def _workspace_frame_classes(extra: str = '') -> str:
            """Return classes for the fixed-height splitter workspace frame.

            The nested Home splitters fill this frame.  The frame height is
            adjusted when the reference-image SmartExpansion opens so the
            outer scroll shell has more scrollable content without replacing
            the splitter-based workspace.

            Args:
                extra: Extra Tailwind/NiceGUI classes.

            Returns:
                Class string for the splitter workspace frame.
            """
            base = 'w-full min-h-0 overflow-visible'
            return f'{base} {extra}'.strip()

        def _workspace_frame_style(height_css: str) -> str:
            """Return inline style for the right-side splitter workspace frame.

            Args:
                height_css: CSS height expression.

            Returns:
                Inline style string with matching height and minimum height.
            """
            return f'height: {height_css}; min-height: {height_css};'

        def _set_workspace_frame_height(height_css: str) -> None:
            """Set the right-side splitter workspace frame height.

            Args:
                height_css: CSS height expression.

            Returns:
                None.
            """
            frame = workspace_frame_ref['value']
            if frame is None:
                return
            # frame.style(_workspace_frame_style(height_css), replace=True)
            frame.style(replace=_workspace_frame_style(height_css))

        def _capture(splitter_id: SplitterId) -> None:
            """Capture a user-adjusted splitter value in AppConfig memory.

            Args:
                splitter_id: Splitter that changed.

            Returns:
                None.
            """
            splitter_manager.capture_current_value(splitter_id)

        def _sync_analysis_reference_layout() -> None:
            """Apply splitter layout for analysis/reference expansion state.

            Returns:
                None.
            """
            analysis_open = panel_open_state['analysis_plot']
            reference_open = panel_open_state['reference_image']
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

        def _open_file_list_panel() -> None:
            """Show file list view and restore its splitter pane.

            Returns:
                None.
            """
            panel_open_state['file_list'] = True
            splitter_manager.restore_open_value(SplitterId.FILE_LIST)
            file_list_panel.show()

        def _close_file_list_panel() -> None:
            """Hide file list view and collapse its splitter pane.

            Returns:
                None.
            """
            panel_open_state['file_list'] = False
            file_list_panel.hide()
            splitter_manager.collapse_pane(SplitterId.FILE_LIST, 'before')

        def _open_analysis_plot_panel() -> None:
            """Show analysis plot view and apply shared splitter layout.

            Returns:
                None.
            """
            panel_open_state['analysis_plot'] = True
            acq_analysis_plot.show()
            _sync_analysis_reference_layout()

        def _close_analysis_plot_panel() -> None:
            """Hide analysis plot view and apply shared splitter layout.

            Returns:
                None.
            """
            panel_open_state['analysis_plot'] = False
            acq_analysis_plot.hide()
            _sync_analysis_reference_layout()

        def _open_reference_image_panel() -> None:
            """Show reference image view and apply shared splitter layout.

            Returns:
                None.
            """
            panel_open_state['reference_image'] = True
            _set_workspace_frame_height(HOME_WORKSPACE_REFERENCE_OPEN_HEIGHT_CSS)
            reference_image.show()
            _sync_analysis_reference_layout()

        def _close_reference_image_panel() -> None:
            """Hide reference image view and apply shared splitter layout.

            Returns:
                None.
            """
            panel_open_state['reference_image'] = False
            reference_image.hide()
            _set_workspace_frame_height(HOME_WORKSPACE_CLOSED_HEIGHT_CSS)
            _sync_analysis_reference_layout()

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
            _set_workspace_frame_height(HOME_WORKSPACE_CLOSED_HEIGHT_CSS)

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
            splitter_manager.restore_open_value(SplitterId.FILE_LIST)
            splitter_manager.restore_open_value(SplitterId.PRIMARY_IMAGE)
            splitter_manager.restore_open_value(SplitterId.ANALYSIS_REFERENCE)
            ui.notify('View layout reset', type='positive')

        self.event_bus.subscribe(ResetHomeLayoutIntent, _reset_home_layout)

        ui.page_title('CloudScope')

        # abb removes browser/body scrolling (leaves only overflow-y-auto)
        ui.add_head_html(
            """
            <style>
            html,
            body,
            #app {
                height: 100%;
                overflow: hidden;
            }
            </style>
            """
        )

        def _header_toggle_right_pool_panel() -> None:
            """Toggle the right velocity-pool panel from the header button.

            Returns:
                None.
            """
            toggle = right_pool_toggle_ref['value']
            if toggle is not None:
                toggle()

        from cloudscope.desktop_launcher import get_pool_launcher

        build_main_header(
            title='CloudScope',
            app_config=self.app_config,
            event_bus=self.event_bus,
            show_open_pool=get_pool_launcher() is not None,
            on_velocity_pool_toggle=(
                _header_toggle_right_pool_panel if SHOW_VELOCITY_POOL_RIGHT_PANEL else None
            ),
        )
        footer.build()
        view_manager.register(footer)
        task_progress_dialog.build()
        view_manager.register(task_progress_dialog)

        def _build_main_workspace() -> None:
            """Build the central home workspace inside the current parent pane.

            Returns:
                None.
            """
            with ui.element('div').classes(_main_scroll_shell_classes()):
                with ui.element('div').classes(_workspace_frame_classes()).style(
                    _workspace_frame_style(HOME_WORKSPACE_CLOSED_HEIGHT_CSS)
                ) as workspace_frame:
                    workspace_frame_ref['value'] = workspace_frame
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

                                file_list_panel.show()
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
                                        splitter_manager.register(
                                            SplitterId.ANALYSIS_REFERENCE,
                                            analysis_reference_splitter,
                                        )

                                        with analysis_reference_splitter.before:
                                            with ui.column().classes(_fill_column_classes()):
                                                acq_analysis_plot.show()
                                                acq_analysis_plot.build()

                                                view_manager.register(acq_analysis_plot)

                                        with analysis_reference_splitter.after:
                                            with ui.column().classes(_fill_column_classes()):
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
                if SHOW_VELOCITY_POOL_RIGHT_PANEL and right_panel_velocity_pool_view is not None:
                    def _sync_right_pool_panel() -> None:
                        """Build, show, hide, or relayout the right-panel velocity pool.

                        Returns:
                            None.
                        """
                        if right_panel_velocity_pool_view is None:
                            return
                        if not splitter_manager.is_right_pool_open():
                            if right_panel_velocity_pool_view.is_built:
                                right_panel_velocity_pool_view.hide()
                            return

                        parent = right_pool_column_ref['value']
                        if parent is None:
                            return

                        if not right_panel_velocity_pool_view.is_built:
                            right_panel_velocity_pool_view.build(parent=parent)
                            view_manager.register(right_panel_velocity_pool_view)
                            right_panel_velocity_pool_view.show()
                            return

                        right_panel_velocity_pool_view.show()
                        right_panel_velocity_pool_view.relayout_plots()

                    def _toggle_right_pool_panel() -> None:
                        """Toggle the right velocity-pool splitter between open and collapsed.

                        Returns:
                            None.
                        """
                        splitter_manager.set_right_pool_open(not splitter_manager.is_right_pool_open())
                        _sync_right_pool_panel()

                    right_pool_toggle_ref['value'] = _toggle_right_pool_panel

                    right_pool_preset = HOME_SPLITTER_PRESETS[SplitterId.RIGHT_POOL]
                    with ui.splitter(
                        value=splitter_manager.value_for(SplitterId.RIGHT_POOL),
                        limits=right_pool_preset.limits,
                    ).classes('w-full h-full min-h-0 overflow-hidden') as right_pool_splitter:
                        splitter_manager.register(SplitterId.RIGHT_POOL, right_pool_splitter)

                        with right_pool_splitter.before:
                            _build_main_workspace()

                        with right_pool_splitter.after:
                            with ui.column().classes(_fill_column_classes()) as right_pool_column:
                                right_pool_column_ref['value'] = right_pool_column

                        add_splitter_handle(
                            right_pool_splitter,
                            orientation='vertical',
                            offset='before',
                            on_dblclick=_toggle_right_pool_panel,
                        )
                        right_pool_splitter.on(
                            'update:model-value',
                            lambda _event=None: (
                                _capture(SplitterId.RIGHT_POOL),
                                _sync_right_pool_panel(),
                            ),
                            throttle=0.2,
                        )

                    _sync_right_pool_panel()
                else:
                    _build_main_workspace()

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

    def _register_native_geometry_handlers(self) -> None:
        """Register NiceGUI native window geometry handlers.

        Move/resize update in-memory ``AppConfig``; disk persist is on shutdown.

        Returns:
            None.
        """
        if getattr(app, 'native', None) is None:
            return

        app.native.on('resized', self._native_resize)
        app.native.on('moved', self._native_moved)

    def _install_shutdown_handlers(self) -> None:
        """Register app shutdown handlers for native desktop mode.

        Returns:
            None.
        """
        native = getattr(app, "native", None)
        if native is None:
            return

        async def _persist_on_shutdown() -> None:
            """Persist application config on shutdown."""
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

