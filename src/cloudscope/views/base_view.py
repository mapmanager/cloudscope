"""Base lifecycle class for CloudScope NiceGUI views."""

from __future__ import annotations

from typing import Any, ClassVar

from nicegui import ui

from cloudscope.event_bus import EventBus, EventSubscription
from cloudscope.events import (
    AppBusyChanged,
    ChannelSelectionChanged,
    FileSelectionChanged,
    RoiSelectionChanged,
)
from cloudscope.state import PrimarySelection
from cloudscope.views.view_ids import ViewId


class BaseView:
    """Base class for views with lifecycle, busy, and selection state.

    Views are built once, kept in memory, and then shown/hidden repeatedly.
    Visible views subscribe to events and refresh from app state. Hidden views
    unsubscribe from events and do not consume event traffic.

    Every visible ``BaseView`` tracks the current primary selection from
    ``FileSelectionChanged``, ``ChannelSelectionChanged``, and
    ``RoiSelectionChanged``. Derived views can use ``current_selection`` and
    ``current_acq_image`` and override ``on_primary_selection_changed`` when they
    need to redraw after a selection change.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional page/controller state object used by
            ``refresh_from_state`` implementations.
        initially_visible: Whether the view should start visible.
    """

    view_id: ClassVar[ViewId]
    disable_when_busy: ClassVar[bool] = True

    def __init__(
        self,
        event_bus: EventBus,
        app_state: Any | None = None,
        *,
        initially_visible: bool = True,
    ) -> None:
        self.event_bus = event_bus
        self.app_state = app_state
        self._visible = bool(initially_visible)
        self._built = False
        self.root: ui.element | None = None
        self._subscriptions: list[EventSubscription] = []
        self.current_selection = PrimarySelection()
        self.current_acq_image: Any | None = None

    @property
    def is_visible(self) -> bool:
        """Return whether this view is currently visible.

        Returns:
            True when the view is visible.
        """
        return self._visible

    @property
    def is_enabled(self) -> bool:
        """Return whether this view is currently enabled.

        Returns:
            True when the root element is enabled or the view has not been built.
        """
        if self.root is None:
            return True
        return bool(getattr(self.root, "enabled", True))

    @property
    def is_built(self) -> bool:
        """Return whether ``build`` has completed.

        Returns:
            True after ``after_build`` has run.
        """
        return self._built

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the view once.

        Args:
            parent: Optional NiceGUI parent.

        Returns:
            Root element for the view.

        Raises:
            NotImplementedError: Always, unless overridden by a subclass.
        """
        raise NotImplementedError

    def after_build(self) -> None:
        """Finalize view lifecycle after subclass UI creation.

        Returns:
            None.

        Raises:
            RuntimeError: If subclass ``build`` did not set ``self.root``.
        """
        if self.root is None:
            raise RuntimeError(f"{self.__class__.__name__}.build() did not set self.root")
        self._built = True
        self._apply_visible(self._visible)
        if self._visible:
            self.on_show()
        else:
            self.on_hide()

    def set_visible(self, visible: bool) -> None:
        """Show or hide this view.

        Args:
            visible: Desired visibility.

        Returns:
            None.
        """
        visible = bool(visible)
        if self._visible == visible:
            return
        self._visible = visible
        self._apply_visible(visible)
        if visible:
            self.on_show()
        else:
            self.on_hide()

    def show(self) -> None:
        """Show this view.

        Returns:
            None.
        """
        self.set_visible(True)

    def hide(self) -> None:
        """Hide this view.

        Returns:
            None.
        """
        self.set_visible(False)

    def on_show(self) -> None:
        """Handle transition to visible state.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(AppBusyChanged, self._on_app_busy_changed))
        self.add_subscription(self.event_bus.subscribe(FileSelectionChanged, self._on_file_selection_changed))
        self.add_subscription(self.event_bus.subscribe(ChannelSelectionChanged, self._on_channel_selection_changed))
        self.add_subscription(self.event_bus.subscribe(RoiSelectionChanged, self._on_roi_selection_changed))
        self._refresh_primary_selection_from_state()
        self.subscribe_events()
        self.refresh_from_state()

    def on_hide(self) -> None:
        """Handle transition to hidden state.

        Returns:
            None.
        """
        self.unsubscribe_events()

    def subscribe_events(self) -> None:
        """Subscribe to events needed while visible.

        Subclasses override this and call ``add_subscription`` for each
        subscription. Selection and busy-state events are handled by ``BaseView``
        and should not be re-subscribed by derived classes.

        Returns:
            None.
        """

    def unsubscribe_events(self) -> None:
        """Unsubscribe from all tracked event subscriptions.

        Returns:
            None.
        """
        for subscription in tuple(self._subscriptions):
            subscription.unsubscribe()
        self._subscriptions.clear()

    def add_subscription(self, subscription: EventSubscription) -> None:
        """Track one event subscription for lifecycle cleanup.

        Args:
            subscription: Subscription handle returned by ``EventBus.subscribe``.

        Returns:
            None.
        """
        self._subscriptions.append(subscription)

    def refresh_from_state(self) -> None:
        """Refresh this view from current app state.

        Subclasses override when they can rebuild themselves from ``app_state``.
        ``BaseView`` already refreshes ``current_selection`` before this method
        is called during ``on_show``.

        Returns:
            None.
        """

    def on_primary_selection_changed(self) -> None:
        """Handle a primary selection change.

        Called after ``current_selection`` and ``current_acq_image`` are updated.
        Derived views override when they need to refresh selection-dependent UI.

        Returns:
            None.
        """

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable this view's root element.

        Args:
            enabled: Desired enabled state.

        Returns:
            None.
        """
        if self.root is None:
            return
        self.root.enabled = bool(enabled)
        self.root.update()

    def handle_app_busy_changed(self, event: AppBusyChanged) -> None:
        """Handle app busy state.

        The default behavior disables the entire root element while a task is
        running. Views with custom busy behavior can override this method.

        Args:
            event: App busy state event.

        Returns:
            None.
        """
        if self.disable_when_busy:
            self.set_enabled(not event.is_busy)

    def _on_app_busy_changed(self, event: AppBusyChanged) -> None:
        """Dispatch app busy events to the overridable handler.

        Args:
            event: App busy state event.

        Returns:
            None.
        """
        self.handle_app_busy_changed(event)

    def _on_file_selection_changed(self, event: FileSelectionChanged) -> None:
        """Update cached primary selection from a file-selection state event.

        Args:
            event: File selection state event.

        Returns:
            None.
        """
        self.current_selection = PrimarySelection(
            file_id=event.file_id,
            channel=event.channel,
            roi_id=event.roi_id,
        )
        self.current_acq_image = event.acq_image
        self.on_primary_selection_changed()

    def _on_channel_selection_changed(self, event: ChannelSelectionChanged) -> None:
        """Update cached channel from a channel-selection state event.

        Args:
            event: Channel selection state event.

        Returns:
            None.
        """
        self.current_selection.channel = event.channel
        self.on_primary_selection_changed()

    def _on_roi_selection_changed(self, event: RoiSelectionChanged) -> None:
        """Update cached ROI from an ROI-selection state event.

        Args:
            event: ROI selection state event.

        Returns:
            None.
        """
        self.current_selection.roi_id = event.roi_id
        self.on_primary_selection_changed()

    def _refresh_primary_selection_from_state(self) -> None:
        """Refresh cached selection from ``app_state`` when available.

        Returns:
            None.
        """
        if self.app_state is None:
            return
        selection = getattr(self.app_state, "selection", None)
        if selection is None:
            return
        self.current_selection = PrimarySelection(
            file_id=getattr(selection, "file_id", None),
            channel=getattr(selection, "channel", None),
            roi_id=getattr(selection, "roi_id", None),
        )
        acq_image = None
        acq_image_list = getattr(self.app_state, "acq_image_list", None)
        if acq_image_list is not None and self.current_selection.file_id is not None:
            get_file_by_id = getattr(acq_image_list, "get_file_by_id", None)
            if callable(get_file_by_id):
                acq_image = get_file_by_id(self.current_selection.file_id)
        self.current_acq_image = acq_image
        self.on_primary_selection_changed()

    def _apply_visible(self, visible: bool) -> None:
        """Apply visibility to the root UI element.

        Args:
            visible: Desired root visibility.

        Returns:
            None.
        """
        if self.root is None:
            return
        self.root.visible = visible
        self.root.update()
