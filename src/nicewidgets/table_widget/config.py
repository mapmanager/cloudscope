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
        extra_grid_options: Additional AG Grid options merged before ``grid_options``.
    """

    selection_mode: SelectionMode = 'single'
    clear_selection_on_set_data: bool = True
    enable_edit_on_double_click: bool = True
    enable_keyboard_row_nav: bool = True
    stop_editing_when_cells_lose_focus: bool = True
    auto_size_columns: bool = True
    extra_grid_options: dict[str, Any] = field(default_factory=dict)
