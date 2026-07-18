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
    assert payload['header']['dims'] == ['C', 'Y', 'X']
    assert payload['header']['sizes'] == {'C': 3, 'Y': 5, 'X': 4}
    assert payload['header']['dtype'] == 'uint16'
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
    absent = client.get(f'/api/v2/sessions/{opened["sessionId"]}/channels/9/data')
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


def test_v2_open_timeout_returns_stable_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import time

    from acqstore_server.v2.open_service import open_acquisition

    path = tmp_path / 'slow.tif'
    _write_cyx_tif(path)

    def slow_open(path_value: str, *, channel_indices: object = None) -> object:
        time.sleep(0.05)
        return open_acquisition(path_value, channel_indices=channel_indices)

    monkeypatch.setenv('ACQSTORE_SERVER_OPEN_TIMEOUT_S', '0.001')
    response = TestClient(create_app(v2_open_fn=slow_open)).post(
        '/api/v2/open',
        json={'path': str(path)},
    )
    assert response.status_code == 504
    assert response.json()['error'] == 'load_timeout'

def test_v2_negative_binary_channel_index_is_rejected() -> None:
    client = TestClient(create_app())
    response = client.get('/api/v2/sessions/example/channels/-1/data')
    assert response.status_code == 422
    assert response.json()['error'] == 'channel_out_of_range'


def test_v2_session_metadata_and_explicit_delete(tmp_path: Path) -> None:
    path = tmp_path / 'session-lifecycle.tif'
    source = _write_cyx_tif(path, shape=(2, 5, 4))
    client = TestClient(create_app(v2_session_store=SessionStore(ttl_seconds=30.0)))

    opened = client.post('/api/v2/open', json={'path': str(path.resolve())})
    assert opened.status_code == 200
    payload = opened.json()
    session_id = payload['sessionId']

    metadata = client.get(f'/api/v2/sessions/{session_id}')
    assert metadata.status_code == 200
    session = metadata.json()
    assert session['ok'] is True
    assert session['sessionId'] == session_id
    assert session['channelIndices'] == [0, 1]
    assert session['referenceChannelIndices'] == []
    assert session['totalBytes'] == source.size * 4
    assert 0 < session['ttlSecondsRemaining'] <= 30.0

    deleted = client.delete(f'/api/v2/sessions/{session_id}')
    assert deleted.status_code == 200
    assert deleted.json() == {'ok': True, 'sessionId': session_id, 'deleted': True}

    missing_metadata = client.get(f'/api/v2/sessions/{session_id}')
    assert missing_metadata.status_code == 404
    assert missing_metadata.json()['error'] == 'session_not_found'

    missing_binary = client.get(payload['channels'][0]['dataUrl'])
    assert missing_binary.status_code == 404
    assert missing_binary.json()['error'] == 'session_not_found'

    repeated_delete = client.delete(f'/api/v2/sessions/{session_id}')
    assert repeated_delete.status_code == 404
    assert repeated_delete.json()['error'] == 'session_not_found'


def test_v2_capabilities_are_sourced_from_acqstore_public_api() -> None:
    from acqstore.acq_image.supported_import_extensions import (
        get_allowed_import_extensions,
        get_supported_import_extensions,
    )

    response = TestClient(create_app(v2_session_store=SessionStore(ttl_seconds=42.0))).get('/api/v2/capabilities')

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['apiVersion'] == 'v2'
    assert payload['supportedImportExtensions'] == list(get_supported_import_extensions())
    assert payload['allowedImportExtensions'] == list(get_allowed_import_extensions())
    assert payload['binary'] == {
        'servedDtype': 'float32',
        'encoding': 'raw-f32-le',
        'layout': 'row-major',
        'mediaType': 'application/octet-stream',
    }
    assert payload['sessionTtlSeconds'] == 42.0


def test_v2_open_logs_human_readable_acquisition_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API v2 logs concise source, plane, channel, and reference details."""
    from acqstore_server.v2 import routes as v2_routes

    path = tmp_path / 'logged-reference.tif'
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
        scan_path=np.asarray([[1.0, 3.0], [2.0, 4.0]], dtype=float),
    )
    monkeypatch.setattr(BaseFileLoader, 'has_reference_image', property(lambda self: True))
    monkeypatch.setattr(BaseFileLoader, 'reference_image', property(lambda self: reference))

    messages: list[str] = []

    def capture(message: str, *args: object) -> None:
        messages.append(message % args if args else message)

    monkeypatch.setattr(v2_routes.logger, 'info', capture)

    response = TestClient(create_app(v2_session_store=SessionStore())).post(
        '/api/v2/open',
        json={'path': str(path.resolve())},
    )

    assert response.status_code == 200
    joined = '\n'.join(messages)
    assert 'Opened logged-reference.tif in ' in joined
    assert '  source format=tif dtype=uint16 channels=1' in joined
    assert "  header dims=('Y', 'X')" in joined
    assert '  header shape=(5, 4)' in joined
    assert '  plane shape=(5, 4)' in joined
    assert '  selected channels=[0]' in joined
    assert '  channel[0] name=CH1 shape=(5, 4) sourceDtype=uint16' in joined
    assert '  reference channels=2 shape=(3, 4)' in joined
    assert '  reference channel[0] shape=(3, 4) sourceDtype=uint16' in joined
    assert '  reference channel[1] shape=(3, 4) sourceDtype=uint16' in joined
    assert '  reference lineRoi=(1.0, 2.0, 3.0, 4.0)' in joined
    assert '  reference scanPath points=2' in joined
