"""Left-side toolbar for showing one optional panel view at a time."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from nicegui import ui

from cloudscope.app_config import AppConfig
from cloudscope.event_bus import EventBus
from cloudscope.views.app_config_view import AppConfigView
from cloudscope.views.app_info_view import AppInfoView
from cloudscope.views.base_view import BaseView
from cloudscope.views.metadata_widget.metadata_view import MetadataView
from cloudscope.views.diameter_analysis_view import DiameterAnalysisView
from cloudscope.views.event_analysis_view import EventAnalysisView
from cloudscope.views.velocity_analysis_view import VelocityAnalysisView
from cloudscope.views.view_ids import ViewId
from cloudscope.views.view_manager import ViewManager


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
    LeftToolbarTab(ViewId.METADATA, "Metadata", "description"),
    LeftToolbarTab(ViewId.VELOCITY_ANALYSIS, "Velocity", "timeline"),
    LeftToolbarTab(ViewId.DIAMETER_ANALYSIS, "Diameter", "straighten"),
    LeftToolbarTab(ViewId.EVENT_ANALYSIS, "Events", "event"),
    LeftToolbarTab(ViewId.APP_CONFIG, "Config", "settings"),
    LeftToolbarTab(ViewId.APP_INFO, "App info", "info"),
)


class LeftToolbarView(BaseView):
    """Composite left toolbar plus optional left-panel views.

    The toolbar owns its tab definitions and child panel views.  Clicking an
    inactive tab shows the associated panel.  Clicking the active tab hides all
    child panels and returns to the no-active-tab state.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Home-page state used by child views.
        app_config: Shared app configuration used by the app config child view.
        view_manager: Manager used to register and show/hide child views.
        initially_visible: Whether the toolbar starts visible.
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
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._app_config = app_config
        self._view_manager = view_manager
        self._on_panel_open_changed = on_panel_open_changed
        self._active_view_id: ViewId | None = None
        self._buttons: dict[ViewId, ui.button] = {}
        self._left_panel_root: ui.element | None = None
        self.metadata_view = MetadataView(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=False,
        )
        self.velocity_analysis_view = VelocityAnalysisView(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=False,
        )
        self.diameter_analysis_view = DiameterAnalysisView(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=False,
        )
        self.event_analysis_view = EventAnalysisView(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=False,
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
                with ui.column().classes("h-full min-h-0 w-80 gap-3 p-3 overflow-hidden") as panel_root:
                    self._left_panel_root = panel_root
                    self.metadata_view.build()
                    self.velocity_analysis_view.build()
                    self.diameter_analysis_view.build()
                    self.event_analysis_view.build()
                    self.app_config_view.build()
                    self.app_info_view.build()

        if parent is None:
            _build()
        else:
            with parent:
                _build()

        self._register_child_views()
        self.after_build()
        self._apply_active_view(None)
        return self.root


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
            self.metadata_view,
            self.velocity_analysis_view,
            self.diameter_analysis_view,
            self.event_analysis_view,
            self.app_config_view,
            self.app_info_view,
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
            if view_id == self._active_view_id:
                button.props("flat dense round color=primary")
            else:
                button.props("flat dense round")
            button.update()
