"""Tests for TableWidget context-menu copy helpers."""

from __future__ import annotations

from typing import Any

from nicewidgets.table_widget import table_widget
from nicewidgets.table_widget.column_def import ColumnDef
from nicewidgets.table_widget.config import TableWidgetConfig
from nicewidgets.table_widget.table_widget import TableWidget


def test_get_table_as_text_returns_tsv_with_visible_columns() -> None:
    """Table text should include headers and current Python-side row values."""
    table = TableWidget(
        columns=(
            ColumnDef(field="path", headerName="Path"),
            ColumnDef(field="name", headerName="Name"),
        ),
        row_id_field="path",
        rows=(
            {"path": "/tmp/b.tif", "name": "B"},
            {"path": "/tmp/a.tif", "name": "A"},
        ),
        config=TableWidgetConfig(show_index_column=False),
    )

    assert table.get_table_as_text() == "Path\tName\n/tmp/b.tif\tB\n/tmp/a.tif\tA"


def test_get_table_as_text_omits_hidden_columns() -> None:
    """Hidden columns should not be copied into the TSV output."""
    table = TableWidget(
        columns=(
            ColumnDef(field="path", headerName="Path"),
            ColumnDef(field="secret", headerName="Secret", hide=True),
        ),
        row_id_field="path",
        rows=({"path": "/tmp/a.tif", "secret": "hidden"},),
        config=TableWidgetConfig(show_index_column=False),
    )

    assert table.get_table_as_text() == "Path\n/tmp/a.tif"


def test_get_table_as_text_normalizes_tabs_and_newlines() -> None:
    """Cell values should be normalized so TSV shape stays valid."""
    table = TableWidget(
        columns=(ColumnDef(field="path", headerName="Path"), ColumnDef(field="note", headerName="Note")),
        row_id_field="path",
        rows=({"path": "/tmp/a.tif", "note": "line 1\nline\t2"},),
        config=TableWidgetConfig(show_index_column=False),
    )

    assert table.get_table_as_text() == "Path\tNote\n/tmp/a.tif\tline 1 line 2"


def test_get_table_as_text_returns_empty_string_without_rows() -> None:
    """Empty tables should copy as an empty string."""
    table = TableWidget(
        columns=(ColumnDef(field="path", headerName="Path"),),
        row_id_field="path",
        rows=(),
        config=TableWidgetConfig(show_index_column=False),
    )

    assert table.get_table_as_text() == ""


def test_copy_table_data_to_clipboard_uses_python_side_tsv(monkeypatch: Any) -> None:
    """Copy Table Data should copy ``get_table_as_text`` without AG Grid JavaScript export."""
    copied: list[str] = []
    notifications: list[tuple[str, str]] = []
    monkeypatch.setattr(table_widget, "copy_to_clipboard", copied.append)
    monkeypatch.setattr(table_widget.ui, "notify", lambda message, type="info": notifications.append((message, type)))
    table = TableWidget(
        columns=(ColumnDef(field="path", headerName="Path"),),
        row_id_field="path",
        rows=({"path": "/tmp/a.tif"},),
        config=TableWidgetConfig(show_index_column=False),
    )

    table.copy_table_data_to_clipboard()

    assert copied == ["Path\n/tmp/a.tif"]
    assert notifications == [("Table data copied to clipboard", "positive")]


def test_context_menu_orders_custom_actions_before_copy_and_columns(monkeypatch: Any) -> None:
    """Context menu should put caller actions, copy, then column toggles."""
    labels: list[str] = []

    def fake_menu_item(label: str, on_click: Any = None) -> None:
        labels.append(label)

    monkeypatch.setattr(table_widget.ui, "menu_item", fake_menu_item)
    monkeypatch.setattr(table_widget.ui, "separator", lambda: labels.append("---"))

    def build_custom_menu(_table: TableWidget) -> None:
        table_widget.ui.menu_item("Reveal In Finder")

    table = TableWidget(
        columns=(ColumnDef(field="path", headerName="Path"),),
        row_id_field="path",
        rows=({"path": "/tmp/a.tif"},),
        on_build_context_menu=build_custom_menu,
        config=TableWidgetConfig(show_index_column=False),
    )

    table._build_context_menu_content()

    assert labels == ["Reveal In Finder", "---", "Copy Table Data", "---", "✓ Path"]
