"""Tests for acqstore.schema_docs markdown table generation."""

from __future__ import annotations

import pytest

from acqstore.acq_image.analysis.diameter_analysis.diameter_analysis import DiameterAnalysis
from acqstore.acq_image.analysis.model import DetectionParamSchema, DetectionValueType
from acqstore.acq_image.analysis.velocity_analysis.radon_velocity_analysis import RadonVelocityAnalysis
from acqstore.acq_image.metadata import (
    EXPERIMENT_METADATA_SCHEMA,
    IMAGE_HEADER_METADATA_SCHEMA,
)
from acqstore.schema import FieldSchema, ValueType
from acqstore.schema_docs import generate_markdown_table


def _header_row(table: str) -> str:
    """Return the first (header) line of a markdown table."""
    return table.splitlines()[0]


def test_empty_fields_raises() -> None:
    with pytest.raises(ValueError):
        generate_markdown_table([], print_markdown=False)


def test_core_columns_always_present() -> None:
    field = FieldSchema(
        name='species',
        display_name='Species',
        value_type=ValueType.STR,
        default_value='',
        description='Animal species.',
    )
    table = generate_markdown_table([field], print_markdown=False)
    header = _header_row(table)
    for column in ('name', 'type', 'default', 'description'):
        assert column in header


def test_field_schema_values_rendered() -> None:
    field = FieldSchema(
        name='depth',
        display_name='Depth',
        value_type=ValueType.FLOAT,
        default_value=None,
        description='Imaging depth in micrometers.',
        group='Sample',
    )
    table = generate_markdown_table([field], print_markdown=False)
    assert 'depth' in table
    assert 'float' in table
    assert 'None' in table
    assert 'Imaging depth in micrometers.' in table
    assert 'Sample' in table


def test_string_default_is_quoted() -> None:
    field = FieldSchema(
        name='note',
        display_name='Note',
        value_type=ValueType.STR,
        default_value='hello',
        description='A note.',
    )
    table = generate_markdown_table([field], print_markdown=False)
    assert '"hello"' in table


def test_optional_column_omitted_when_absent() -> None:
    field = FieldSchema(
        name='note',
        display_name='note',  # equal to name -> display_name column omitted
        value_type=ValueType.STR,
        default_value='',
        description='A note.',
    )
    header = _header_row(generate_markdown_table([field], print_markdown=False))
    assert 'group' not in header
    assert 'display_name' not in header


def test_detection_param_choices_and_methods_columns() -> None:
    field = DetectionParamSchema(
        name='window_width',
        display_name='Window Width',
        value_type=DetectionValueType.INT,
        default=64,
        description='Samples per window.',
        choices=(16, 64, 128),
        methods=('threshold_width',),
    )
    table = generate_markdown_table([field], print_markdown=False)
    header = _header_row(table)
    assert 'choices' in header
    assert 'methods' in header
    assert '16, 64, 128' in table
    assert 'threshold_width' in table


def test_real_schemas_generate_tables() -> None:
    for fields in (
        EXPERIMENT_METADATA_SCHEMA.fields,
        IMAGE_HEADER_METADATA_SCHEMA.fields,
        RadonVelocityAnalysis.get_detection_schema(),
        DiameterAnalysis.get_detection_schema(),
    ):
        table = generate_markdown_table(fields, print_markdown=False)
        assert table.strip()
        for field in fields:
            assert field.name in table
