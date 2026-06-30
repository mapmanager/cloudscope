"""Compact file-list tree panel for the left toolbar."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from cloudscope.event_bus import EventBus
from cloudscope.schema_adapters import _TREE_NAME_COLUMN_MIN_WIDTH_PX
from cloudscope.views.file_list_tree_view import AcqImageListTreeView
from cloudscope.views.view_ids import ViewId
from nicewidgets.aggrid_common.column_def import ColumnDef
from nicewidgets.tree_widget.config import TreeWidgetConfig, font_scaled_column_width_px

_DEFAULT_VISIBLE_COLUMNS = frozenset({'name', 'loaded', 'saved', 'dims'})
_BLANK_HEADER_FIELDS = frozenset({'loaded', 'saved'})
_NAME_MIN_WIDTH_SCALE = 0.8
_MARKER_COLUMN_MULTIPLIER = 3
_MARKER_COLUMN_MINIMUM_PX = 28
_INDEX_COLUMN_WIDTH_MULTIPLIER = 0.8  #0.5


class LeftPanelFileListView(AcqImageListTreeView):
    """File-list tree hosted in the left toolbar with a compact default column set.

    Inherits selection, event subscriptions, and context-menu actions from
    :class:`cloudscope.views.file_list_tree_view.AcqImageListTreeView`. Hidden
    schema columns remain available via the tree widget column-visibility menu.

    Args:
        event_bus: CloudScope event bus.
        app_state: Home-page state for file-list refresh and selection sync.
        table_font_size_px: Tree cell font size in pixels.
        initially_visible: Whether this panel starts visible.
        default_visible_columns: Schema fields shown by default; others start
            hidden but can be toggled from the context menu.
    """

    view_id = ViewId.LEFT_TOOLBAR_FILE_LIST

    def __init__(
        self,
        event_bus: EventBus,
        *,
        app_state: Any | None = None,
        table_font_size_px: int = 12,
        initially_visible: bool = False,
        default_visible_columns: frozenset[str] = _DEFAULT_VISIBLE_COLUMNS,
    ) -> None:
        super().__init__(
            event_bus=event_bus,
            app_state=app_state,
            table_font_size_px=table_font_size_px,
            initially_visible=initially_visible,
            default_visible_columns=default_visible_columns,
        )

    def _build_schema_column_defs(self, font_px: int) -> list[ColumnDef]:
        """Return compact toolbar column definitions.

        Args:
            font_px: Cell font size in pixels.

        Returns:
            Column definitions with toolbar-specific default visibility and
            widths.
        """
        columns = super()._build_schema_column_defs(font_px)
        marker_width = font_scaled_column_width_px(
            font_px,
            multiplier=_MARKER_COLUMN_MULTIPLIER,
            minimum=_MARKER_COLUMN_MINIMUM_PX,
        )
        name_min_width = max(1, int(round(_TREE_NAME_COLUMN_MIN_WIDTH_PX * _NAME_MIN_WIDTH_SCALE)))
        width_by_field: dict[str, dict[str, object]] = {
            'name': {'minWidth': name_min_width, 'flex': 1},
            'loaded': {'width': marker_width, 'minWidth': marker_width},
            'saved': {'width': marker_width, 'minWidth': marker_width},
        }
        adjusted: list[ColumnDef] = []
        for col in columns:
            extra = dict(col.extra)
            width_extra = width_by_field.get(col.field)
            if width_extra is not None:
                extra.update(width_extra)
            header_name = '' if col.field in _BLANK_HEADER_FIELDS else col.headerName
            adjusted.append(replace(col, headerName=header_name, extra=extra))
        return adjusted

    def _build_tree_widget_config(
        self,
        font_px: int,
        row_h: int,
        header_h: int,
    ) -> TreeWidgetConfig:
        """Return tree config with a narrower index column for the toolbar.

        Args:
            font_px: Cell font size in pixels.
            row_h: Row height in pixels.
            header_h: Header height in pixels.

        Returns:
            Tree widget configuration for the left-toolbar panel.
        """
        return TreeWidgetConfig(
            selection_mode='single',
            auto_size_columns=False,
            fit_columns_on_grid_resize=False,
            suppress_movable_columns=True,
            show_index_column=True,
            cell_font_size_px=font_px,
            row_height=row_h,
            header_height=header_h,
            index_column_width_multiplier=_INDEX_COLUMN_WIDTH_MULTIPLIER,
        )
