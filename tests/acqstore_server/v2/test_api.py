"""HTTP integration tests for AcqStore Server API v2."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient

from acqstore.acq_image.file_loaders.base_file_loader import BaseFileLoader, ReferenceImage
from acqstore_server.app import create_app
from acqstore_server.v2.session_store import SessionStore


def _write_cyx_tif(path: Path, shape: tuple[int, int, int] = (3, 5, 4)) -> np.ndarray:
    array = np.arange(int(np.prod(shape)), dtype=np.uint16).reshape(shape)
    tifffile.imwrite(path, array, metadata={'axes': 'CYX'}, photometric='minisblack')
    return array


def test_v2_open_and_download_selected_channels(tmp_path: Path) -> None:
    path = tmp_path / 'multi.tif'
    source = _write_cyx_tif(path)
    client = TestClient(create_app(v2_session_store=SessionStore()))

    response = client.post(
        '/api/v2/open',
        json={'path': str(path.resolve()), 'channelIndices': [2, 0]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['source']['numChannels'] == 3
    assert payload['source']['sourceDtype'] == 'uint16'
    assert payload['plane']['shape'] == [5, 4]
    assert payload['plane']['encoding'] == 'raw-f32-le'
    assert [item['index'] for item in payload['channels']] == [2, 0]

    for item, source_index in zip(payload['channels'], [2, 0], strict=True):
        binary = client.get(item['dataUrl'])
        assert binary.status_code == 200
        assert binary.headers['cache-control'] == 'no-store'
        assert int(binary.headers['content-length']) == source[source_index].size * 4
        decoded = np.frombuffer(binary.content, dtype='<f4').reshape(5, 4)
        np.testing.assert_array_equal(decoded, source[source_index].astype(np.float32))


def test_v2_open_loads_all_channels_when_omitted(tmp_path: Path) -> None:
    path = tmp_path / 'all.tif'
    _write_cyx_tif(path)
    client = TestClient(create_app(v2_session_store=SessionStore()))
    response = client.post('/api/v2/open', json={'path': str(path.resolve())})
    assert response.status_code == 200
    assert [item['index'] for item in response.json()['channels']] == [0, 1, 2]


def test_v2_pick_and_open_success_and_cancel(tmp_path: Path) -> None:
    path = tmp_path / 'picked.tif'
    _write_cyx_tif(path)
    client = TestClient(
        create_app(
            v2_session_store=SessionStore(),
            pick_file_fn=lambda _extensions: str(path.resolve()),
        )
    )
    opened = client.post('/api/v2/pick-and-open', json={'channelIndices': [1]})
    assert opened.status_code == 200
    assert [item['index'] for item in opened.json()['channels']] == [1]

    cancelled_client = TestClient(create_app(pick_file_fn=lambda _extensions: None))
    cancelled = cancelled_client.post('/api/v2/pick-and-open', json={})
    assert cancelled.status_code == 200
    assert cancelled.json()['error'] == 'cancelled'


def test_v2_missing_session_and_channel_errors(tmp_path: Path) -> None:
    path = tmp_path / 'one.tif'
    source = np.arange(20, dtype=np.uint16).reshape(5, 4)
    tifffile.imwrite(path, source, metadata={'axes': 'YX'}, photometric='minisblack')
    client = TestClient(create_app(v2_session_store=SessionStore()))

    missing = client.get('/api/v2/sessions/missing/channels/0/data')
    assert missing.status_code == 404
    assert missing.json()['error'] == 'session_not_found'

    opened = client.post('/api/v2/open', json={'path': str(path.resolve())}).json()
    absent = client.get(f"/api/v2/sessions/{opened['sessionId']}/channels/9/data")
    assert absent.status_code == 404
    assert absent.json()['error'] == 'channel_not_found'


def test_v2_reference_channels_are_generic(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / 'reference.tif'
    source = np.arange(20, dtype=np.uint16).reshape(5, 4)
    tifffile.imwrite(path, source, metadata={'axes': 'YX'}, photometric='minisblack')
    reference = ReferenceImage(
        array=np.stack(
            [np.ones((3, 4), dtype=np.uint16), np.full((3, 4), 2, dtype=np.uint16)],
            axis=0,
        ),
        dims=('C', 'Y', 'X'),
        num_channels=2,
        line_roi=(1.0, 2.0, 3.0, 4.0),
        coord_units=(('X', 'um'), ('Y', 'um')),
        coord_scales=(('X', 0.5), ('Y', 0.25)),
        coords=(),
        scan_path=None,
    )
    monkeypatch.setattr(BaseFileLoader, 'has_reference_image', property(lambda self: True))
    monkeypatch.setattr(BaseFileLoader, 'reference_image', property(lambda self: reference))

    client = TestClient(create_app(v2_session_store=SessionStore()))
    response = client.post('/api/v2/open', json={'path': str(path.resolve())})
    assert response.status_code == 200
    payload = response.json()
    assert payload['reference']['plane']['shape'] == [3, 4]
    assert [item['index'] for item in payload['reference']['channels']] == [0, 1]
    binary = client.get(payload['reference']['channels'][1]['dataUrl'])
    decoded = np.frombuffer(binary.content, dtype='<f4').reshape(3, 4)
    np.testing.assert_array_equal(decoded, np.full((3, 4), 2, dtype=np.float32))


def test_v2_validation_and_missing_path() -> None:
    client = TestClient(create_app())
    invalid = client.post('/api/v2/open', json={'path': '/tmp/a.tif', 'calciumChannel': 0})
    assert invalid.status_code == 422
    missing = client.post('/api/v2/open', json={'path': '/tmp/missing-v2.tif'})
    assert missing.status_code == 404
    assert missing.json()['error'] == 'path_not_found'
