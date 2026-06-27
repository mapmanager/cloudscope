"""Client-safe updates for VelocityPoolView."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
from nicegui import ui

from acqstore.analysis_pool.base_analysis_pool import AnalysisPool
from acqstore.analysis_pool.velocity_analysis_pool import VelocityAnalysisPool
from cloudscope.event_bus import EventBus
from cloudscope.events.selection import SelectFileIntent
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.velocity_pool import VelocityPoolChanged
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.view_ids import ViewId
from cloudscope.views.velocity_pool_plot_config import VELOCITY_POOL_INITIAL_PLOT_CONFIG
from nicewidgets.nicepool import NicePool, NicePoolConfig

logger = get_logger(__name__)


class VelocityPoolView(BaseView):
    """Display and select rows from ``velocity_analysis_pool``.

    Args:
        event_bus: Page-scoped event bus.
        app_state: Home-page state containing the current ``AcqImageList``.
        table_font_size_px: Table font size in pixels.
        initially_visible: Whether the view starts visible.
        dark_mode: Initial Plotly layout theme for pool plots.
        dark_mode_provider: Optional callable returning the current application
            dark-mode state when the view is shown after missing events.
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
        dark_mode: bool = False,
        dark_mode_provider: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(event_bus=event_bus, app_state=app_state, initially_visible=initially_visible)
        self._table_font_size_px = int(table_font_size_px)
        self._dark_mode = bool(dark_mode)
        self._dark_mode_provider = dark_mode_provider
        self._pool_widget: NicePool | None = None
        self._client: Any | None = None
        self._disposed = False
        self._skip_refresh_from_state_once = False

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the velocity-pool UI.

        Args:
            parent: Optional NiceGUI parent element.

        Returns:
            Root NiceGUI element.
        """
        self._client = ui.context.client
        self._disposed = False
        self._pool_widget = NicePool(
            self._pool_dataframe_from_state(),
            config=NicePoolConfig(
                unique_row_id_col="pool_row_id",
                table_font_size_px=self._table_font_size_px,
                initial_plot_config=VELOCITY_POOL_INITIAL_PLOT_CONFIG,
                show_table_widget=False,
                enable_config_persistence=False,
                dark_mode=self._dark_mode,
            ),
            on_row_selected=self._on_row_selected,
        )
        self.root = self._pool_widget.build(parent=parent)
        self._skip_refresh_from_state_once = True
        self.after_build()
        return self.root

    def relayout_plots(self) -> None:
        """Rebuild pool plots after the parent pane resizes.

        Returns:
            None.
        """
        if self._disposed or self._pool_widget is None:
            return
        self._pool_widget.relayout_plots()

    def subscribe_events(self) -> None:
        """Subscribe to velocity-pool changes while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(VelocityPoolChanged, self._on_velocity_pool_changed))
        self.add_subscription(self.event_bus.subscribe(ThemeChanged, self._on_theme_changed))

    def on_show(self) -> None:
        """Handle transition to visible state.

        Returns:
            None.
        """
        self._disposed = False
        super().on_show()

    def on_hide(self) -> None:
        """Unsubscribe and mark this view inactive for cross-client callbacks.

        Returns:
            None.
        """
        self._disposed = True
        super().on_hide()

    def on_primary_selection_changed(self) -> None:
        """Highlight the pool row matching the shared primary selection.

        Returns:
            None.
        """
        self._run_ui(self._sync_plot_selection_from_primary)

    def _sync_plot_selection_from_primary(self) -> None:
        """Apply cross-page primary selection to the NicePool plot highlight.

        Returns:
            None.
        """
        if self._disposed or self._pool_widget is None:
            return
        file_id = self.current_selection.file_id
        channel = self.current_selection.channel
        roi_id = self.current_selection.roi_id
        if file_id is None or channel is None or roi_id is None:
            return
        row_id = AnalysisPool.build_pool_row_id(
            file_id,
            channel=int(channel),
            roi_id=int(roi_id),
        )
        self._pool_widget.select_points_by_row_id(row_id)

    def refresh_from_state(self) -> None:
        """Refresh the widget from the current backend pool DataFrame.

        Returns:
            None.
        """
        if self._skip_refresh_from_state_once:
            self._skip_refresh_from_state_once = False
            return
        self._run_ui(self._refresh_from_state_impl)

    def _on_theme_changed(self, event: ThemeChanged) -> None:
        """Apply an application theme change to the pool plots.

        Args:
            event: Theme state event published by the page header.

        Returns:
            None.
        """
        self._run_ui(lambda: self._apply_dark_mode(event.dark_mode))

    def _sync_theme_from_provider(self) -> None:
        """Apply the current application theme when a provider is available.

        Returns:
            None.
        """
        if self._dark_mode_provider is None:
            return
        self._apply_dark_mode(bool(self._dark_mode_provider()))

    def _apply_dark_mode(self, enabled: bool) -> None:
        """Push dark-mode state into the embedded NicePool widget.

        Args:
            enabled: Whether dark mode is enabled.

        Returns:
            None.
        """
        if self._disposed or self._pool_widget is None:
            return
        self._dark_mode = bool(enabled)
        self._pool_widget.set_dark_mode(self._dark_mode)

    def _run_ui(self, fn: Callable[[], None]) -> None:
        """Run UI updates; remarshal via ``Client.safe_invoke`` when needed.

        Args:
            fn: UI update callable.

        Returns:
            None.
        """
        if self._disposed:
            return
        try:
            fn()
        except RuntimeError as exc:
            message = str(exc).lower()
            if 'slot' not in message and 'client' not in message:
                raise
            if self._client is None:
                logger.warning('Velocity pool UI update dropped (no client): %s', exc)
                return
            self._client.safe_invoke(fn)

    def _refresh_from_state_impl(self) -> None:
        """Refresh NicePool from runtime state on the owning client.

        Returns:
            None.
        """
        if self._disposed or self._pool_widget is None:
            return
        self._sync_theme_from_provider()
        self._pool_widget.set_dataframe(self._pool_dataframe_from_state())
        self._sync_plot_selection_from_primary()

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
            return _empty_velocity_pool_dataframe()
        pool = getattr(acq_image_list, "velocity_analysis_pool", None)
        if pool is None:
            return _empty_velocity_pool_dataframe()
        return pool.get_dataframe()


def _empty_velocity_pool_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=VelocityAnalysisPool.pool_column_names())
