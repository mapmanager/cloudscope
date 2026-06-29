"""Client-safe updates for the right-panel analysis pool view."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
from nicegui import ui

from acqstore.analysis_pool.base_analysis_pool import AnalysisPool
from acqstore.analysis_pool.sum_intensity_analysis_pool import SumIntensityAnalysisPool
from acqstore.analysis_pool.velocity_analysis_pool import VelocityAnalysisPool
from cloudscope.event_bus import EventBus
from cloudscope.events.selection import SelectFileIntent
from cloudscope.events.sum_intensity_pool import SumIntensityPoolChanged
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.velocity_pool import VelocityPoolChanged
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.sum_intensity_pool_plot_config import SUM_INTENSITY_POOL_INITIAL_PLOT_CONFIG
from cloudscope.views.view_ids import ViewId
from cloudscope.views.velocity_pool_plot_config import VELOCITY_POOL_INITIAL_PLOT_CONFIG
from nicewidgets.nicepool import NicePool, NicePoolConfig

logger = get_logger(__name__)

_TAB_VELOCITY = "velocity"
_TAB_PEAKS = "peaks"


class VelocityPoolView(BaseView):
    """Display and select rows from collection-level analysis pools.

    The view hosts two ``NicePool`` tabs: velocity summaries and sum-intensity
    peak events from ``AcqImageList.velocity_analysis_pool`` and
    ``AcqImageList.sum_intensity_analysis_pool``.

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
        self._velocity_pool: NicePool | None = None
        self._peaks_pool: NicePool | None = None
        self._tabs: ui.tabs | None = None
        self._velocity_tab: ui.tab | None = None
        self._peaks_tab: ui.tab | None = None
        self._client: Any | None = None
        self._disposed = False
        self._skip_refresh_from_state_once = False

    def build(self, parent: ui.element | None = None) -> ui.element:
        """Build the tabbed analysis-pool UI.

        Args:
            parent: Optional NiceGUI parent element.

        Returns:
            Root NiceGUI element.
        """
        self._client = ui.context.client
        self._disposed = False
        pool_config = NicePoolConfig(
            unique_row_id_col="pool_row_id",
            table_font_size_px=self._table_font_size_px,
            show_table_widget=False,
            enable_config_persistence=False,
            dark_mode=self._dark_mode,
        )
        if parent is None:
            self.root = ui.column().classes("w-full h-full min-h-0 flex flex-col")
        else:
            with parent:
                self.root = ui.column().classes("w-full h-full min-h-0 flex flex-col")

        assert self.root is not None
        with self.root:
            with ui.tabs().classes("w-full shrink-0") as tabs:
                self._velocity_tab = ui.tab(_TAB_VELOCITY, label="Velocity")
                self._peaks_tab = ui.tab(_TAB_PEAKS, label="Peaks")
            self._tabs = tabs
            assert self._velocity_tab is not None
            with ui.tab_panels(tabs, value=self._velocity_tab).classes("w-full flex-1 min-h-0"):
                with ui.tab_panel(self._velocity_tab):
                    self._velocity_pool = NicePool(
                        self._velocity_dataframe_from_state(),
                        config=NicePoolConfig(
                            unique_row_id_col=pool_config.unique_row_id_col,
                            table_font_size_px=pool_config.table_font_size_px,
                            initial_plot_config=VELOCITY_POOL_INITIAL_PLOT_CONFIG,
                            show_table_widget=pool_config.show_table_widget,
                            enable_config_persistence=pool_config.enable_config_persistence,
                            dark_mode=pool_config.dark_mode,
                        ),
                        on_row_selected=self._on_row_selected,
                    )
                    self._velocity_pool.build()
                assert self._peaks_tab is not None
                with ui.tab_panel(self._peaks_tab):
                    self._peaks_pool = NicePool(
                        self._peaks_dataframe_from_state(),
                        config=NicePoolConfig(
                            unique_row_id_col=pool_config.unique_row_id_col,
                            table_font_size_px=pool_config.table_font_size_px,
                            initial_plot_config=SUM_INTENSITY_POOL_INITIAL_PLOT_CONFIG,
                            show_table_widget=pool_config.show_table_widget,
                            enable_config_persistence=pool_config.enable_config_persistence,
                            dark_mode=pool_config.dark_mode,
                        ),
                        on_row_selected=self._on_row_selected,
                    )
                    self._peaks_pool.build()

            tabs.on("update:model-value", lambda _event=None: self._run_ui(self._relayout_active_tab))

        self._skip_refresh_from_state_once = True
        self.after_build()
        return self.root

    def relayout_plots(self) -> None:
        """Rebuild pool plots after the parent pane resizes.

        Returns:
            None.
        """
        self._run_ui(self._relayout_active_tab)

    def subscribe_events(self) -> None:
        """Subscribe to analysis-pool changes while visible.

        Returns:
            None.
        """
        self.add_subscription(self.event_bus.subscribe(VelocityPoolChanged, self._on_pool_changed))
        self.add_subscription(self.event_bus.subscribe(SumIntensityPoolChanged, self._on_pool_changed))
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
        """Highlight pool rows matching the shared primary selection.

        Returns:
            None.
        """
        self._run_ui(self._sync_plot_selection_from_primary)

    def _sync_plot_selection_from_primary(self) -> None:
        """Apply cross-page primary selection to both pool plot highlights.

        Returns:
            None.
        """
        if self._disposed:
            return
        file_id = self.current_selection.file_id
        channel = self.current_selection.channel
        roi_id = self.current_selection.roi_id
        if file_id is None or channel is None or roi_id is None:
            return

        if self._velocity_pool is not None:
            row_id = AnalysisPool.build_pool_row_id(
                file_id,
                channel=int(channel),
                roi_id=int(roi_id),
            )
            self._velocity_pool.select_points_by_row_id(row_id)

        if self._peaks_pool is not None:
            pool = self._sum_intensity_pool_from_state()
            if pool is None:
                return
            row_ids = pool.row_ids_for_selection(
                file_id,
                channel=int(channel),
                roi_id=int(roi_id),
            )
            if row_ids:
                self._peaks_pool.select_points_by_row_ids(row_ids)

    def refresh_from_state(self) -> None:
        """Refresh both pool widgets from the current backend DataFrames.

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
        """Push dark-mode state into both embedded NicePool widgets.

        Args:
            enabled: Whether dark mode is enabled.

        Returns:
            None.
        """
        if self._disposed:
            return
        self._dark_mode = bool(enabled)
        for pool in (self._velocity_pool, self._peaks_pool):
            if pool is not None:
                pool.set_dark_mode(self._dark_mode)

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
            if "slot" not in message and "client" not in message:
                raise
            if self._client is None:
                logger.warning("Analysis pool UI update dropped (no client): %s", exc)
                return
            self._client.safe_invoke(fn)

    def _refresh_from_state_impl(self) -> None:
        """Refresh both NicePool widgets from runtime state on the owning client.

        Returns:
            None.
        """
        if self._disposed:
            return
        self._sync_theme_from_provider()
        if self._velocity_pool is not None:
            self._velocity_pool.set_dataframe(self._velocity_dataframe_from_state())
        if self._peaks_pool is not None:
            self._peaks_pool.set_dataframe(self._peaks_dataframe_from_state())
        self._sync_plot_selection_from_primary()

    def _on_pool_changed(self, event: VelocityPoolChanged | SumIntensityPoolChanged) -> None:
        """Refresh after either backend analysis pool changes.

        Args:
            event: Pool-change state event.

        Returns:
            None.
        """
        _ = event
        self.refresh_from_state()

    def _relayout_active_tab(self) -> None:
        """Relayout the NicePool widget for the currently selected tab.

        Returns:
            None.
        """
        if self._disposed:
            return
        pool = self._active_pool_widget()
        if pool is not None:
            pool.relayout_plots()

    def _active_pool_widget(self) -> NicePool | None:
        """Return the NicePool widget for the active tab.

        Returns:
            Active-tab NicePool instance, or None when tabs are unavailable.
        """
        if self._tabs is None:
            return self._velocity_pool
        active = self._tabs.value
        if active == _TAB_PEAKS:
            return self._peaks_pool
        return self._velocity_pool

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

    def _velocity_dataframe_from_state(self) -> pd.DataFrame:
        acq_image_list = getattr(self.app_state, "acq_image_list", None)
        if acq_image_list is None:
            return _empty_velocity_pool_dataframe()
        pool = getattr(acq_image_list, "velocity_analysis_pool", None)
        if pool is None:
            return _empty_velocity_pool_dataframe()
        return pool.get_dataframe()

    def _peaks_dataframe_from_state(self) -> pd.DataFrame:
        acq_image_list = getattr(self.app_state, "acq_image_list", None)
        if acq_image_list is None:
            return _empty_sum_intensity_pool_dataframe()
        pool = getattr(acq_image_list, "sum_intensity_analysis_pool", None)
        if pool is None:
            return _empty_sum_intensity_pool_dataframe()
        return pool.get_dataframe()

    def _sum_intensity_pool_from_state(self) -> SumIntensityAnalysisPool | None:
        acq_image_list = getattr(self.app_state, "acq_image_list", None)
        if acq_image_list is None:
            return None
        pool = getattr(acq_image_list, "sum_intensity_analysis_pool", None)
        if pool is None:
            return None
        if not isinstance(pool, SumIntensityAnalysisPool):
            return None
        return pool


def _empty_velocity_pool_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=VelocityAnalysisPool.pool_column_names())


def _empty_sum_intensity_pool_dataframe() -> pd.DataFrame:
    return pd.DataFrame(columns=SumIntensityAnalysisPool.pool_column_names())
