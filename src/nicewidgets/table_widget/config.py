from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SelectionMode = Literal['none', 'single', 'multiple']


@dataclass(frozen=True, slots=True)
class TableWidgetConfig:
    """Grid-level options for ``TableWidget``.

    Attributes:
        selection_mode: Row selection behavior.
        clear_selection_on_set_data: Clear tracked/grid selection when replacing all rows.
        enable_edit_on_double_click: Start edit on double-click and emit edit-finished events.
        enable_keyboard_row_nav: ArrowUp/ArrowDown select previous/next displayed row.
        stop_editing_when_cells_lose_focus: End edits when focus leaves the grid.
        auto_size_columns: Forwarded to ``ui.aggrid(auto_size_columns=...)``.
        cell_font_size_px: When set, cell and header font size in pixels (merged into
            ``defaultColDef``). When ``None``, AG Grid theme defaults apply.
        extra_grid_options: Additional AG Grid options merged before ``grid_options``.
        show_index_column: When true, prepend a synthetic 1-based ``Index`` column
            (stored in row data at ``index_field``); values follow ``rowData`` list
            order so they move with rows when the grid is sorted by other columns.
        index_field: Row dict / AG Grid field name for the index column (must not
            collide with application row keys).
        index_header: Column header label for the index column.
    """

    selection_mode: SelectionMode = 'single'
    clear_selection_on_set_data: bool = True
    enable_edit_on_double_click: bool = True
    enable_keyboard_row_nav: bool = True
    stop_editing_when_cells_lose_focus: bool = True
    auto_size_columns: bool = True
    cell_font_size_px: int | None = None
    extra_grid_options: dict[str, Any] = field(default_factory=dict)
    show_index_column: bool = True
    index_field: str = 'table_row_index'
    index_header: str = 'Index'
