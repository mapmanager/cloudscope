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
from cloudscope.runtime import CloudScopeRuntime, get_current_runtime
from cloudscope.session_state import HomePageChromeState, HomePageSessionSnapshot
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
# from cloudscope.views.reference_image_view import ReferenceImageView  # 20260629 home reference image commented out
from cloudscope.views.sum_intensity_plot_view import SumIntensityPlotView
from cloudscope.views.task_progress_dialog_view import TaskProgressDialogView
from cloudscope.views.velocity_pool_view import VelocityPoolView
from cloudscope.views.view_manager import ViewManager
from cloudscope.views.splitter_handle import add_splitter_handle
from cloudscope.views.splitter_manager import HOME_SPLITTER_PRESETS, SplitterId, SplitterManager

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)


def _selection_snapshot(runtime: CloudScopeRuntime) -> str:
    """Return a compact primary-selection string for session-state logs.

    Args:
        runtime: Active CloudScope runtime for the current client.

    Returns:
        Human-readable selection summary.
    """
    sel = runtime.home_page_controller.state.selection
    return (
        f'file_id={sel.file_id!r} channel={sel.channel} roi_id={sel.roi_id} '
        f'analysis_name={sel.analysis_name!r}'
    )


def _log_home_session_state(
    phase: str,
    *,
    runtime: CloudScopeRuntime,
    client_id: str | None = None,
    view_count: int | None = None,
    note: str = '',
) -> None:
    """Log runtime vs config state during home-page connect/build/disconnect.

    Args:
        phase: Short label for the point in the home-page lifecycle.
        runtime: Active CloudScope runtime for the current client.
        client_id: NiceGUI client id when available.
        view_count: Number of registered views after ``HomePage.build()``.
        note: Optional extra context appended to the log line.

    Returns:
        None.
    """
    state = runtime.home_page_controller.state
    acq_list = state.acq_image_list
    acq_image_list_status = 'loaded' if acq_list is not None else 'none'
    file_count = len(state.file_ids) if acq_list is not None else 0
    config_last_path = runtime.app_config.get_last_path()

    logger.info('home_page [%s]', phase)
    logger.info('  client_id=%s', client_id)
    logger.info('  runtime_initialized=%s', runtime.initialized)
    logger.info('  acq_image_list=%s', acq_image_list_status)
    logger.info('  file_count=%s', file_count)
    logger.info('  selection=%s', _selection_snapshot(runtime))
    logger.info('  config_last_path=%r', config_last_path)
    if view_count is not None:
        logger.info('  view_count=%s', view_count)
    if note:
        logger.info('  note=%s', note)


SHOW_EMBEDDED_VELOCITY_POOL = False
SHOW_VELOCITY_POOL_RIGHT_PANEL = True

# HOME_WORKSPACE_CLOSED_HEIGHT_CSS = 'calc(100vh - 4rem)'
# HOME_WORKSPACE_REFERENCE_OPEN_HEIGHT_CSS = 'calc(100vh - 4rem + 420px)'
HOME_WORKSPACE_CLOSED_HEIGHT_CSS = 'calc(100vh - 4rem + 120px)'
# HOME_WORKSPACE_REFERENCE_OPEN_HEIGHT_CSS = 'calc(100vh - 4rem + 520px)'  # 20260629 home reference image commented out


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

    def build(self, *, reconnect: bool = False) -> None:
        """Build the page UI and load initial AcqStore state.

        Args:
            reconnect: When True, restore page chrome from the last disconnect
                snapshot and defer view hydrates until
                :class:`HomePageSessionReconnectRestore`.

        Returns:
            None.
        """
        logger.info('=== === === build(start) === === ===')
        runtime = get_current_runtime()
        reconnect_chrome: HomePageChromeState | None = None
        if reconnect and runtime.session_snapshot is not None:
            reconnect_chrome = runtime.session_snapshot.chrome
        _log_home_session_state(
            'build(start)',
            runtime=get_current_runtime(),
            client_id=getattr(ui.context.client, 'id', None),
        )

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
        file_list_panel.set_blinded_provider(self.app_config.get_blinded)
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
            app_config=self.app_config,
            app_state=app_state,
        )
        acq_analysis_plot = AcqAnalysisPlotView(
            self.event_bus,
            app_state=app_state,
            title='Analysis plot',
            initially_visible=False,
            dark_mode=dark_mode,
            dark_mode_provider=_dark_mode,
        )
        sum_intensity_plot = SumIntensityPlotView(
            self.event_bus,
            app_state=app_state,
            title='Sum intensity plot',
            initially_visible=False,
            dark_mode=dark_mode,
            dark_mode_provider=_dark_mode,
        )
        # reference_image = ReferenceImageView(  # 20260629 home reference image commented out
        #     self.event_bus,  # 20260629 home reference image commented out
        #     app_state=app_state,  # 20260629 home reference image commented out
        #     title='Reference image',  # 20260629 home reference image commented out
        #     initially_visible=False,  # 20260629 home reference image commented out
        #     dark_mode=dark_mode,  # 20260629 home reference image commented out
        #     dark_mode_provider=_dark_mode,  # 20260629 home reference image commented out
        #     raster_display_cache=get_current_runtime().raster_display_cache,  # 20260629 home reference image commented out
        # )  # 20260629 home reference image commented out
        velocity_pool_view: VelocityPoolView | None = None
        if SHOW_EMBEDDED_VELOCITY_POOL:
            velocity_pool_view = VelocityPoolView(
                event_bus=self.event_bus,
                app_state=app_state,
                table_font_size_px=int(self.app_config.data.table_font_size_px),
                initially_visible=False,
                dark_mode=dark_mode,
                dark_mode_provider=_dark_mode,
                blinded_provider=self.app_config.get_blinded,
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
                blinded_provider=self.app_config.get_blinded,
            )
        footer = FooterView(
            event_bus=self.event_bus,
            app_state=app_state,
            initially_visible=True,
            blinded_provider=self.app_config.get_blinded,
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
            'analysis_plot': None,
            # 'reference_image': None,  # 20260629 home reference image commented out
            'velocity_pool': None,
        }
        file_list_header_chevron_ref: dict[str, ui.icon | None] = {'value': None}
        chrome_defaults = HomePageChromeState.defaults()
        panel_open_state = {
            'file_list': (
                reconnect_chrome.file_list_open
                if reconnect_chrome is not None
                else chrome_defaults.file_list_open
            ),
            'analysis_plot': (
                reconnect_chrome.analysis_plot_open
                if reconnect_chrome is not None
                else chrome_defaults.analysis_plot_open
            ),
            'reference_image': (
                reconnect_chrome.reference_image_open
                if reconnect_chrome is not None
                else chrome_defaults.reference_image_open
            ),
            'velocity_pool': (
                reconnect_chrome.velocity_pool_open
                if reconnect_chrome is not None
                else chrome_defaults.velocity_pool_open
            ),
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

        def _sync_file_list_header() -> None:
            """Update the file-list header chevron to match panel open state.

            Returns:
                None.
            """
            chevron = file_list_header_chevron_ref['value']
            if chevron is None:
                return
            if panel_open_state['file_list']:
                chevron.classes(add='rotate-180', remove='rotate-0')
            else:
                chevron.classes(add='rotate-0', remove='rotate-180')

        def _open_file_list_panel() -> None:
            """Show file list view and restore its splitter pane when opening from closed.

            Returns:
                None.
            """
            was_closed = not panel_open_state['file_list']
            panel_open_state['file_list'] = True
            if was_closed:
                splitter_manager.restore_open_value(SplitterId.FILE_LIST)
            file_list_panel.show()
            _sync_file_list_header()

        def _close_file_list_panel() -> None:
            """Hide file list view and collapse its splitter pane.

            Returns:
                None.
            """
            panel_open_state['file_list'] = False
            file_list_panel.hide()
            splitter_manager.collapse_file_list_to_peek()
            _sync_file_list_header()

        def _toggle_file_list_panel() -> None:
            """Toggle home file-list panel open or closed.

            Returns:
                None.
            """
            if panel_open_state['file_list']:
                _close_file_list_panel()
            else:
                _open_file_list_panel()

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

        # def _open_reference_image_panel() -> None:  # 20260629 home reference image commented out
        #     """Show reference image view and apply shared splitter layout.  # 20260629 home reference image commented out
        #
        #     Returns:  # 20260629 home reference image commented out
        #         None.  # 20260629 home reference image commented out
        #     """  # 20260629 home reference image commented out
        #     panel_open_state['reference_image'] = True  # 20260629 home reference image commented out
        #     _set_workspace_frame_height(HOME_WORKSPACE_REFERENCE_OPEN_HEIGHT_CSS)  # 20260629 home reference image commented out
        #     reference_image.show()  # 20260629 home reference image commented out
        #     _sync_analysis_reference_layout()  # 20260629 home reference image commented out
        #
        # def _close_reference_image_panel() -> None:  # 20260629 home reference image commented out
        #     """Hide reference image view and apply shared splitter layout.  # 20260629 home reference image commented out
        #
        #     Returns:  # 20260629 home reference image commented out
        #         None.  # 20260629 home reference image commented out
        #     """  # 20260629 home reference image commented out
        #     panel_open_state['reference_image'] = False  # 20260629 home reference image commented out
        #     reference_image.hide()  # 20260629 home reference image commented out
        #     _set_workspace_frame_height(HOME_WORKSPACE_CLOSED_HEIGHT_CSS)  # 20260629 home reference image commented out
        #     _sync_analysis_reference_layout()  # 20260629 home reference image commented out

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

        def _sync_panels_from_chrome() -> None:
            """Apply ``panel_open_state`` to visible panels and splitters.

            Returns:
                None.
            """
            if panel_open_state['file_list']:
                _open_file_list_panel()
            else:
                _close_file_list_panel()
            if panel_open_state['analysis_plot']:
                _open_analysis_plot_panel()
            else:
                _close_analysis_plot_panel()
            if panel_open_state['velocity_pool']:
                _open_velocity_pool_panel()
            else:
                _close_velocity_pool_panel()

        def _reset_home_expansions() -> None:
            """Restore Home page panels to their default open state.

            Reference image stays collapsed; other panels are opened.

            Returns:
                None.
            """
            _open_file_list_panel()
            for expansion in home_expansion_refs.values():
                if expansion is None:
                    continue
                # if key == 'reference_image':  # 20260629 home reference image commented out
                #     expansion.close()  # 20260629 home reference image commented out
                # else:  # 20260629 home reference image commented out
                expansion.open()
            panel_open_state['analysis_plot'] = True
            # panel_open_state['reference_image'] = False  # 20260629 home reference image commented out
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
            splitter_manager.restore_open_value(SplitterId.ANALYSIS_SUM_INTENSITY)
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
            load_save_view=load_save_view,
            show_open_pool=get_pool_launcher() is not None,
            on_velocity_pool_toggle=(
                _header_toggle_right_pool_panel if SHOW_VELOCITY_POOL_RIGHT_PANEL else None
            ),
        )
        view_manager.register(load_save_view)
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
                            with ui.column().classes(_fill_column_classes('gap-0')):
                                with ui.row().classes(
                                    'w-full items-center gap-2 shrink-0 cursor-pointer py-1 px-1 '
                                    'border-b border-gray-200 dark:border-gray-700'
                                ) as file_list_header:
                                    ui.icon('account_tree').classes('text-lg')
                                    ui.label('File list').classes('flex-1 text-sm font-medium')
                                    file_list_header_chevron = ui.icon('expand_more').classes(
                                        'transition-transform duration-200'
                                    )
                                    file_list_header_chevron_ref['value'] = file_list_header_chevron
                                file_list_header.on('click', _toggle_file_list_panel)

                                with ui.column().classes(
                                    'w-full flex-1 min-h-0 flex flex-col overflow-hidden'
                                ):
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
                                            analysis_sum_intensity_preset = HOME_SPLITTER_PRESETS[
                                                SplitterId.ANALYSIS_SUM_INTENSITY
                                            ]
                                            with ui.splitter(
                                                value=splitter_manager.value_for(SplitterId.ANALYSIS_SUM_INTENSITY),
                                                limits=analysis_sum_intensity_preset.limits,
                                                horizontal=True,
                                            ).classes('w-full h-full min-h-0') as analysis_sum_intensity_splitter:
                                                splitter_manager.register(
                                                    SplitterId.ANALYSIS_SUM_INTENSITY,
                                                    analysis_sum_intensity_splitter,
                                                )

                                                with analysis_sum_intensity_splitter.before:
                                                    with ui.column().classes(_fill_column_classes()):
                                                        acq_analysis_plot.show()
                                                        acq_analysis_plot.build()
                                                        view_manager.register(acq_analysis_plot)

                                                with analysis_sum_intensity_splitter.after:
                                                    with ui.column().classes(_fill_column_classes()):
                                                        sum_intensity_plot.show()
                                                        sum_intensity_plot.build()
                                                        view_manager.register(sum_intensity_plot)

                                                add_splitter_handle(
                                                    analysis_sum_intensity_splitter,
                                                    orientation='horizontal',
                                                )
                                                analysis_sum_intensity_splitter.on(
                                                    'update:model-value',
                                                    lambda _event=None: _capture(SplitterId.ANALYSIS_SUM_INTENSITY),
                                                    throttle=0.2,
                                                )

                                        with analysis_reference_splitter.after:
                                            with ui.column().classes(_fill_column_classes()):
                                                # reference_image_expansion = SmartExpansion(  # 20260629 home reference image commented out
                                                #     'Reference image',  # 20260629 home reference image commented out
                                                #     icon='image',  # 20260629 home reference image commented out
                                                #     initially_open=False,  # 20260629 home reference image commented out
                                                #     on_open=_open_reference_image_panel,  # 20260629 home reference image commented out
                                                #     on_close=_close_reference_image_panel,  # 20260629 home reference image commented out
                                                # )  # 20260629 home reference image commented out
                                                # home_expansion_refs['reference_image'] = reference_image_expansion  # 20260629 home reference image commented out
                                                # with reference_image_expansion:  # 20260629 home reference image commented out
                                                #     reference_image.build()  # 20260629 home reference image commented out
                                                # reference_image_expansion.apply_initial_state()  # 20260629 home reference image commented out
                                                # view_manager.register(reference_image)  # 20260629 home reference image commented out

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

                    _sync_panels_from_chrome()

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
                    dark_mode=dark_mode,
                    dark_mode_provider=_dark_mode,
                    raster_display_cache=get_current_runtime().raster_display_cache,
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

                    def _sync_right_pool_splitter_drag() -> None:
                        """Freeze right-pool splitter drag while the panel is collapsed.

                        Returns:
                            None.
                        """
                        splitter_manager.set_splitter_drag_enabled(
                            SplitterId.RIGHT_POOL,
                            splitter_manager.is_right_pool_open(),
                        )

                    right_pool_toggle_ref['value'] = _toggle_right_pool_panel

                    right_pool_preset = HOME_SPLITTER_PRESETS[SplitterId.RIGHT_POOL]
                    with ui.splitter(
                        value=splitter_manager.value_for(SplitterId.RIGHT_POOL),
                        limits=right_pool_preset.limits,
                    ).classes('w-full h-full min-h-0 overflow-hidden') as right_pool_splitter:
                        splitter_manager.register(SplitterId.RIGHT_POOL, right_pool_splitter)
                        if not splitter_manager.is_right_pool_open():
                            splitter_manager.set_splitter_drag_enabled(SplitterId.RIGHT_POOL, False)

                        with right_pool_splitter.before:
                            _build_main_workspace()

                        with right_pool_splitter.after:
                            with ui.column().classes(_fill_column_classes()) as right_pool_column:
                                right_pool_column_ref['value'] = right_pool_column

                        add_splitter_handle(
                            right_pool_splitter,
                            orientation='vertical',
                            offset='before',
                            show_handle=False,
                            on_dblclick=_toggle_right_pool_panel,
                        )
                        right_pool_splitter.on(
                            'update:model-value',
                            lambda _event=None: (
                                _capture(SplitterId.RIGHT_POOL),
                                _sync_right_pool_panel(),
                                _sync_right_pool_splitter_drag(),
                            ),
                            throttle=0.2,
                        )

                    _sync_right_pool_panel()
                else:
                    _build_main_workspace()

            add_splitter_handle(left_splitter, orientation='vertical', offset='after', show_handle=False)
            left_splitter.on(
                'update:model-value',
                lambda _event=None: _capture(SplitterId.LEFT_TOOLBAR),
                throttle=0.2,
            )

        contrast_controller.bind()
        x_range_controller.bind()

        def _on_client_disconnect() -> None:
            runtime = get_current_runtime()
            runtime.session_snapshot = HomePageSessionSnapshot(
                chrome=HomePageChromeState.from_panel_open(panel_open_state),
                views=view_manager.collect_session_state(),
            )
            _log_home_session_state(
                'client_disconnect',
                runtime=runtime,
                client_id=getattr(ui.context.client, 'id', None),
                view_count=len(view_manager.view_ids()),
                note='captured session snapshot; hiding views',
            )
            for view_id in view_manager.view_ids():
                view_manager.get(view_id).on_hide()

        ui.context.client.on_disconnect(_on_client_disconnect)

        _log_home_session_state(
            'build(complete)',
            runtime=get_current_runtime(),
            client_id=getattr(ui.context.client, 'id', None),
            view_count=len(view_manager.view_ids()),
            note='GUI widgets rebuilt; views hydrate from runtime state and/or pending load events',
        )
        logger.info('=== === === build(complete) === === ===')

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
    client_id = getattr(ui.context.client, 'id', None)
    was_initialized = runtime.initialized
    had_acq_image_list = runtime.home_page_controller.state.acq_image_list is not None
    config_last_path = runtime.app_config.get_last_path().strip()

    _log_home_session_state(
        'connect(before initialize_once)',
        runtime=runtime,
        client_id=client_id,
    )

    runtime.initialize_once()

    if not was_initialized:
        if had_acq_image_list:
            logger.info(
                'home_page bootstrap: initialize_once skipped LoadPathIntent because '
                'acq_image_list was already loaded before first initialize_once'
            )
        elif config_last_path:
            logger.info(
                'home_page bootstrap: initialize_once published LoadPathIntent for '
                'config last_path=%r (load is async; GUI build may run before load completes)',
                config_last_path,
            )
        else:
            logger.info(
                'home_page bootstrap: initialize_once finished with no config last_path; '
                'starting from empty demo file list'
            )
    else:
        logger.info(
            'home_page reconnect: initialize_once skipped (runtime_initialized=True); '
            'repopulating GUI from existing runtime state (no new LoadPathIntent). '
            'acq_image_list=%s selection=%s config_last_path=%r',
            'loaded' if runtime.home_page_controller.state.acq_image_list is not None else 'none',
            _selection_snapshot(runtime),
            config_last_path or None,
        )

    _log_home_session_state(
        'connect(after initialize_once)',
        runtime=runtime,
        client_id=client_id,
    )

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
    if was_initialized:
        runtime.reconnect_build_in_progress = True
    page.build(reconnect=was_initialized)

    if was_initialized:
        snapshot = runtime.session_snapshot or HomePageSessionSnapshot.empty()
        runtime.home_page_controller.publish_session_reconnect_restore(snapshot)
    runtime.reconnect_build_in_progress = False

