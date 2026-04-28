"""Tests for ``ExperimentMetadata`` and ``EXPERIMENT_METADATA_SCHEMA``."""

from __future__ import annotations

import pytest

from acqstore.acq_image.metadata import EXPERIMENT_METADATA_SCHEMA, ExperimentMetadata
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


def test_experiment_metadata_from_dict_coerces_str_none() -> None:
    m = ExperimentMetadata.from_dict({'species': None, 'depth': 2.0})
    assert m.species == ''
    assert m.depth == 2.0


def test_acq_file_list_schema_field_names_stable() -> None:
    names = ACQ_FILE_LIST_SCHEMA.field_names()
    assert names == ('name', 'path', 'num_channels', 'num_rois')
