"""Configuration dataclass for :class:`nicewidgets.tree_widget.TreeWidget`."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

SelectionMode = Literal['none', 'single', 'multiple']

DEFAULT_AG_GRID_ENTERPRISE_MODULE_URL = (
    'https://cdn.jsdelivr.net/npm/ag-grid-enterprise@34.2.0/+esm'
)


@dataclass(frozen=True, slots=True)
class TreeWidgetConfig:
    """Grid-level options for ``TreeWidget``.

    Mirrors the relevant fields of
    :class:`nicewidgets.table_widget.config.TableWidgetConfig`. Cell editing
    and the synthetic index column are intentionally omitted -- a tree's
    depth-first row order has no useful 1-based "row number", and inline cell
    editing is not part of the v1 surface.

    Attributes:
        selection_mode: Row selection behavior.
        clear_selection_on_set_data: Clear tracked/grid selection when
            replacing all rows via :meth:`TreeWidget.set_data`.
        enable_keyboard_row_nav: ArrowUp/ArrowDown select previous/next
            displayed row.
        auto_size_columns: Forwarded to ``ui.aggrid(auto_size_columns=...)``.
        fit_columns_on_grid_resize: When true, AG Grid calls
            ``sizeColumnsToFit`` after browser-side grid size changes.
        cell_font_size_px: When set, cell and header font size in pixels
            (merged into ``defaultColDef``). When ``None``, AG Grid theme
            defaults apply.
        row_height: Optional fixed row height (px). When ``None``, the option
            is omitted (theme/browser default).
        header_height: Optional fixed header row height (px). When ``None``,
            the option is omitted.
        extra_grid_options: Additional AG Grid options merged before any
            ``grid_options`` constructor argument.
        enterprise_module_url: AG Grid Enterprise ESM module URL passed to
            ``ui.aggrid.set_module_source``. ``set_module_source`` is invoked
            once at widget construction time. When ``None``, no override is
            applied (caller is assumed to have configured the bundle).
    """

    selection_mode: SelectionMode = 'single'
    clear_selection_on_set_data: bool = True
    enable_keyboard_row_nav: bool = True
    auto_size_columns: bool = True
    fit_columns_on_grid_resize: bool = False
    cell_font_size_px: int | None = None
    row_height: int | None = None
    header_height: int | None = None
    extra_grid_options: dict[str, Any] = field(default_factory=dict)
    enterprise_module_url: str | None = DEFAULT_AG_GRID_ENTERPRISE_MODULE_URL


def scaled_row_header_heights_px(cell_font_size_px: int) -> tuple[int, int]:
    """Return ``(row_height, header_height)`` in px from a cell font size.

    Mirrors ``nicewidgets.table_widget.config.scaled_row_header_heights_px``
    so tree-view callers can reuse the same row/header chrome scaling without
    crossing the table-widget package boundary.

    Args:
        cell_font_size_px: Body cell font size in pixels (typically >= 8).

    Returns:
        ``(row_height, header_height)`` both positive integers suitable for
        AG Grid ``rowHeight`` and ``headerHeight``.
    """
    fp = max(1, int(cell_font_size_px))
    row_h = max(28, min(64, fp * 2 + 12))
    header_h = max(28, min(56, fp + 24))
    return (row_h, header_h)
