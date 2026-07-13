"""Left-side toolbar for showing one optional panel view at a time."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from nicegui import ui

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.events.app_config import BlindedAnalysisModeChanged
from cloudscope.raster_display_cache import RasterDisplayCache
from cloudscope.views.app_config_view import AppConfigView
from cloudscope.views.app_info_view import AppInfoView
from cloudscope.views.base_view import BaseView
from cloudscope.views.debug_view import DebugView
from cloudscope.views.metadata_widget.experiment_metadata_view import ExperimentMetadataView
from cloudscope.views.metadata_widget.image_header_metadata_view import ImageHeaderMetadataView
from cloudscope.views.diameter_analysis_view import DiameterAnalysisView
from cloudscope.views.left_panel_file_list_view import LeftPanelFileListView
from cloudscope.views.sum_intensity_analysis_view import SumIntensityAnalysisView
from cloudscope.views.reference_image_view import ReferenceImageView
from cloudscope.views.velocity_analysis_view import VelocityAnalysisView
from cloudscope.views.view_ids import ViewId
from cloudscope.views.view_manager import ViewManager


class LeftPanelReferenceImageView(ReferenceImageView):
    """Reference image panel hosted in the left toolbar."""

    view_id = ViewId.LEFT_TOOLBAR_REFERENCE_IMAGE


@dataclass(frozen=True, slots=True)
class LeftToolbarTab:
    """Configuration for one left-toolbar tab.

    Args:
        view_id: Panel view controlled by this tab.
        label: Human-readable tab label and tooltip.
        icon: Material icon name used by the toolbar button.
    """

    view_id: ViewId
    label: str
    icon: str


_LEFT_TOOLBAR_TABS: tuple[LeftToolbarTab, ...] = (
    LeftToolbarTab(ViewId.LEFT_TOOLBAR_FILE_LIST, "File List", "account_tree"),
    LeftToolbarTab(ViewId.EXPERIMENT_METADATA, "Experimental Metadata", "description"),
    LeftToolbarTab(ViewId.IMAGE_HEADER_METADATA, "Image Header", "biotech"),
    LeftToolbarTab(ViewId.VELOCITY_ANALYSIS, "Velocity", "speed"),
    LeftToolbarTab(ViewId.DIAMETER_ANALYSIS, "Diameter", "straighten"),
    LeftToolbarTab(ViewId.SUM_INTENSITY_ANALYSIS, "Peak Detect", "functions"),
    LeftToolbarTab(ViewId.LEFT_TOOLBAR_REFERENCE_IMAGE, "Reference Image", "image"),
    LeftToolbarTab(ViewId.APP_CONFIG, "Config", "settings"),
    LeftToolbarTab(ViewId.APP_INFO, "App info", "info"),
    LeftToolbarTab(ViewId.DEBUG, "Debug", "bug_report"),
)


class LeftToolbarView(BaseView):
    """Composite left toolbar plus optional left-panel views.

    The toolbar owns its tab definitions and child panel views.  Clicking an
    inactive tab shows the associated panel.  Clicking the active tab hides all
    child panels and returns to the no-active-tab state.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Home-page state used by child views. Analysis children read
            ``visible_file_ids_provider`` from this state when present.
        app_config: Shared app configuration used by the app config child view.
        view_manager: Manager used to register and show/hide child views.
        initially_visible: Whether the toolbar starts visible.
        on_panel_open_changed: Optional callback invoked when the left panel opens or closes.
        dark_mode: Initial Plotly raster-viewer theme for the reference image panel.
        dark_mode_provider: Callable returning current dark-mode state for the reference image panel.
        raster_display_cache: Shared LRU cache for reference image planes and pyramids.
        initial_active_view_id: Left toolbar tab to activate on build, or
            ``None`` to start collapsed. Used to restore the active tab after a
            client disconnect/reconnect.
    """

    view_id = ViewId.LEFT_TOOLBAR
    disable_when_busy = False

    def __init__(
        self,
        *,
        event_bus: EventBus,
        app_state: Any,
        app_config: AppConfig,
        view_manager: ViewManager,
        initially_visible: bool = True,
        on_panel_open_changed: Callable[[bool], None] | None = None,
        dark_mode: bool = False,
        dark_mode_provider: Callable[[], bool] | None = None,
        raster_display_cache: RasterDisplayCache | None = None,
        initial_active_view_id: ViewId | None = None,
    ) -> None:
        super().__init__(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=initially_visible,
            blinded_provider=app_config.get_blinded,
        )
        self._app_config = app_config
        self._view_manager = view_manager
        self._on_panel_open_changed = on_panel_open_changed
        self._initial_active_view_id = initial_active_view_id
        self._active_view_id: ViewId | None = None
        self._buttons: dict[ViewId, ui.button] = {}
        self._left_panel_root: ui.element | None = None
        self.file_list_view = LeftPanelFileListView(
            event_bus=event_bus,
            app_state=app_state,
            table_font_size_px=int(app_config.data.table_font_size_px),
            initially_visible=False,
        )
        self.experiment_metadata_view = ExperimentMetadataView(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=False,
        )
        self.image_header_metadata_view = ImageHeaderMetadataView(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=False,
        )
        self.velocity_analysis_view = VelocityAnalysisView(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=False,
            app_config=app_config,
        )
        self.diameter_analysis_view = DiameterAnalysisView(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=False,
        )
        self.sum_intensity_analysis_view = SumIntensityAnalysisView(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=False,
        )
        self.reference_image_view = LeftPanelReferenceImageView(
            event_bus=event_bus,
            app_state=app_state,
            title='Reference image',
            initially_visible=False,
            dark_mode=dark_mode,
            dark_mode_provider=dark_mode_provider,
            raster_display_cache=raster_display_cache,
            app_config=app_config,
        )
        self.app_config_view = AppConfigView(
            app_config=app_config,
            event_bus=event_bus,
            initially_visible=False,
        )
        self.app_info_view = AppInfoView(
            event_bus=event_bus,
            initially_visible=False,
        )
        self.debug_view = DebugView(
            event_bus=event_bus,
            initially_visible=False,
        )
        for child in (
            self.file_list_view,
            self.experiment_metadata_view,
            self.image_header_metadata_view,
            self.velocity_analysis_view,
            self.velocity_analysis_view.event_analysis_view,
            self.diameter_analysis_view,
            self.sum_intensity_analysis_view,
            self.reference_image_view,
            self.app_config_view,
            self.app_info_view,
            self.debug_view,
        ):
            child.set_blinded_provider(app_config.get_blinded)

    @property
    def active_view_id(self) -> ViewId | None:
        """Return the active left-panel view id.

        Returns:
            Active view id, or None when no panel is shown.
        """
        return self._active_view_id

    @property
    def panel_view_ids(self) -> tuple[ViewId, ...]:
        """Return view ids controlled by this toolbar.

        Returns:
            Tuple of controlled panel view ids.
        """
        return tuple(tab.view_id for tab in _LEFT_TOOLBAR_TABS)

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the composite toolbar and child panel stack.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this composite view.
        """
        def _build() -> None:
            with ui.row().classes("w-full h-full min-h-0 items-start gap-0 overflow-hidden") as self.root:
                with ui.column().classes("h-full min-h-0 shrink-0 items-center gap-1 p-1 overflow-hidden bg-gray-100 dark:bg-gray-900"):
                    self._build_buttons()
                with ui.column().classes("h-full min-h-0 w-full flex-1 gap-3 p-3 overflow-hidden") as panel_root:
                    self._left_panel_root = panel_root
                    self.file_list_view.build()
                    self.experiment_metadata_view.build()
                    self.image_header_metadata_view.build()
                    self.velocity_analysis_view.build()
                    self.diameter_analysis_view.build()
                    self.sum_intensity_analysis_view.build()
                    self.reference_image_view.build()
                    self.app_config_view.build()
                    self.app_info_view.build()
                    self.debug_view.build()

        if parent is None:
            _build()
        else:
            with parent:
                _build()

        self._register_child_views()
        self.after_build()
        self._apply_active_view(self._resolve_initial_active_view_id())
        return self.root

    def _resolve_initial_active_view_id(self) -> ViewId | None:
        """Return the initial active tab, ignoring ids this toolbar can't show.

        Returns:
            Requested initial tab when it is a valid toolbar tab, otherwise
            ``None`` (collapsed).
        """
        requested = self._initial_active_view_id
        if requested is not None and requested in self.panel_view_ids:
            return requested
        return None


    def close_panel(self) -> None:
        """Close the optional left-toolbar panel.

        Returns:
            None.
        """
        self._apply_active_view(None)

    def _register_child_views(self) -> None:
        """Register child panel views with the shared view manager.

        Returns:
            None.
        """
        for view in (
            self.file_list_view,
            self.experiment_metadata_view,
            self.image_header_metadata_view,
            self.velocity_analysis_view,
            self.diameter_analysis_view,
            self.sum_intensity_analysis_view,
            self.reference_image_view,
            self.app_config_view,
            self.app_info_view,
            self.debug_view,
        ):
            if view.view_id not in self._view_manager.view_ids():
                self._view_manager.register(view)

    def _build_buttons(self) -> None:
        """Build toolbar tab buttons.

        Returns:
            None.
        """
        for tab in _LEFT_TOOLBAR_TABS:
            button = ui.button(
                icon=tab.icon,
                on_click=lambda _event=None, view_id=tab.view_id: self._on_tab_clicked(view_id),
            ).props("flat dense round")
            button.tooltip(tab.label)
            self._buttons[tab.view_id] = button

    def _on_tab_clicked(self, view_id: ViewId) -> None:
        """Toggle the clicked panel tab.

        Args:
            view_id: Panel view controlled by the clicked tab.

        Returns:
            None.
        """
        if view_id is ViewId.EXPERIMENT_METADATA and self.is_blinded():
            return
        next_view_id = None if self._active_view_id == view_id else view_id
        self._apply_active_view(next_view_id)

    def _apply_active_view(self, view_id: ViewId | None) -> None:
        """Apply active panel state to child views and panel container.

        Args:
            view_id: Panel view to show, or None to hide all panels.

        Returns:
            None.
        """
        self._active_view_id = view_id
        self._view_manager.show_only(view_id, self.panel_view_ids)
        if self._left_panel_root is not None:
            self._left_panel_root.visible = view_id is not None
            self._left_panel_root.update()
        self._refresh_button_state()
        if self._on_panel_open_changed is not None:
            self._on_panel_open_changed(view_id is not None)

    def _refresh_button_state(self) -> None:
        """Refresh visual state for toolbar buttons.

        Returns:
            None.
        """
        for view_id, button in self._buttons.items():
            if view_id is ViewId.EXPERIMENT_METADATA and self.is_blinded():
                button.enabled = False
                button.update()
                continue
            button.enabled = True
            if view_id == self._active_view_id:
                button.props("flat dense round color=primary")
            else:
                button.props("flat dense round")
            button.update()

    def on_blinded_analysis_mode_changed(self, event: BlindedAnalysisModeChanged) -> None:
        """Close and disable experiment metadata while blinded mode is active."""
        if event.blinded and self._active_view_id is ViewId.EXPERIMENT_METADATA:
            self._apply_active_view(None)
            return
        self._refresh_button_state()
