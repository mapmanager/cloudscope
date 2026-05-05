"""Base lifecycle class for CloudScope NiceGUI views."""

from __future__ import annotations

from typing import Any, ClassVar

from nicegui import ui

from cloudscope.event_bus import EventBus, EventSubscription
from cloudscope.views.view_ids import ViewId


class BaseView:
    """Base class for views with visibility and event-subscription lifecycle.

    Views are built once, kept in memory, and then shown/hidden repeatedly.
    Visible views subscribe to events and refresh from app state. Hidden views
    unsubscribe from events and do not consume event traffic.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Optional page/controller state object used by
            ``refresh_from_state`` implementations.
        initially_visible: Whether the view should start visible.
    """

    view_id: ClassVar[ViewId]

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

    @property
    def is_visible(self) -> bool:
        """Return whether this view is currently visible.

        Returns:
            True when the view is visible.
        """
        return self._visible

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
        subscription.

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

        Returns:
            None.
        """

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
