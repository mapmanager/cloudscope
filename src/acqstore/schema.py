"""Semantic schema definitions for AcqStore values and views.

These schemas are backend-owned and GUI-agnostic. They describe values that can
be rendered in table views, card views, or both.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from enum import StrEnum
from typing import Any


class ValueType(StrEnum):
    """Supported semantic value types."""

    STR = 'str'
    INT = 'int'
    FLOAT = 'float'
    BOOL = 'bool'
    PATH = 'path'
    ENUM = 'enum'


class CardControl(StrEnum):
    """Supported semantic card control hints."""

    READONLY = 'readonly'
    TEXT = 'text'
    TEXTAREA = 'textarea'
    NUMBER = 'number'
    CHECKBOX = 'checkbox'
    SELECT = 'select'


class SemanticKind(StrEnum):
    """Higher-level semantic hint for generic GUI behavior."""

    ID = 'id'
    NAME = 'name'
    PATH = 'path'
    COUNT = 'count'
    STATUS = 'status'
    METRIC = 'metric'
    OTHER = 'other'


@dataclass(frozen=True, slots=True)
class TableHint:
    """Table/grid presentation hints."""

    visible: bool = True
    editable: bool = False
    sortable: bool = True
    filterable: bool = True
    width: int | None = None
    pinned: bool = False
    display_format: str | None = None


@dataclass(frozen=True, slots=True)
class CardHint:
    """Card/form presentation hints."""

    visible: bool = True
    editable: bool = False
    control: CardControl = CardControl.READONLY
    group: str | None = None
    multiline: bool = False


@dataclass(frozen=True, slots=True)
class FieldSchema:
    """Semantic schema for one backend value."""

    name: str
    display_name: str
    value_type: ValueType = ValueType.STR
    semantic_kind: SemanticKind = SemanticKind.OTHER
    description: str = ''
    unit: str | None = None
    required: bool = False
    default: Any | None = None
    choices: tuple[Any, ...] | None = None
    table: TableHint = TableHint()
    card: CardHint = CardHint()

    def __post_init__(self) -> None:
        """Validate schema consistency."""
        if not self.name:
            raise ValueError('FieldSchema.name must not be empty')
        if not self.display_name:
            raise ValueError('FieldSchema.display_name must not be empty')
        if self.card.control is CardControl.SELECT and not self.choices:
            raise ValueError(f"FieldSchema {self.name!r} uses SELECT but has no choices")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'value_type': self.value_type.value,
            'semantic_kind': self.semantic_kind.value,
            'description': self.description,
            'unit': self.unit,
            'required': self.required,
            'default': self.default,
            'choices': list(self.choices) if self.choices is not None else None,
            'table': {
                'visible': self.table.visible,
                'editable': self.table.editable,
                'sortable': self.table.sortable,
                'filterable': self.table.filterable,
                'width': self.table.width,
                'pinned': self.table.pinned,
                'display_format': self.table.display_format,
            },
            'card': {
                'visible': self.card.visible,
                'editable': self.card.editable,
                'control': self.card.control.value,
                'group': self.card.group,
                'multiline': self.card.multiline,
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FieldSchema:
        """Create a field schema from a dictionary.

        Unknown keys are ignored for forward compatibility.
        """
        allowed = {field.name for field in fields(cls)}
        filtered = {key: value for key, value in data.items() if key in allowed}

        if 'value_type' in filtered:
            filtered['value_type'] = ValueType(str(filtered['value_type']))
        if 'semantic_kind' in filtered:
            filtered['semantic_kind'] = SemanticKind(str(filtered['semantic_kind']))
        if 'choices' in filtered and filtered['choices'] is not None:
            filtered['choices'] = tuple(filtered['choices'])
        if 'table' in filtered and filtered['table'] is not None:
            filtered['table'] = TableHint(**filtered['table'])
        if 'card' in filtered and filtered['card'] is not None:
            card_data = dict(filtered['card'])
            if 'control' in card_data:
                card_data['control'] = CardControl(str(card_data['control']))
            filtered['card'] = CardHint(**card_data)

        return cls(**filtered)


@dataclass(frozen=True, slots=True)
class SchemaDefinition:
    """Schema envelope for versioned backend contracts."""

    schema_id: str
    version: int
    fields: tuple[FieldSchema, ...]

    def __post_init__(self) -> None:
        """Validate schema identifier and duplicate fields."""
        if not self.schema_id:
            raise ValueError('SchemaDefinition.schema_id must not be empty')
        if self.version < 1:
            raise ValueError('SchemaDefinition.version must be >= 1')

        names = [field.name for field in self.fields]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f'Duplicate schema field names: {duplicates}')

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable dictionary."""
        return {
            'schema_id': self.schema_id,
            'version': self.version,
            'fields': [field.to_dict() for field in self.fields],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SchemaDefinition:
        """Create a schema definition from a dictionary.

        Unknown keys are ignored for forward compatibility.
        """
        schema_id = str(data.get('schema_id', ''))
        version = int(data.get('version', 1))
        raw_fields = data.get('fields', [])
        parsed_fields = tuple(
            FieldSchema.from_dict(item)
            for item in raw_fields
            if isinstance(item, dict)
        )
        return cls(schema_id=schema_id, version=version, fields=parsed_fields)

    def table_fields(self) -> tuple[FieldSchema, ...]:
        """Return fields visible in table/grid views."""
        return tuple(field for field in self.fields if field.table.visible)

    def card_fields(self) -> tuple[FieldSchema, ...]:
        """Return fields visible in card/form views."""
        return tuple(field for field in self.fields if field.card.visible)

    def card_groups(self) -> tuple[str | None, ...]:
        """Return card groups in first-seen order."""
        groups: list[str | None] = []
        for field in self.card_fields():
            if field.card.group not in groups:
                groups.append(field.card.group)
        return tuple(groups)


ACQ_FILE_LIST_SCHEMA = SchemaDefinition(
    schema_id='acq_file_list',
    version=1,
    fields=(
        FieldSchema(
            name='path',
            display_name='Path',
            value_type=ValueType.PATH,
            semantic_kind=SemanticKind.PATH,
            table=TableHint(width=380),
            card=CardHint(control=CardControl.READONLY, group='File'),
        ),
        FieldSchema(
            name='num_channels',
            display_name='Channels',
            value_type=ValueType.INT,
            semantic_kind=SemanticKind.COUNT,
            table=TableHint(width=120),
            card=CardHint(control=CardControl.READONLY, group='Image'),
        ),
        FieldSchema(
            name='num_rois',
            display_name='ROIs',
            value_type=ValueType.INT,
            semantic_kind=SemanticKind.COUNT,
            table=TableHint(width=120),
            card=CardHint(control=CardControl.READONLY, group='ROI'),
        ),
    ),
)
