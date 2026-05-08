"""Tests for ``ExperimentMetadata`` and ``EXPERIMENT_METADATA_SCHEMA``."""

from __future__ import annotations

import pytest
import numpy as np

from acqstore.acq_image.file_loaders.base_file_loader import ImageHeader
from acqstore.acq_image.metadata import (
    EXPERIMENT_METADATA_SCHEMA,
    IMAGE_HEADER_METADATA_SCHEMA,
    ExperimentMetadata,
    ImageHeaderMetadata,
)
from acqstore.schema import ACQ_FILE_LIST_SCHEMA, ValueType, validate_values_for_schema


def test_experiment_metadata_get_values_matches_schema() -> None:
    m = ExperimentMetadata(species='mouse', depth=1.5, branch_order=2)
    row = m.get_values()
    validate_values_for_schema(EXPERIMENT_METADATA_SCHEMA, row)
    assert row['species'] == 'mouse'
    assert row['depth'] == 1.5
    assert row['branch_order'] == 2
    assert row['note'] == ''


def test_experiment_metadata_get_values_coerces_str_none_to_empty() -> None:
    m = ExperimentMetadata()
    row = m.get_values()
    for fs in EXPERIMENT_METADATA_SCHEMA.fields:
        if fs.value_type is ValueType.STR:
            assert isinstance(row[fs.name], str)


def test_experiment_metadata_update_values_updates_field() -> None:
    m = ExperimentMetadata()
    m.update_values({'species': 'rat', 'depth': 3.0})
    assert m.species == 'rat'
    assert m.depth == 3.0


def test_experiment_metadata_update_values_coerces_none_str_to_empty() -> None:
    m = ExperimentMetadata(species='x')
    m.update_values({'species': None})
    assert m.species == ''


def test_experiment_metadata_update_values_rejects_unknown_field() -> None:
    m = ExperimentMetadata()
    with pytest.raises(KeyError):
        m.update_values({'nope': 'a'})


def test_experiment_metadata_dirty_flag_tracks_changed_values() -> None:
    m = ExperimentMetadata()
    assert m.is_dirty() is False
    m.update_values({'species': 'mouse'})
    assert m.is_dirty() is True
    m.set_clean()
    assert m.is_dirty() is False
    m.update_values({'species': 'mouse'})  # no effective value change
    assert m.is_dirty() is False


def test_experiment_metadata_from_dict_coerces_str_none() -> None:
    m = ExperimentMetadata.from_dict({'species': None, 'depth': 2.0})
    assert m.species == ''
    assert m.depth == 2.0


def test_acq_file_list_schema_core_contract_and_unique_names() -> None:
    """Guard stable consumer expectations without freezing the full field list."""
    names_tuple = ACQ_FILE_LIST_SCHEMA.field_names()
    names_set = set(names_tuple)
    assert len(names_set) == len(names_tuple)
    assert {'name', 'path', 'accept', 'saved'}.issubset(names_set)


def test_experiment_metadata_schema_defaults_match_dataclass_defaults() -> None:
    metadata = ExperimentMetadata()
    values = metadata.get_values()
    for fs in EXPERIMENT_METADATA_SCHEMA.fields:
        assert fs.default_value == values[fs.name]


def test_image_header_with_coerced_physical_calibration_normalizes_invalid_units() -> None:
    header = ImageHeader(
        path='/tmp/a.oir',
        shape=(10, 20),
        dims=('Y', 'X'),
        sizes={'Y': 10, 'X': 20},
        dtype=np.dtype('uint16'),
        num_channels=1,
        num_scenes=1,
        physical_units=('bad', -2.0),
        physical_units_labels=('', ''),
    )
    coerced = header.with_coerced_physical_calibration()
    assert coerced.physical_units == (1.0, 1.0)
    assert coerced.physical_units_labels == ('Pixels', 'Pixels')


def test_image_header_metadata_coerces_on_init_and_reads_normalized_units() -> None:
    header = ImageHeader(
        path='/tmp/a.oir',
        shape=(10, 20),
        dims=('Y', 'X'),
        sizes={'Y': 10, 'X': 20},
        dtype=np.dtype('uint16'),
        num_channels=1,
        num_scenes=1,
        physical_units=('x',),
        physical_units_labels=('',),
    )
    section = ImageHeaderMetadata(header, apply_header=lambda _h: None)
    values = section.get_values()
    assert values['physical_unit_y'] == 1.0
    assert values['physical_unit_x'] == 1.0
    assert values['physical_label_y'] == 'Pixels'


def test_image_header_metadata_get_values_and_patch_updates_yx() -> None:
    header = ImageHeader(
        path='/tmp/a.oir',
        shape=(10, 20),
        dims=('Y', 'X'),
        sizes={'Y': 10, 'X': 20},
        dtype=np.dtype('uint16'),
        num_channels=1,
        num_scenes=1,
        physical_units=(1.0, 2.0),
        physical_units_labels=('um', 'um'),
    )
    seen: list[ImageHeader] = []
    section = ImageHeaderMetadata(header, apply_header=lambda h: seen.append(h))
    values = section.get_values()
    validate_values_for_schema(IMAGE_HEADER_METADATA_SCHEMA, values)
    assert values['physical_unit_y'] == 1.0
    assert values['physical_unit_x'] == 2.0
    section.update_values({'physical_unit_y': 3.5, 'physical_label_x': 'px'})
    assert section.is_dirty() is True
    assert seen[-1].physical_units[0] == 3.5
    assert seen[-1].physical_units_labels[1] == 'px'


def test_metadata_section_objects_expose_expected_methods_and_attributes() -> None:
    exp = ExperimentMetadata()
    header = ImageHeader(
        path='/tmp/a.oir',
        shape=(10, 20),
        dims=('Y', 'X'),
        sizes={'Y': 10, 'X': 20},
        dtype=np.dtype('uint16'),
        num_channels=1,
        num_scenes=1,
        physical_units=(1.0, 1.0),
        physical_units_labels=('Pixels', 'Pixels'),
    )
    img = ImageHeaderMetadata(header, apply_header=lambda _h: None)
    for section in (exp, img):
        assert isinstance(section.metadata_section_id, str)
        assert isinstance(section.display_section_title, str)
        assert callable(section.get_schema)
        assert callable(section.get_values)
        assert callable(section.update_values)
        assert callable(section.is_dirty)
        assert callable(section.set_clean)
