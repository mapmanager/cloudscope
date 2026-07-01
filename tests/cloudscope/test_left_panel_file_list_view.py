"""Tests for LeftPanelFileListView compact toolbar column layout."""

from __future__ import annotations

from cloudscope.event_bus import EventBus
from cloudscope.schema_adapters import _TREE_NAME_COLUMN_MIN_WIDTH_PX
from cloudscope.views.left_panel_file_list_view import LeftPanelFileListView
from cloudscope.views.view_ids import ViewId
from nicewidgets.tree_widget.config import font_scaled_column_width_px


def test_left_panel_default_visible_columns() -> None:
    """Toolbar file list should show name, loaded, saved, and dims by default."""
    view = LeftPanelFileListView(event_bus=EventBus())
    columns = view._build_schema_column_defs(13)
    by_field = {col.field: col for col in columns}

    assert by_field['name'].hide is False
    assert by_field['loaded'].hide is False
    assert by_field['saved'].hide is False
    assert by_field['dims'].hide is False
    assert by_field['parent'].hide is True
    assert by_field['grandparent'].hide is True


def test_left_panel_column_widths_and_blank_marker_headers() -> None:
    """Toolbar marker columns should be narrow with blank headers."""
    font_px = 13
    view = LeftPanelFileListView(event_bus=EventBus(), table_font_size_px=font_px)
    columns = view._build_schema_column_defs(font_px)
    by_field = {col.field: col for col in columns}

    marker_width = font_scaled_column_width_px(font_px, multiplier=3, minimum=28)
    name_min_width = max(1, int(round(_TREE_NAME_COLUMN_MIN_WIDTH_PX * 0.8)))

    assert by_field['name'].extra['minWidth'] == name_min_width
    assert by_field['loaded'].headerName == ''
    assert by_field['saved'].headerName == ''
    assert by_field['loaded'].extra['width'] == marker_width
    assert by_field['saved'].extra['width'] == marker_width


def test_left_panel_tree_config_uses_narrow_index_column() -> None:
    """Toolbar tree should use a reduced index column width multiplier."""
    view = LeftPanelFileListView(event_bus=EventBus(), table_font_size_px=12)
    config = view._build_tree_widget_config(12, 36, 36)

    assert config.index_column_width_multiplier == 0.8
    assert view.view_id is ViewId.LEFT_TOOLBAR_FILE_LIST
