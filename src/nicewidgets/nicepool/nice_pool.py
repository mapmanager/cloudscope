"""Public NicePool wrapper around the faithful plot-pool controller."""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd
from nicegui import ui

from nicewidgets.nicepool.config import NicePoolConfig, resolve_pre_filter_columns
from nicewidgets.nicepool.plot_pool_controller import PlotPoolConfig, PlotPoolController


class NicePool(PlotPoolController):
    """General-purpose DataFrame plotting and selection widget.

    ``NicePool`` preserves the original plot-pool GUI behavior while exposing a
    small stable API for CloudScope and scripts.

    Args:
        df: Source DataFrame.
        config: Optional NicePool configuration.
        on_row_selected: Optional callback invoked when a table row is selected.
        on_refresh_requested: Optional callback invoked by the refresh button.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        config: NicePoolConfig | None = None,
        on_row_selected: Callable[[str, dict[str, object]], None] | None = None,
        on_refresh_requested: Callable[[], pd.DataFrame] | None = None,
    ) -> None:
        cfg = config if config is not None else NicePoolConfig()
        pre_filter_columns = resolve_pre_filter_columns(
            [str(column) for column in df.columns],
            explicit_columns=cfg.pre_filter_columns,
            auto_columns=cfg.auto_pre_filter_columns,
        )
        table_callback = on_row_selected if on_row_selected is not None else cfg.on_table_row_selected
        refresh_callback = on_refresh_requested if on_refresh_requested is not None else cfg.on_refresh_requested
        controller_config = PlotPoolConfig(
            pre_filter_columns=list(pre_filter_columns),
            unique_row_id_col=cfg.unique_row_id_col,
            db_type=cfg.db_type,
            app_name=cfg.app_name,
            config_path=cfg.config_path,
            plot_state=cfg.plot_state,
            on_table_row_selected=table_callback,
            on_refresh_requested=refresh_callback,
            show_save_button=cfg.show_save_button,
            show_selection_feedback=cfg.show_selection_feedback,
            show_table_widget=cfg.show_table_widget,
            enable_config_persistence=cfg.enable_config_persistence,
            dark_mode=cfg.dark_mode,
        )
        super().__init__(df, config=controller_config)
        self.nicepool_config = cfg
        self.pre_filter_columns = tuple(pre_filter_columns)

    def build(self, parent: ui.element | None = None, *, container: ui.element | None = None) -> ui.element:
        """Build the NicePool UI.

        Args:
            parent: Optional NiceGUI parent element.
            container: Optional legacy container argument.

        Returns:
            Root NiceGUI element containing the widget.
        """
        target = container if container is not None else parent
        if target is None:
            root = ui.column().classes("w-full h-full")
        else:
            with target:
                root = ui.column().classes("w-full h-full")
        super().build(container=root)
        return root

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Replace the source DataFrame and refresh the widget.

        Args:
            df: New source DataFrame.
        """
        self.update_df(df)

    def set_dark_mode(self, enabled: bool) -> None:
        """Set the Plotly layout theme from a dark-mode flag.

        Args:
            enabled: Whether dark mode is enabled.

        Returns:
            None.
        """
        super().set_dark_mode(enabled)
