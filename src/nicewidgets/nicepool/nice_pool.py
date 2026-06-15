"""Reusable full DataFrame-driven pool widget for NiceGUI applications.

``NicePool`` is intentionally independent of CloudScope. It accepts a pandas
DataFrame, renders a left control panel, Plotly plots, optional bottom table,
and calls back with ``(row_id, row_dict)`` when the user selects a row from the
table or plot. CloudScope uses that callback to publish its own MVC intents.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd
from nicegui import ui

from nicewidgets.aggrid_common.column_def import ColumnDef
from nicewidgets.nicepool.config import NicePoolConfig, resolve_pre_filter_columns
from nicewidgets.nicepool.control_panel import NicePoolControlPanel
from nicewidgets.nicepool.dataframe_adapter import dataframe_to_rows
from nicewidgets.nicepool.dataframe_processor import DataFrameProcessor
from nicewidgets.nicepool.figure_generator import FigureGenerator
from nicewidgets.nicepool.plot_helpers import numeric_columns
from nicewidgets.nicepool.plot_state import PlotState, make_default_plot_state
from nicewidgets.nicepool.plot_summary import PlotSummary, format_plot_summary_to_str
from nicewidgets.nicepool.pre_filter_conventions import PRE_FILTER_NONE
from nicewidgets.table_widget.config import TableWidgetConfig, scaled_row_header_heights_px
from nicewidgets.table_widget.table_widget import TableWidget
from nicewidgets.utils.clipboard import copy_to_clipboard


RowSelectedCallback = Callable[[str, dict[str, Any]], None]
RefreshRequestedCallback = Callable[[], pd.DataFrame]


class NicePool:
    """General-purpose DataFrame pool widget with controls, plots, and table.

    Args:
        df: Source DataFrame. The widget keeps a copy.
        config: Optional widget configuration.
        on_row_selected: Callback invoked with row id and row dict when a row is
            selected from either the table or a plot point.
        on_refresh_requested: Optional callback invoked by future refresh UI.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        config: NicePoolConfig | None = None,
        on_row_selected: RowSelectedCallback | None = None,
        on_refresh_requested: RefreshRequestedCallback | None = None,
    ) -> None:
        self.config = config or NicePoolConfig()
        self._on_row_selected = on_row_selected
        self._on_refresh_requested = on_refresh_requested
        self._df = df.copy()
        self._pre_filter_columns = resolve_pre_filter_columns(
            tuple(self._df.columns),
            explicit_columns=self.config.pre_filter_columns,
            auto_columns=self.config.auto_pre_filter_columns,
        )
        self._data_processor = self._new_processor()
        self._figure_generator = FigureGenerator(self._data_processor, unique_row_id_col=self.config.unique_row_id_col)
        default_state = make_default_plot_state(
            [str(column) for column in self._df.columns],
            numeric_columns(self._df),
            self._pre_filter_columns,
        )
        self._plot_states: list[PlotState] = [default_state for _ in range(4)]
        self._plot_summaries: list[PlotSummary | None] = [None, None, None, None]
        self._layout = "1x1"
        self._current_plot_index = 0
        self._selected_row_ids: set[str] = set()
        self._root: ui.column | None = None
        self._summary_label: ui.label | None = None
        self._selection_label: ui.label | None = None
        self._control_panel: NicePoolControlPanel | None = None
        self._plot_container: ui.element | None = None
        self._plot_elements: list[ui.plotly] = []
        self._table: TableWidget | None = None

    @property
    def dataframe(self) -> pd.DataFrame:
        """Return a copy of the source DataFrame.

        Returns:
            DataFrame copy currently owned by the widget.
        """
        return self._df.copy()

    @property
    def pre_filter_columns(self) -> tuple[str, ...]:
        """Return active pre-filter columns.

        Returns:
            Tuple of columns rendered as filter controls.
        """
        return tuple(self._pre_filter_columns)

    def build(self, parent: ui.element | None = None) -> ui.column:
        """Build the NiceGUI UI.

        Args:
            parent: Optional parent element. When omitted, the current NiceGUI
                slot is used.

        Returns:
            Root column for the widget.
        """
        container = parent if parent is not None else ui.column().classes("w-full h-full")
        with container:
            self._root = ui.column().classes("w-full h-full min-w-0 min-h-0 gap-2")
            with self._root:
                self._summary_label = ui.label().classes("text-xs opacity-70")
                if self.config.show_selection_feedback:
                    self._selection_label = ui.label("No selection").classes("text-xs opacity-70")
                self._build_plot_area()
                if self.config.show_table_widget:
                    self._build_table_area()
        self._refresh_summary()
        return self._root

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Replace the DataFrame and refresh controls, plots, and table.

        Args:
            df: New source DataFrame.

        Returns:
            None.
        """
        self._df = df.copy()
        self._pre_filter_columns = resolve_pre_filter_columns(
            tuple(self._df.columns),
            explicit_columns=self.config.pre_filter_columns,
            auto_columns=self.config.auto_pre_filter_columns,
        )
        self._data_processor = self._new_processor()
        self._figure_generator = FigureGenerator(self._data_processor, unique_row_id_col=self.config.unique_row_id_col)
        default_state = make_default_plot_state(
            [str(column) for column in self._df.columns],
            numeric_columns(self._df),
            self._pre_filter_columns,
        )
        self._plot_states = [self._coerce_state_for_dataframe(state, default_state) for state in self._plot_states]
        if self._table is not None:
            self._table.set_data(self._filtered_rows())
        self._rebuild_controls_and_plots()
        self._refresh_summary()

    def update_df(self, df: pd.DataFrame) -> None:
        """Backward-compatible alias for :meth:`set_dataframe`.

        Args:
            df: New source DataFrame.

        Returns:
            None.
        """
        self.set_dataframe(df)

    def get_selected_row_ids(self) -> list[str]:
        """Return selected row ids known by the widget.

        Returns:
            Selected row ids.
        """
        if self._table is None:
            return sorted(self._selected_row_ids)
        table_ids = self._table.get_selected_row_ids()
        return table_ids or sorted(self._selected_row_ids)

    def select_points_by_row_id(self, row_id: str) -> None:
        """Programmatically select a row id.

        Args:
            row_id: Stable row identifier.

        Returns:
            None.
        """
        self._selected_row_ids = {str(row_id)}
        self._refresh_selection_label()

    def _build_plot_area(self) -> None:
        splitter = ui.splitter(value=self.config.left_panel_width).classes("w-full grow min-h-0")
        with splitter.before:
            self._build_control_panel()
        with splitter.after:
            self._plot_container = ui.column().classes("w-full h-full min-h-0")
            self._render_plots()

    def _build_control_panel(self) -> None:
        self._control_panel = NicePoolControlPanel(
            self._df,
            initial_state=self._plot_states[self._current_plot_index],
            pre_filter_options=self._pre_filter_options(),
            layout=self._layout,
            current_plot_index=self._current_plot_index,
            on_any_change=self._on_control_changed,
            on_layout_change=self._on_layout_changed,
            on_plot_radio_change=self._on_plot_radio_changed,
            on_apply_current_to_others=self._apply_current_to_others,
            on_replot_current=self._replot_current,
            on_reset_to_default=self._reset_to_default,
            on_copy_stats=self._copy_stats,
            on_clear_selection=self._clear_selection,
            show_save_button=self.config.show_save_button and self.config.enable_config_persistence,
            on_save_config=self._save_config if self.config.enable_config_persistence else None,
        )
        self._control_panel.build()

    def _build_table_area(self) -> None:
        table_container = ui.column().classes("w-full h-[16rem] min-h-0")
        self._table = TableWidget(
            self._build_columns(),
            self.config.unique_row_id_col,
            self._filtered_rows(),
            on_row_selected=self._on_table_row_selected,
            config=self._table_config(),
        )
        self._table.build(table_container)

    def _render_plots(self) -> None:
        if self._plot_container is None:
            return
        self._plot_container.clear()
        self._plot_elements = []
        with self._plot_container:
            with ui.grid(columns=self._grid_columns()).classes("w-full h-full gap-2"):
                for plot_index in range(self._visible_plot_count()):
                    figure = self._figure_for_plot(plot_index)
                    plot = ui.plotly(figure).classes("w-full")
                    plot.style(f"height: {self.config.plot_height_px}px")
                    plot.on("plotly_click", lambda event, index=plot_index: self._on_plotly_click(event, index))
                    self._plot_elements.append(plot)

    def _rebuild_controls_and_plots(self) -> None:
        if self._root is None:
            return
        # Rebuild the full widget body. This is intentionally wholesale for now.
        self._root.clear()
        with self._root:
            self._summary_label = ui.label().classes("text-xs opacity-70")
            if self.config.show_selection_feedback:
                self._selection_label = ui.label("No selection").classes("text-xs opacity-70")
            self._build_plot_area()
            if self.config.show_table_widget:
                self._build_table_area()
        self._refresh_summary()

    def _figure_for_plot(self, plot_index: int) -> dict:
        state = self._plot_states[plot_index]
        df_f = self._data_processor.filter_by_pre_filters(state.pre_filter)
        try:
            figure, summary = self._figure_generator.make_figure(df_f, state)
        except Exception as exc:  # pragma: no cover - defensive UI fallback
            figure = {
                "data": [],
                "layout": {
                    "title": f"Unable to render plot: {exc}",
                    "margin": {"l": 50, "r": 20, "t": 55, "b": 50},
                },
            }
            summary = PlotSummary(plot_type=state.plot_type.value, row_count=0, details={"error": str(exc)})
        self._plot_summaries[plot_index] = summary
        return figure

    def _on_control_changed(self) -> None:
        if self._control_panel is None:
            return
        self._plot_states[self._current_plot_index] = self._control_panel.read_state()
        self._render_plots()
        if self._table is not None:
            self._table.set_data(self._filtered_rows())
        self._refresh_summary()

    def _on_layout_changed(self, value: str) -> None:
        self._layout = value if value in {"1x1", "1x2", "2x1", "2x2"} else "1x1"
        self._render_plots()

    def _on_plot_radio_changed(self, event: Any) -> None:
        value = getattr(event, "value", event)
        try:
            self._current_plot_index = max(0, min(3, int(value) - 1))
        except (TypeError, ValueError):
            self._current_plot_index = 0
        self._rebuild_controls_and_plots()

    def _apply_current_to_others(self) -> None:
        state = self._plot_states[self._current_plot_index]
        self._plot_states = [PlotState.from_dict(state.to_dict()) for _ in range(4)]
        self._render_plots()

    def _replot_current(self) -> None:
        self._on_control_changed()

    def _reset_to_default(self) -> None:
        default_state = make_default_plot_state(
            [str(column) for column in self._df.columns],
            numeric_columns(self._df),
            self._pre_filter_columns,
        )
        self._plot_states = [PlotState.from_dict(default_state.to_dict()) for _ in range(4)]
        self._current_plot_index = 0
        self._layout = "1x1"
        self._rebuild_controls_and_plots()

    def _copy_stats(self) -> None:
        summaries = [summary for summary in self._plot_summaries[: self._visible_plot_count()] if summary is not None]
        text = "\n\n".join(format_plot_summary_to_str(summary) for summary in summaries)
        if text:
            copy_to_clipboard(text)
            ui.notify("Copied plot stats", type="positive")

    def _clear_selection(self) -> None:
        self._selected_row_ids.clear()
        self._refresh_selection_label()

    def _save_config(self) -> None:
        ui.notify("NicePool config persistence is disabled by default", type="info")

    def _on_table_row_selected(self, row: Mapping[str, Any]) -> None:
        row_dict = dict(row)
        self._notify_row_selected(row_dict)

    def _on_plotly_click(self, event: Any, _plot_index: int) -> None:
        args = getattr(event, "args", None)
        payload = args if isinstance(args, dict) else {}
        points = payload.get("points") if isinstance(payload, dict) else None
        if not isinstance(points, list) or not points:
            return
        customdata = points[0].get("customdata") if isinstance(points[0], dict) else None
        if customdata is None:
            return
        row = self._row_for_id(str(customdata))
        if row is not None:
            self._notify_row_selected(row)

    def _notify_row_selected(self, row: dict[str, Any]) -> None:
        row_id = str(row.get(self.config.unique_row_id_col, ""))
        if not row_id:
            return
        self._selected_row_ids = {row_id}
        self._refresh_selection_label()
        if self._on_row_selected is not None:
            self._on_row_selected(row_id, row)

    def _refresh_summary(self) -> None:
        if self._summary_label is None:
            return
        shown = len(self._filtered_dataframe())
        total = len(self._df)
        self._summary_label.text = f"Rows: {shown} shown / {total} total"
        self._summary_label.update()
        self._refresh_selection_label()

    def _refresh_selection_label(self) -> None:
        if self._selection_label is None:
            return
        count = len(self._selected_row_ids)
        self._selection_label.text = "No selection" if count == 0 else f"{count} selected"
        self._selection_label.update()

    def _new_processor(self) -> DataFrameProcessor:
        return DataFrameProcessor(
            self._df,
            pre_filter_columns=list(self._pre_filter_columns),
            unique_row_id_col=self.config.unique_row_id_col,
        )

    def _pre_filter_options(self) -> dict[str, list[str]]:
        return {
            column: [PRE_FILTER_NONE, *self._data_processor.get_pre_filter_values(column)]
            for column in self._pre_filter_columns
        }

    def _filtered_dataframe(self) -> pd.DataFrame:
        state = self._plot_states[self._current_plot_index]
        return self._data_processor.filter_by_pre_filters(state.pre_filter)

    def _filtered_rows(self) -> list[dict[str, Any]]:
        return dataframe_to_rows(self._filtered_dataframe(), unique_row_id_col=self.config.unique_row_id_col)

    def _row_for_id(self, row_id: str) -> dict[str, Any] | None:
        rows = dataframe_to_rows(self._df, unique_row_id_col=self.config.unique_row_id_col)
        for row in rows:
            if str(row.get(self.config.unique_row_id_col)) == str(row_id):
                return row
        return None

    def _build_columns(self) -> list[ColumnDef]:
        columns: list[ColumnDef] = []
        for column in self._df.columns:
            extra: dict[str, object] = {}
            if pd.api.types.is_numeric_dtype(self._df[column]):
                extra["type"] = "numericColumn"
            if column == self.config.unique_row_id_col:
                extra["hide"] = True
            columns.append(ColumnDef(str(column), str(column), extra=extra))
        return columns

    def _table_config(self) -> TableWidgetConfig:
        row_height = None
        header_height = None
        if self.config.table_font_size_px is not None:
            row_height, header_height = scaled_row_header_heights_px(int(self.config.table_font_size_px))
        return TableWidgetConfig(
            selection_mode="single",
            enable_edit_on_double_click=False,
            auto_size_columns=True,
            fit_columns_on_grid_resize=True,
            cell_font_size_px=self.config.table_font_size_px,
            row_height=row_height,
            header_height=header_height,
            show_index_column=False,
        )

    def _visible_plot_count(self) -> int:
        return {"1x1": 1, "1x2": 2, "2x1": 2, "2x2": 4}.get(self._layout, 1)

    def _grid_columns(self) -> int:
        return {"1x1": 1, "1x2": 2, "2x1": 1, "2x2": 2}.get(self._layout, 1)

    def _coerce_state_for_dataframe(self, state: PlotState, default_state: PlotState) -> PlotState:
        columns = {str(column) for column in self._df.columns}
        numeric = set(numeric_columns(self._df))
        data = state.to_dict()
        if data.get("xcol") not in columns:
            data["xcol"] = default_state.xcol
        if data.get("ycol") not in columns or (numeric and data.get("ycol") not in numeric):
            data["ycol"] = default_state.ycol
        if data.get("group_col") not in columns:
            data["group_col"] = default_state.group_col
        if data.get("color_grouping") not in columns:
            data["color_grouping"] = default_state.color_grouping
        data["pre_filter"] = {
            column: data.get("pre_filter", {}).get(column, PRE_FILTER_NONE)
            for column in self._pre_filter_columns
        }
        return PlotState.from_dict(data)
