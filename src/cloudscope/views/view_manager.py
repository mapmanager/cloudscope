"""View visibility manager for CloudScope."""

from __future__ import annotations

from collections.abc import Iterable

from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId


class ViewManager:
    """Registry and visibility manager for built views."""

    def __init__(self) -> None:
        """Initialize an empty manager."""
        self._views: dict[ViewId, BaseView] = {}

    def register(self, view: BaseView) -> None:
        """Register one view by its canonical ``view_id``.

        Args:
            view: Built or unbuilt view instance.

        Returns:
            None.

        Raises:
            ValueError: If another view already uses the same id.
        """
        if view.view_id in self._views:
            raise ValueError(f"Duplicate view_id: {view.view_id}")
        self._views[view.view_id] = view

    def get(self, view_id: ViewId) -> BaseView:
        """Return a registered view.

        Args:
            view_id: View identifier.

        Returns:
            Registered view.

        Raises:
            KeyError: If the view id is unknown.
        """
        return self._views[view_id]

    def set_visible(self, view_id: ViewId, visible: bool) -> None:
        """Set visibility for one registered view.

        Args:
            view_id: View identifier.
            visible: Desired visibility.

        Returns:
            None.
        """
        self.get(view_id).set_visible(visible)

    def show(self, view_id: ViewId) -> None:
        """Show one registered view.

        Args:
            view_id: View identifier.

        Returns:
            None.
        """
        self.set_visible(view_id, True)

    def hide(self, view_id: ViewId) -> None:
        """Hide one registered view.

        Args:
            view_id: View identifier.

        Returns:
            None.
        """
        self.set_visible(view_id, False)

    def is_visible(self, view_id: ViewId) -> bool:
        """Return visibility for one registered view.

        Args:
            view_id: View identifier.

        Returns:
            True if the view is visible.
        """
        return self.get(view_id).is_visible

    def show_only(self, active_view_id: ViewId | None, candidate_view_ids: Iterable[ViewId]) -> None:
        """Show only one candidate view, or hide all candidates.

        Args:
            active_view_id: Candidate to show. If None, all candidates are hidden.
            candidate_view_ids: View ids controlled as a group.

        Returns:
            None.
        """
        candidates = tuple(candidate_view_ids)
        if active_view_id is not None and active_view_id not in candidates:
            raise ValueError(f"active_view_id {active_view_id!r} is not in candidates")
        for view_id in candidates:
            self.set_visible(view_id, active_view_id == view_id)

    def view_ids(self) -> tuple[ViewId, ...]:
        """Return registered view ids.

        Returns:
            Registered view ids in insertion order.
        """
        return tuple(self._views)
