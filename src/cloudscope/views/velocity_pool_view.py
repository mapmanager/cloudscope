"""CloudScope view that displays the AcqImageList velocity pool.

This view wires the backend ``AcqImageList.velocity_analysis_pool`` DataFrame to
the reusable ``nicewidgets.nicepool.NicePool`` widget. It stays thin: acqstore
owns the pool data, nicewidgets owns widget internals, and this view only
refreshes from app state and publishes selection intents when rows are picked.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
from nicegui import ui

from cloudscope.event_bus import EventBus
from cloudscope.events.selection import SelectFileIntent
from cloudscope.events.velocity_pool import VelocityPoolChanged
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from nicewidgets.nicepool import NicePool, NicePoolConfig


class VelocityPoolView(BaseView):
    """Display and select rows from ``velocity_analysis_pool``.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Home-page state containing the current ``AcqImageList``.
        table_font_size_px: Table font size in pixels.
        initially_visible: Whether the view starts visible.
    """

    view_id = ViewId.VELOCITY_POOL
    disable_when_busy = False

    def __init__(
        self,
        event_bus: EventBus,
        *,
        app_state: Any | None = None,
        table_font_size_px: int = 12,
        initially_visible: bool = True,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._table_font_size_px = int(table_font_size_px)
        self._pool_widget: NicePool | None = None

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the velocity-pool UI.

        Args:
            parent: Optional NiceGUI parent element.

        Returns:
            Root NiceGUI element.
        """
        self._pool_widget = NicePool(
            self._pool_dataframe_from_state(),
            config=NicePoolConfig(
                unique_row_id_col="pool_row_id",
                table_font_size_px=self._table_font_size_px,
                show_table_widget=False,
                enable_config_persistence=False,
            ),
            on_row_selected=self._on_row_selected,
        )
        self.root = self._pool_widget.build(parent=parent)
        self.after_build()
        return self.root

    def subscribe_events(self) -> None:
        """Subscribe to velocity-pool changes while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(VelocityPoolChanged, self._on_velocity_pool_changed))

    def refresh_from_state(self) -> None:
        """Refresh the widget from the current backend pool DataFrame.

        Returns:
            None.
        """
        if self._pool_widget is None:
            return
        self._pool_widget.set_dataframe(self._pool_dataframe_from_state())

    def _on_velocity_pool_changed(self, event: VelocityPoolChanged) -> None:
        """Refresh after the backend velocity pool changes.

        Args:
            event: Pool-change state event.

        Returns:
            None.
        """
        _ = event
        self.refresh_from_state()

    def _on_row_selected(self, _row_id: str, row: dict[str, Any]) -> None:
        """Publish primary-selection intent for the selected pool row.

        Args:
            _row_id: Canonical pool row id, unused because row data carries the
                CloudScope selection fields.
            row: Selected row dictionary.

        Returns:
            None.
        """
        file_id = row.get("path")
        channel = row.get("channel")
        roi_id = row.get("roi_id")
        if file_id is None:
            return
        self.event_bus.publish(
            SelectFileIntent(
                file_id=str(file_id),
                channel=None if channel is None else int(channel),
                roi_id=None if roi_id is None else int(roi_id),
            )
        )

    def _pool_dataframe_from_state(self) -> pd.DataFrame:
        acq_image_list = getattr(self.app_state, "acq_image_list", None)
        if acq_image_list is None:
            return pd.DataFrame(columns=["pool_row_id", "pool_row", "path", "channel", "roi_id"])
        pool = getattr(acq_image_list, "velocity_analysis_pool", None)
        if pool is None:
            return pd.DataFrame(columns=["pool_row_id", "pool_row", "path", "channel", "roi_id"])
        return pool.get_dataframe()
