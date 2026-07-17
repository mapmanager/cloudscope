"""Optional behavioral API tests against representative microscopy files."""

from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from acqstore_server.app import create_app
from acqstore_server.v2.session_store import SessionStore
from tests.acqstore_server.v2.representative_files import (
    REPRESENTATIVE_FORMATS,
    RepresentativeFormat,
    resolve_representative_file,
)


@pytest.mark.parametrize('spec', REPRESENTATIVE_FORMATS, ids=lambda spec: spec.name.lower())
def test_representative_file_api_contract(spec: RepresentativeFormat) -> None:
    """Open, download, decode, inspect, and delete one real acquisition session."""
    path = resolve_representative_file(spec)
    if path is None:
        pytest.skip(
            f'No representative {spec.name} file configured; set '
            f'{spec.environment_variable} or ACQSTORE_SERVER_TEST_DATA_DIR'
        )

    client = TestClient(create_app(v2_session_store=SessionStore(ttl_seconds=60.0)))
    response = client.post(
        '/api/v2/open',
        json={'path': str(path), 'channelIndices': [0]},
    )
    if response.status_code != 200:
        pytest.fail(
            f'API error while opening representative {spec.name} file {path}: '
            f'HTTP {response.status_code} {response.text}'
        )

    payload = response.json()
    assert payload['ok'] is True
    assert payload['source']['path'] == str(path)
    assert payload['source']['name'] == path.name
    assert payload['source']['format'].casefold() == spec.extension.lstrip('.').casefold()
    assert payload['source']['numChannels'] >= 1
    assert payload['source']['sourceDtype']

    shape = tuple(payload['plane']['shape'])
    assert len(shape) == 2
    assert all(size > 0 for size in shape)
    assert payload['plane']['servedDtype'] == 'float32'
    assert payload['plane']['encoding'] == 'raw-f32-le'
    assert payload['plane']['layout'] == 'row-major'

    axes = payload['plane']['axes']
    assert [axis['arrayDimension'] for axis in axes] == [0, 1]
    assert [axis['name'] for axis in axes] == ['Y', 'X']
    assert [axis['size'] for axis in axes] == list(shape)
    assert all(axis['step'] > 0 for axis in axes)
    assert all(axis['unit'].strip() for axis in axes)

    assert len(payload['channels']) == 1
    channel = payload['channels'][0]
    assert channel['index'] == 0
    expected_bytes = int(np.prod(shape)) * np.dtype('<f4').itemsize
    assert channel['byteLength'] == expected_bytes

    binary = client.get(channel['dataUrl'])
    assert binary.status_code == 200
    assert binary.headers['content-type'].startswith('application/octet-stream')
    assert binary.headers['cache-control'] == 'no-store'
    assert len(binary.content) == expected_bytes

    decoded = np.frombuffer(binary.content, dtype='<f4')
    assert decoded.size == int(np.prod(shape))
    assert decoded.reshape(shape).shape == shape

    session_id = payload['sessionId']
    metadata = client.get(f'/api/v2/sessions/{session_id}')
    assert metadata.status_code == 200
    assert metadata.json()['channelIndices'] == [0]
    assert metadata.json()['totalBytes'] >= expected_bytes

    deleted = client.delete(f'/api/v2/sessions/{session_id}')
    assert deleted.status_code == 200
    assert deleted.json()['deleted'] is True
    assert client.get(channel['dataUrl']).status_code == 404
