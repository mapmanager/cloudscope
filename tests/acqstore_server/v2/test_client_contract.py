"""Behavioral contract tests for generic API v2 clients."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile
from fastapi.testclient import TestClient

from acqstore_server.app import create_app
from acqstore_server.v2.session_store import SessionStore


def _write_multichannel_tiff(path: Path) -> np.ndarray:
    source = np.arange(3 * 7 * 5, dtype=np.uint16).reshape(3, 7, 5)
    tifffile.imwrite(path, source, metadata={'axes': 'CYX'}, photometric='minisblack')
    return source


def test_api_index_is_a_machine_and_human_discovery_entry_point() -> None:
    client = TestClient(create_app())
    response = client.get('/api/v2')

    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['apiVersion'] == 'v2'
    assert payload['links']['open'] == {
        'href': '/api/v2/open',
        'method': 'POST',
        'description': 'Open a server-visible acquisition path.',
    }
    assert payload['links']['openapi']['href'] == '/openapi.json'
    assert payload['links']['demo']['href'] == '/demo/v2/'


def test_generic_client_can_open_download_reshape_and_delete(tmp_path: Path) -> None:
    path = tmp_path / 'client-contract.tif'
    source = _write_multichannel_tiff(path)
    client = TestClient(create_app(v2_session_store=SessionStore(ttl_seconds=60.0)))

    capabilities = client.get('/api/v2/capabilities')
    assert capabilities.status_code == 200
    assert capabilities.json()['binary']['encoding'] == 'raw-f32-le'

    opened_response = client.post(
        '/api/v2/open',
        json={'path': str(path.resolve()), 'channelIndices': [2, 0]},
    )
    assert opened_response.status_code == 200
    opened = opened_response.json()

    assert opened['plane']['shape'] == [7, 5]
    assert opened['plane']['servedDtype'] == 'float32'
    assert opened['plane']['layout'] == 'row-major'
    assert [axis['arrayDimension'] for axis in opened['plane']['axes']] == [0, 1]
    assert [channel['index'] for channel in opened['channels']] == [2, 0]

    expected_bytes = 7 * 5 * np.dtype('<f4').itemsize
    for channel, source_index in zip(opened['channels'], [2, 0], strict=True):
        assert channel['byteLength'] == expected_bytes
        binary = client.get(channel['dataUrl'])
        assert binary.status_code == 200
        assert binary.headers['content-type'].startswith('application/octet-stream')
        assert binary.headers['cache-control'] == 'no-store'
        assert len(binary.content) == channel['byteLength']

        decoded = np.frombuffer(binary.content, dtype='<f4').reshape(opened['plane']['shape'])
        np.testing.assert_array_equal(decoded, source[source_index].astype(np.float32))

    session_id = opened['sessionId']
    metadata = client.get(f'/api/v2/sessions/{session_id}')
    assert metadata.status_code == 200
    assert metadata.json()['channelIndices'] == [0, 2]

    deleted = client.delete(f'/api/v2/sessions/{session_id}')
    assert deleted.status_code == 200
    assert client.get(opened['channels'][0]['dataUrl']).status_code == 404
