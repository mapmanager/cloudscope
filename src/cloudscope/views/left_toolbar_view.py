"""Left-side toolbar for showing one optional panel view at a time."""

from __future__ import annotations

from dataclasses import dataclass

from nicegui import ui

from cloudscope.event_bus import EventBus
from cloudscope.views.base_view import BaseView
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
    LeftToolbarTab(ViewId.APP_CONFIG, "Config", "settings"),
)


class LeftToolbarView(BaseView):
    """Always-visible vertical toolbar controlling left panel views.

    Clicking an inactive tab shows the associated panel. Clicking the active tab
    hides all left-panel views and returns to the no-active-tab state.

    Args:
        event_bus: Page-scoped event bus.
        view_manager: Manager containing the controlled panel views.
        left_panel_root: Root container for the panel stack beside the toolbar.
    """

    view_id = ViewId.LEFT_TOOLBAR

    def __init__(
        self,
        *,
        event_bus: EventBus,
        view_manager: ViewManager,
        left_panel_root: ui.element,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=None, initially_visible=True)
        self._view_manager = view_manager
        self._left_panel_root = left_panel_root
        self._active_view_id: ViewId | None = None
        self._buttons: dict[ViewId, ui.button] = {}

    @property
    def active_view_id(self) -> ViewId | None:
        """Return the currently active left-panel view id.

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
        """Build the vertical toolbar.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for this view.
        """
        if parent is None:
            with ui.column().classes("h-full items-center gap-1 p-1 bg-gray-100 dark:bg-gray-900") as self.root:
                self._build_buttons()
        else:
            with parent:
                with ui.column().classes("h-full items-center gap-1 p-1 bg-gray-100 dark:bg-gray-900") as self.root:
                    self._build_buttons()
        self.after_build()
        self._apply_active_view(None)
        return self.root

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
        """Apply active panel state to views and panel container.

        Args:
            view_id: Panel view to show, or None to hide all panels.

        Returns:
            None.
        """
        self._active_view_id = view_id
        self._view_manager.show_only(view_id, self.panel_view_ids)
        self._left_panel_root.visible = view_id is not None
        self._left_panel_root.update()
        self._refresh_button_state()

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
