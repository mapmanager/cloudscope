"""Client-safe updates for the right-panel analysis pool view."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pandas as pd
from nicegui import ui

from acqstore.analysis_pool.base_analysis_pool import AnalysisPool
from acqstore.analysis_pool.sum_intensity_analysis_pool import SumIntensityAnalysisPool
from acqstore.analysis_pool.velocity_analysis_pool import VelocityAnalysisPool
from cloudscope.blinded_display import (
    PoolSelectionIdentity,
    mask_pool_dataframe,
)
from cloudscope.event_bus import EventBus
from cloudscope.events.app_config import BlindedAnalysisModeChanged
from cloudscope.events.selection import (
    SELECTION_SOURCE_VELOCITY_POOL,
    SelectFileIntent,
)
from cloudscope.events.sum_intensity_pool import SumIntensityPoolChanged
from cloudscope.events.theme import ThemeChanged
from cloudscope.events.velocity_pool import VelocityPoolChanged
from cloudscope.session_state import (
    VIEW_SESSION_SCHEMA_VERSION,
    require_keys,
    require_schema_version,
)
from cloudscope.utils.logging import get_logger
from cloudscope.views.base_view import BaseView
from cloudscope.views.sum_intensity_pool_plot_config import SUM_INTENSITY_POOL_INITIAL_PLOT_CONFIG
from cloudscope.views.view_ids import ViewId
from cloudscope.views.velocity_pool_plot_config import VELOCITY_POOL_INITIAL_PLOT_CONFIG
from nicewidgets.nicepool import NicePool, NicePoolConfig

logger = get_logger(__name__)

_TAB_VELOCITY = "velocity"
_TAB_PEAKS = "peaks"


@dataclass(slots=True)
class VelocityPoolViewState:
    """Serializable reconnect session state for :class:`VelocityPoolView`.

    Args:
        active_tab: Selected tab name (``"velocity"`` or ``"peaks"``).
        schema_version: Session blob schema version.
    """

    active_tab: str = _TAB_VELOCITY
    schema_version: int = VIEW_SESSION_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable session blob.

        Returns:
            Mapping with schema version and the active tab name.
        """
        active_tab = self.active_tab if self.active_tab in (_TAB_VELOCITY, _TAB_PEAKS) else _TAB_VELOCITY
        return {
            'schema_version': self.schema_version,
            'active_tab': active_tab,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VelocityPoolViewState:
        """Build state from a blob produced by :meth:`to_dict`.

        Args:
            data: Session blob from :meth:`VelocityPoolView.export_session_state`.

        Returns:
            Reconstructed :class:`VelocityPoolViewState`.

        Raises:
            KeyError: If required keys (including ``schema_version``) are absent.
            ValueError: If ``schema_version`` is unsupported.
        """
        require_schema_version(data)
        require_keys(data, 'active_tab')
        active_tab = str(data['active_tab'])
        if active_tab not in (_TAB_VELOCITY, _TAB_PEAKS):
            active_tab = _TAB_VELOCITY
        return cls(
            active_tab=active_tab,
            schema_version=int(data.get('schema_version', VIEW_SESSION_SCHEMA_VERSION)),
        )
_VELOCITY_POOL_TABS_CLASS = "velocity-pool-tabs"
_VELOCITY_POOL_TAB_PANELS_CLASS = "velocity-pool-tab-panels"
_VELOCITY_POOL_TAB_CSS_ADDED = False
_VELOCITY_POOL_TAB_CSS = """
.velocity-pool-tabs .q-tab {
    min-height: 28px;
    padding: 0 8px;
}
.velocity-pool-tab-panels .q-tab-panel {
    padding: 0;
}
"""


def _ensure_velocity_pool_tab_css() -> None:
    """Inject compact pool-tab CSS once per process.

    Returns:
        None.
    """
    global _VELOCITY_POOL_TAB_CSS_ADDED
    if _VELOCITY_POOL_TAB_CSS_ADDED:
        return
    ui.add_css(_VELOCITY_POOL_TAB_CSS)
    _VELOCITY_POOL_TAB_CSS_ADDED = True


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
        blinded_provider: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__(
            event_bus=event_bus,
            app_state=app_state,
            initially_visible=initially_visible,
            blinded_provider=blinded_provider,
        )
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
        self._velocity_display_to_selection: dict[str, PoolSelectionIdentity] = {}
        self._velocity_real_to_display_row_id: dict[str, str] = {}
        self._peaks_display_to_selection: dict[str, PoolSelectionIdentity] = {}
        self._peaks_real_to_display_row_id: dict[str, str] = {}

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
            _ensure_velocity_pool_tab_css()
            with ui.tabs().classes(
                f"w-full shrink-0 {_VELOCITY_POOL_TABS_CLASS}"
            ).props("dense align=left inline-label narrow-indicator no-caps") as tabs:
                self._velocity_tab = ui.tab(_TAB_VELOCITY, label="Velocity", icon="speed")
                self._peaks_tab = ui.tab(_TAB_PEAKS, label="Peaks", icon="functions")
            self._tabs = tabs
            assert self._velocity_tab is not None
            with ui.tab_panels(tabs, value=self._velocity_tab).classes(
                f"w-full flex-1 min-h-0 p-0 {_VELOCITY_POOL_TAB_PANELS_CLASS}"
            ):
                with ui.tab_panel(self._velocity_tab).classes("p-0 h-full min-h-0"):
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
                with ui.tab_panel(self._peaks_tab).classes("p-0 h-full min-h-0"):
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

    def export_session_state(self) -> dict[str, Any]:
        """Return a reconnect session blob capturing the active pool tab.

        Returns:
            JSON-serializable blob with the currently selected tab.
        """
        active_tab = _TAB_VELOCITY
        if self._tabs is not None and self._tabs.value in (_TAB_VELOCITY, _TAB_PEAKS):
            active_tab = str(self._tabs.value)
        return VelocityPoolViewState(active_tab=active_tab).to_dict()

    def apply_session_state(self, data: dict[str, Any]) -> None:
        """Restore the active pool tab from a reconnect session blob.

        Args:
            data: Blob produced by :meth:`export_session_state`.

        Returns:
            None.
        """
        state = VelocityPoolViewState.from_dict(data)
        if self._tabs is None:
            return
        self._tabs.set_value(state.active_tab)
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
            row_id = self._velocity_real_to_display_row_id.get(row_id, row_id)
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
                row_ids = tuple(self._peaks_real_to_display_row_id.get(row_id, row_id) for row_id in row_ids)
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

    def on_blinded_analysis_mode_changed(self, event: BlindedAnalysisModeChanged) -> None:
        """Refresh pool display DataFrames after blinded mode changes."""
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
        identity = self._selection_identity_for_display_row(_row_id)
        file_id = identity.file_id if identity is not None else row.get("path")
        channel = identity.channel if identity is not None else row.get("channel")
        roi_id = identity.roi_id if identity is not None else row.get("roi_id")
        if file_id is None:
            return
        self.event_bus.publish(
            SelectFileIntent(
                file_id=str(file_id),
                channel=None if channel is None else int(channel),
                roi_id=None if roi_id is None else int(roi_id),
                source=SELECTION_SOURCE_VELOCITY_POOL,
            )
        )

    def _velocity_dataframe_from_state(self) -> pd.DataFrame:
        acq_image_list = getattr(self.app_state, "acq_image_list", None)
        if acq_image_list is None:
            return _empty_velocity_pool_dataframe()
        pool = getattr(acq_image_list, "velocity_analysis_pool", None)
        if pool is None:
            return _empty_velocity_pool_dataframe()
        return self._display_velocity_dataframe(pool.get_dataframe())

    def _peaks_dataframe_from_state(self) -> pd.DataFrame:
        acq_image_list = getattr(self.app_state, "acq_image_list", None)
        if acq_image_list is None:
            return _empty_sum_intensity_pool_dataframe()
        pool = getattr(acq_image_list, "sum_intensity_analysis_pool", None)
        if pool is None:
            return _empty_sum_intensity_pool_dataframe()
        return self._display_peaks_dataframe(pool.get_dataframe())

    def _display_velocity_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return the velocity DataFrame in the current display mode."""
        if not self.is_blinded():
            self._velocity_display_to_selection = {}
            self._velocity_real_to_display_row_id = {}
            return df
        display = mask_pool_dataframe(df, file_label_map=self.file_label_map())
        self._velocity_display_to_selection = display.display_to_real_selection
        self._velocity_real_to_display_row_id = display.real_to_display_row_id
        return display.dataframe

    def _display_peaks_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Return the peaks DataFrame in the current display mode."""
        if not self.is_blinded():
            self._peaks_display_to_selection = {}
            self._peaks_real_to_display_row_id = {}
            return df
        display = mask_pool_dataframe(df, file_label_map=self.file_label_map())
        self._peaks_display_to_selection = display.display_to_real_selection
        self._peaks_real_to_display_row_id = display.real_to_display_row_id
        return display.dataframe

    def _selection_identity_for_display_row(self, row_id: str) -> PoolSelectionIdentity | None:
        """Return real selection identity for a possibly blinded pool row."""
        return self._velocity_display_to_selection.get(row_id) or self._peaks_display_to_selection.get(row_id)

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
