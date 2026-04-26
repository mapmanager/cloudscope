"""Unit tests for acqstore semantic schema definitions."""

from __future__ import annotations

import pytest

from acqstore.schema import (
    ACQ_FILE_LIST_SCHEMA,
    CardControl,
    CardHint,
    FieldSchema,
    SchemaDefinition,
    SemanticKind,
    TableHint,
    ValueType,
)


def test_field_schema_select_requires_choices() -> None:
    with pytest.raises(ValueError, match='SELECT'):
        FieldSchema(
            name='status',
            display_name='Status',
            card=CardHint(control=CardControl.SELECT),
        )


def test_field_schema_to_from_dict_round_trip() -> None:
    field = FieldSchema(
        name='path',
        display_name='Path',
        value_type=ValueType.PATH,
        semantic_kind=SemanticKind.PATH,
        table=TableHint(width=240),
        card=CardHint(group='File'),
    )
    restored = FieldSchema.from_dict(field.to_dict())
    assert restored == field


def test_schema_definition_rejects_duplicate_fields() -> None:
    with pytest.raises(ValueError, match='Duplicate schema field names'):
        SchemaDefinition(
            schema_id='x',
            version=1,
            fields=(
                FieldSchema(name='a', display_name='A'),
                FieldSchema(name='a', display_name='A2'),
            ),
        )


def test_schema_definition_helpers() -> None:
    schema = ACQ_FILE_LIST_SCHEMA
    assert schema.schema_id == 'acq_file_list'
    assert schema.version == 1
    assert [field.name for field in schema.table_fields()] == ['path', 'num_channels', 'num_rois']
    assert schema.card_groups() == ('File', 'Image', 'ROI')


def test_schema_from_dict_ignores_unknown_keys() -> None:
    restored = SchemaDefinition.from_dict(
        {
            'schema_id': 'example',
            'version': 1,
            'unknown': 'ignored',
            'fields': [
                {
                    'name': 'a',
                    'display_name': 'A',
                    'value_type': 'int',
                    'semantic_kind': 'count',
                    'table': {'visible': True},
                    'card': {'visible': True, 'control': 'readonly'},
                    'new_future_key': 'ignored',
                }
            ],
        }
    )
    assert restored.schema_id == 'example'
    assert restored.fields[0].value_type is ValueType.INT
