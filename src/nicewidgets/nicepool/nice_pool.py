"""Reusable DataFrame-driven pool widget for NiceGUI applications.

``NicePool`` is intentionally independent of CloudScope. It accepts a pandas
DataFrame, exposes optional categorical pre-filters, renders a selectable table,
and calls back with ``(row_id, row_dict)`` when the user selects a row. CloudScope
uses the callback to publish its own MVC intents.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pandas as pd
from nicegui import ui

from nicewidgets.aggrid_common.column_def import ColumnDef
from nicewidgets.nicepool.config import NicePoolConfig, resolve_pre_filter_columns
from nicewidgets.nicepool.dataframe_adapter import (
    ALL_FILTER_VALUE,
    dataframe_to_rows,
    filter_dataframe,
    unique_filter_values,
)
from nicewidgets.table_widget.config import TableWidgetConfig, scaled_row_header_heights_px
from nicewidgets.table_widget.table_widget import TableWidget


RowSelectedCallback = Callable[[str, dict[str, Any]], None]


class NicePool:
    """General-purpose DataFrame pool widget.

    Args:
        df: Source DataFrame. The widget keeps a copy.
        config: Optional widget configuration.
        on_row_selected: Callback invoked with row id and row dict when a table
            row is selected.
    """

    def __init__(
        self,
        df: pd.DataFrame,
        *,
        config: NicePoolConfig | None = None,
        on_row_selected: RowSelectedCallback | None = None,
    ) -> None:
        self.config = config or NicePoolConfig()
        self._on_row_selected = on_row_selected
        self._df = df.copy()
        self._pre_filter_columns = resolve_pre_filter_columns(
            tuple(self._df.columns),
            explicit_columns=self.config.pre_filter_columns,
            auto_columns=self.config.auto_pre_filter_columns,
        )
        self._filters: dict[str, object] = {column: ALL_FILTER_VALUE for column in self._pre_filter_columns}
        self._root: ui.column | None = None
        self._summary_label: ui.label | None = None
        self._filter_selects: dict[str, ui.select] = {}
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
                with ui.row().classes("w-full gap-2 items-center"):
                    self._build_filter_controls()
                table_container = ui.column().classes("w-full grow min-h-0")
                self._table = TableWidget(
                    self._build_columns(),
                    self.config.unique_row_id_col,
                    self._filtered_rows(),
                    on_row_selected=self._on_table_row_selected,
                    config=self._table_config(),
                )
                self._table.build(table_container)
        self._refresh_summary()
        return self._root

    def set_dataframe(self, df: pd.DataFrame) -> None:
        """Replace the DataFrame and refresh the table wholesale.

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
        self._filters = {
            column: self._filters.get(column, ALL_FILTER_VALUE)
            for column in self._pre_filter_columns
        }
        self._coerce_filters_to_available_values()
        self._refresh_filter_controls()
        if self._table is not None:
            self._table.set_data(self._filtered_rows())
        self._refresh_summary()

    def get_selected_row_ids(self) -> list[str]:
        """Return selected row ids known by the table.

        Returns:
            Selected row ids.
        """
        if self._table is None:
            return []
        return self._table.get_selected_row_ids()

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
            row_height, header_height = scaled_row_header_heights_px(
                int(self.config.table_font_size_px)
            )
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

    def _build_filter_controls(self) -> None:
        values = unique_filter_values(self._df, self._pre_filter_columns)
        for column in self._pre_filter_columns:
            options = {ALL_FILTER_VALUE: "All", **{value: value for value in values[column]}}
            select = ui.select(
                options=options,
                value=ALL_FILTER_VALUE,
                label=column,
                on_change=lambda _event=None, col=column: self._on_filter_changed(col),
            ).classes("min-w-[8rem]").props("dense outlined")
            self._filter_selects[column] = select

    def _refresh_filter_controls(self) -> None:
        if not self._filter_selects:
            return
        values = unique_filter_values(self._df, self._pre_filter_columns)
        for column, select in tuple(self._filter_selects.items()):
            if column not in self._pre_filter_columns:
                select.visible = False
                select.update()
                continue
            options = {ALL_FILTER_VALUE: "All", **{value: value for value in values[column]}}
            select.options = options
            select.value = self._filters.get(column, ALL_FILTER_VALUE)
            select.visible = True
            select.update()

    def _coerce_filters_to_available_values(self) -> None:
        values = unique_filter_values(self._df, self._pre_filter_columns)
        for column in self._pre_filter_columns:
            value = self._filters.get(column, ALL_FILTER_VALUE)
            if value not in (ALL_FILTER_VALUE, None) and str(value) not in values.get(column, []):
                self._filters[column] = ALL_FILTER_VALUE

    def _on_filter_changed(self, column: str) -> None:
        select = self._filter_selects.get(column)
        self._filters[column] = ALL_FILTER_VALUE if select is None else select.value
        if self._table is not None:
            self._table.set_data(self._filtered_rows())
        self._refresh_summary()

    def _filtered_dataframe(self) -> pd.DataFrame:
        return filter_dataframe(self._df, self._filters)

    def _filtered_rows(self) -> list[dict[str, Any]]:
        return dataframe_to_rows(
            self._filtered_dataframe(),
            unique_row_id_col=self.config.unique_row_id_col,
        )

    def _refresh_summary(self) -> None:
        if self._summary_label is None:
            return
        total = len(self._df)
        shown = len(self._filtered_dataframe())
        self._summary_label.text = f"Rows: {shown} shown / {total} total"
        self._summary_label.update()

    def _on_table_row_selected(self, row: Mapping[str, Any]) -> None:
        row_dict = dict(row)
        row_id = str(row_dict.get(self.config.unique_row_id_col, ""))
        if not row_id or self._on_row_selected is None:
            return
        self._on_row_selected(row_id, row_dict)
