"""Adapters from AcqStore semantic schemas to NiceWidgets table definitions.

This module belongs in CloudScope because it translates backend-owned AcqStore
schemas into GUI-owned NiceWidgets definitions. AcqStore must not import
CloudScope or NiceWidgets.
"""

from __future__ import annotations

from typing import Any

from acqstore.schema import FieldSchema, SchemaDefinition, ValueType
from nicewidgets.table_widget.column_def import ColumnDef


def field_schema_to_column_def(field: FieldSchema) -> ColumnDef:
    """Convert one AcqStore field schema into a NiceWidgets column definition.

    Args:
        field: AcqStore semantic field schema. ``field.name`` is used as the row
            key, and ``field.display_name`` is used as the column header.

    Returns:
        NiceWidgets column definition preserving the backend field name.
    """
    extra: dict[str, Any] = {
        "editable": field.editable,
    }

    if field.description:
        extra["headerTooltip"] = field.description

    if field.choices is not None:
        extra["cellEditor"] = "agSelectCellEditor"
        extra["cellEditorParams"] = {"values": list(field.choices)}

    if field.value_type in (ValueType.INT, ValueType.FLOAT):
        extra["type"] = "numericColumn"

    if field.value_type is ValueType.BOOL:
        extra["cellRenderer"] = "agCheckboxCellRenderer"
        if field.editable:
            extra["cellEditor"] = "agCheckboxCellEditor"

    return ColumnDef(
        field=field.name,
        headerName=field.display_name,
        hide=not field.visible,
        extra=extra,
    )


def schema_to_column_defs(schema: SchemaDefinition) -> list[ColumnDef]:
    """Convert an AcqStore schema into NiceWidgets table columns.

    Args:
        schema: AcqStore semantic schema.

    Returns:
        Column definitions in schema field order.
    """
    return [field_schema_to_column_def(field) for field in schema.fields]
