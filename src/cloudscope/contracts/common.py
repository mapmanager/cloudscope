"""Shared core contract types for CloudScope.

This module defines small, backend-facing shared types used by the CloudScope
contract layer. These types are intentionally semantic rather than tied to any
specific GUI toolkit. The GUI may adapt them into NiceGUI widgets, AG Grid
columns, tooltips, and other presentation details.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class AnalysisKind(StrEnum):
    """Supported analysis kinds known to CloudScope.

    The backend may support only a subset of these values for a given file.
    CloudScope uses this enum in controller state, events, and protocol methods.
    """

    NONE = 'none'
    VELOCITY = 'velocity'
    DIAMETER = 'diameter'


@dataclass(frozen=True, slots=True)
class MetadataFieldSchema:
    """Describe one editable metadata field.

    Attributes:
        name: Stable backend key for this field.
        display_name: Human-readable label for GUI display.
        description: Longer help text describing the field semantics.
        editable: Whether the GUI should allow user edits for this field.
        visible: Whether the field should be shown by default.
        required: Whether the field must hold a value.
        value_type: Semantic value type such as ``str``, ``int``, ``float``,
            ``bool``, ``enum``, or ``path``.
        default: Optional default value used when creating new records or
            pre-populating editing widgets.
        choices: Optional constrained value list for enum-like fields.
        group: Optional logical group name for metadata form layout.
        order: Stable display order within a metadata section.
        unit: Optional engineering or scientific unit string.
        display_format: Optional display hint for formatting values.
        multiline: Whether a text-oriented widget should allow multiple lines.
    """

    name: str
    display_name: str
    description: str = ''
    editable: bool = True
    visible: bool = True
    required: bool = False
    value_type: str = 'str'
    default: Any | None = None
    choices: tuple[Any, ...] | None = None
    group: str | None = None
    order: int = 0
    unit: str | None = None
    display_format: str | None = None
    multiline: bool = False


@dataclass(frozen=True, slots=True)
class TableColumnSchema:
    """Describe one file-table column.

    Attributes:
        name: Stable backend field key for the column.
        display_name: Human-readable column header.
        description: Longer help text for the column.
        value_type: Semantic value type for formatting and editor selection.
        visible: Whether the column should be shown by default.
        order: Stable display order.
        sortable: Whether the GUI may allow sorting by this column.
        filterable: Whether the GUI may allow filtering by this column.
        editable: Whether the GUI may allow in-table edits for this column.
        width: Optional preferred width hint in pixels.
        pinned: Whether the GUI may pin the column by default.
        display_format: Optional formatting hint for rendered values.
    """

    name: str
    display_name: str
    description: str = ''
    value_type: str = 'str'
    visible: bool = True
    order: int = 0
    sortable: bool = True
    filterable: bool = True
    editable: bool = False
    width: int | None = None
    pinned: bool = False
    display_format: str | None = None
