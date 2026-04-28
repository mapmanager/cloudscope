"""Tests for CloudScope schema-to-table adapters."""

from __future__ import annotations

from acqstore.schema import FieldSchema, SchemaDefinition, ValueType
from cloudscope.gui.schema_adapters import (
    field_schema_to_column_def,
    schema_to_column_defs,
)


def test_field_schema_to_column_def_maps_basic_fields() -> None:
    """A simple visible field should map to a visible ColumnDef."""
    field = FieldSchema(
        name="path",
        display_name="Path",
        value_type=ValueType.PATH,
        description="Absolute path.",
    )

    column = field_schema_to_column_def(field)

    assert column.field == "path"
    assert column.headerName == "Path"
    assert column.hide is False
    assert column.extra["editable"] is False
    assert column.extra["headerTooltip"] == "Absolute path."


def test_field_schema_to_column_def_hides_invisible_fields() -> None:
    """Invisible fields should map to hidden columns."""
    field = FieldSchema(name="path", display_name="Path", visible=False)

    column = field_schema_to_column_def(field)

    assert column.hide is True


def test_field_schema_to_column_def_maps_choices_to_select_editor() -> None:
    """Fields with choices should use AG Grid select-editor metadata."""
    field = FieldSchema(
        name="status",
        display_name="Status",
        value_type=ValueType.ENUM,
        choices=("new", "done"),
        editable=True,
    )

    column = field_schema_to_column_def(field)

    assert column.extra["editable"] is True
    assert column.extra["cellEditor"] == "agSelectCellEditor"
    assert column.extra["cellEditorParams"] == {"values": ["new", "done"]}


def test_field_schema_to_column_def_maps_numeric_type() -> None:
    """Integer and float fields should use AG Grid numeric column type."""
    field = FieldSchema(
        name="num_channels",
        display_name="Channels",
        value_type=ValueType.INT,
    )

    column = field_schema_to_column_def(field)

    assert column.extra["type"] == "numericColumn"


def test_schema_to_column_defs_preserves_schema_order() -> None:
    """Schema conversion should preserve backend field order."""
    schema = SchemaDefinition(
        schema_id="example",
        version=1,
        fields=(
            FieldSchema(name="a", display_name="A"),
            FieldSchema(name="b", display_name="B"),
        ),
    )

    columns = schema_to_column_defs(schema)

    assert [column.field for column in columns] == ["a", "b"]
