"""Tests for AcqImage sidecar JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import tifffile

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.roi import LineEndpoints, RectRoiBounds


def _write_tif(path: Path) -> None:
    tifffile.imwrite(path, np.zeros((10, 20), dtype=np.uint8))


def test_sidecar_path_uses_full_filename_plus_json(tmp_path: Path) -> None:
    path = tmp_path / 'sample.tif'
    _write_tif(path)
    acq = AcqImage(str(path))
    assert acq.get_sidecar_json_path() == str(path.resolve()) + '.json'


def test_save_writes_expected_top_level_contract(tmp_path: Path) -> None:
    path = tmp_path / 'sample.tif'
    _write_tif(path)
    acq = AcqImage(str(path))
    acq.rois.create_rect_roi(RectRoiBounds(1, 5, 2, 7), name='rect')
    acq.rois.create_line_roi(LineEndpoints(1, 2, 3, 4), name='line')
    acq.apply_metadata_patch('experiment_metadata', {'species': 'mouse'})

    acq.save()

    sidecar = Path(acq.get_sidecar_json_path())
    payload = json.loads(sidecar.read_text(encoding='utf-8'))
    assert set(payload.keys()) == {
        'accepted',
        'analysis',
        'experiment_metadata',
        'image_header_metadata',
        'rois',
        'version',
    }
    assert payload['version'] == 2
    assert isinstance(payload['rois'], list)
    assert payload['experiment_metadata']['species'] == 'mouse'


def test_load_round_trip_restores_rois_and_experiment_metadata(tmp_path: Path) -> None:
    path = tmp_path / 'sample.tif'
    _write_tif(path)

    source = AcqImage(str(path))
    source.rois.create_rect_roi(RectRoiBounds(1, 5, 2, 7), name='rect')
    source.rois.create_line_roi(LineEndpoints(1, 2, 3, 4), name='line')
    source.apply_metadata_patch('experiment_metadata', {'species': 'mouse', 'genotype': 'wt'})
    source.save()

    loaded = AcqImage(str(path))
    assert loaded.rois.num_rois == 2
    assert loaded.rois.get_roi_ids() == [1, 2]
    exp = loaded.get_metadata_section('experiment_metadata')
    assert exp.species == 'mouse'
    assert exp.genotype == 'wt'


def test_load_ignores_image_header_values_in_json_phase1(tmp_path: Path) -> None:
    path = tmp_path / 'sample.tif'
    _write_tif(path)
    acq = AcqImage(str(path))
    acq.save()

    sidecar = Path(acq.get_sidecar_json_path())
    payload = json.loads(sidecar.read_text(encoding='utf-8'))
    payload['image_header_metadata']['physical_unit_x'] = 999.0
    payload['image_header_metadata']['physical_unit_y'] = 777.0
    sidecar.write_text(json.dumps(payload), encoding='utf-8')

    loaded = AcqImage(str(path))
    header = loaded.get_metadata_section('acq_image_header').get_values()
    assert header['physical_unit_x'] != 999.0
    assert header['physical_unit_y'] != 777.0


def test_malformed_or_invalid_sidecar_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / 'sample.tif'
    _write_tif(path)
    sidecar = Path(str(path.resolve()) + '.json')
    sidecar.write_text('{"version": 999, "rois": []}', encoding='utf-8')

    loaded = AcqImage(str(path))
    assert loaded.rois.num_rois == 0
    exp = loaded.get_metadata_section('experiment_metadata')
    assert exp.species == ''
