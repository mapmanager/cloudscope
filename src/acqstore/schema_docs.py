"""Generate markdown documentation tables from AcqStore schemas.

This module renders human-readable markdown tables from the two AcqStore schema
families used to describe values and parameters:

- :class:`acqstore.schema.FieldSchema` (for example metadata schemas such as
  ``EXPERIMENT_METADATA_SCHEMA`` and ``IMAGE_HEADER_METADATA_SCHEMA``).
- :class:`acqstore.acq_image.analysis.model.DetectionParamSchema` (for analysis
  detection parameters such as velocity and diameter detection schemas).

The generated tables are intended to be copy/pasted into the MkDocs site under
``docs/``. The output always includes the core columns ``name``, ``type``,
``default``, and ``description``; additional columns are included only when at
least one field populates them.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import Any

import pandas as pd

from acqstore.acq_image.analysis.model import DetectionParamSchema
from acqstore.schema import FieldSchema

SchemaField = FieldSchema | DetectionParamSchema

_CORE_COLUMNS: tuple[str, ...] = ('name', 'type', 'default', 'description')

# Optional columns inserted between ``default`` and ``description`` when at least
# one field provides an informative value.
_OPTIONAL_COLUMNS: tuple[str, ...] = (
    'display_name',
    'unit',
    'choices',
    'editable',
    'required',
    'group',
    'methods',
)


def _type_str(field: SchemaField) -> str:
    """Return the value-type label for a schema field.

    Args:
        field: A ``FieldSchema`` or ``DetectionParamSchema`` instance.

    Returns:
        The value type as a string (for example ``"int"`` or ``"enum"``).
    """
    value_type = field.value_type
    return str(getattr(value_type, 'value', value_type))


def _format_default(value: Any) -> str:
    """Format a default value for display in a markdown table.

    Args:
        value: The raw default value from the schema field.

    Returns:
        A string representation. ``None`` becomes ``"None"``, strings are
        quoted, and enum members are rendered using their ``value``.
    """
    if value is None:
        return 'None'
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, str):
        return f'"{value}"'
    return str(value)


def _format_choices(value: Any) -> str:
    """Format a choices tuple for display.

    Args:
        value: The ``choices`` attribute value, or ``None``.

    Returns:
        A comma-separated string, or an empty string when there are no choices.
    """
    if not value:
        return ''
    parts: list[str] = []
    for choice in value:
        if isinstance(choice, Enum):
            parts.append(str(choice.value))
        else:
            parts.append(str(choice))
    return ', '.join(parts)


def _optional_value(field: SchemaField, column: str) -> Any:
    """Return the raw value for one optional column on a field.

    Args:
        field: The schema field.
        column: The optional column name.

    Returns:
        The raw attribute value, or ``None`` when the attribute is absent.
    """
    if column == 'display_name':
        display_name = getattr(field, 'display_name', '') or ''
        name = getattr(field, 'name', '')
        return display_name if display_name and display_name != name else None
    if column == 'choices':
        return getattr(field, 'choices', None)
    if column == 'methods':
        return getattr(field, 'methods', None)
    return getattr(field, column, None)


def _is_informative(column: str, value: Any) -> bool:
    """Return whether an optional column value is worth showing.

    Args:
        column: The optional column name.
        value: The raw value returned by :func:`_optional_value`.

    Returns:
        ``True`` when the value should cause the column to be included.
    """
    if value is None:
        return False
    if column in {'editable', 'required'}:
        return True
    if isinstance(value, str):
        return value != ''
    if isinstance(value, (tuple, list)):
        return len(value) > 0
    return True


def _format_optional(column: str, value: Any) -> Any:
    """Format an optional column value for display.

    Args:
        column: The optional column name.
        value: The raw value returned by :func:`_optional_value`.

    Returns:
        A display-ready value (string for collections, otherwise the value).
    """
    if value is None:
        return ''
    if column in {'choices', 'methods'}:
        return _format_choices(value)
    return value


def generate_markdown_table(
    fields: Sequence[SchemaField],
    *,
    title: str | None = None,
    print_markdown: bool = True,
) -> str:
    """Generate a markdown documentation table from schema fields.

    Works with both :class:`acqstore.schema.FieldSchema` and
    :class:`acqstore.acq_image.analysis.model.DetectionParamSchema` sequences,
    which both expose ``name``, ``display_name``, ``value_type``, ``default``,
    ``description``, ``choices``, ``unit``, and ``editable``.

    The table always contains ``name``, ``type``, ``default``, and
    ``description``. Optional columns (``display_name``, ``unit``, ``choices``,
    ``editable``, ``required``, ``group``, ``methods``) are included only when at
    least one field provides an informative value for them.

    Args:
        fields: Schema fields to document. Must not be empty.
        title: Optional heading printed above the table (as ``"## {title}"``).
        print_markdown: If ``True``, print the heading and table to stdout.

    Returns:
        The markdown table as a string (without the heading).

    Raises:
        ValueError: If ``fields`` is empty.
    """
    if not fields:
        raise ValueError('generate_markdown_table requires at least one field')

    included_optional: list[str] = []
    for column in _OPTIONAL_COLUMNS:
        if any(_is_informative(column, _optional_value(f, column)) for f in fields):
            included_optional.append(column)

    columns = ['name', 'type', 'default', *included_optional, 'description']

    rows: list[dict[str, Any]] = []
    for field in fields:
        row: dict[str, Any] = {
            'name': field.name,
            'type': _type_str(field),
            'default': _format_default(field.default),
            'description': getattr(field, 'description', '') or '',
        }
        for column in included_optional:
            row[column] = _format_optional(column, _optional_value(field, column))
        rows.append(row)

    df = pd.DataFrame(rows, columns=columns)
    table = df.to_markdown(index=False)

    if print_markdown:
        if title:
            print(f'\n## {title}\n')
        print(table)
        print()

    return table
