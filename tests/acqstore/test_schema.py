"""Unit tests for acqstore semantic schema definitions."""

from __future__ import annotations

from pathlib import Path

import pytest

from acqstore.schema import (
    ACQ_FILE_LIST_SCHEMA,
    FieldSchema,
    SchemaDefinition,
    ValueType,
    card_groups,
    validate_patch_for_schema,
    validate_values_for_schema,
)


def test_enum_field_requires_choices() -> None:
    with pytest.raises(ValueError, match='ENUM'):
        FieldSchema(
            name='status',
            display_name='Status',
            value_type=ValueType.ENUM,
        )


def test_field_schema_to_from_dict_round_trip() -> None:
    field = FieldSchema(
        name='path',
        display_name='Path',
        value_type=ValueType.PATH,
        group='File',
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
    assert [field.name for field in schema.visible_fields()] == ['name', 'path', 'num_channels', 'num_rois']
    assert card_groups(schema) == ('File', 'Image', 'ROI')


def test_field_schema_from_dict_ignores_unknown_keys() -> None:
    restored = FieldSchema.from_dict(
        {
            'name': 'a',
            'display_name': 'A',
            'value_type': 'int',
            'visible': True,
            'editable': False,
            'new_future_key': 'ignored',
        }
    )
    assert restored.value_type is ValueType.INT


def test_validate_values_for_schema_rejects_missing_visible_field() -> None:
    with pytest.raises(KeyError, match='name'):
        validate_values_for_schema(ACQ_FILE_LIST_SCHEMA, {'path': '/tmp/a.tif'})


def test_validate_values_for_schema_rejects_extra_keys_by_default() -> None:
    with pytest.raises(ValueError, match='extra'):
        validate_values_for_schema(
            ACQ_FILE_LIST_SCHEMA,
            {
                'name': 'a.tif',
                'path': '/tmp/a.tif',
                'num_channels': 2,
                'num_rois': 0,
                'extra': True,
            },
        )


def test_validate_values_for_schema_allows_extra_values_when_enabled() -> None:
    validate_values_for_schema(
        ACQ_FILE_LIST_SCHEMA,
        {
            'name': 'a.tif',
            'path': '/tmp/a.tif',
            'num_channels': 2,
            'num_rois': 0,
            'extra': True,
        },
        allow_extra_values=True,
    )


def test_validate_patch_for_schema_rejects_unknown_or_noneditable_fields() -> None:
    with pytest.raises(KeyError, match='unknown'):
        validate_patch_for_schema(ACQ_FILE_LIST_SCHEMA, {'unknown': 1})
    with pytest.raises(ValueError, match='name'):
        validate_patch_for_schema(ACQ_FILE_LIST_SCHEMA, {'name': 'new'})


def test_schema_definition_from_dict_ignores_unknown_top_level_keys() -> None:
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
                    'new_future_key': 'ignored',
                }
            ],
        }
    )
    assert restored.schema_id == 'example'
    assert restored.fields[0].value_type is ValueType.INT


def test_acqstore_does_not_import_cloudscope() -> None:
    src_root = Path(__file__).resolve().parents[2] / 'src' / 'acqstore'
    python_files = src_root.rglob('*.py')
    for py_file in python_files:
        text = py_file.read_text()
        assert 'from cloudscope' not in text
        assert 'import cloudscope' not in text
