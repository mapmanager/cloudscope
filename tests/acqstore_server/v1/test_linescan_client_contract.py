"""Frozen HTTP contract required by neuronal linescan analyzer v1.18_b."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import tifffile
from fastapi.testclient import TestClient

from acqstore_server.app import create_app
from acqstore_server.session_store import SessionStore


def _write_cyx_tif(path: Path) -> None:
    array = np.arange(2 * 5 * 4, dtype=np.uint16).reshape(2, 5, 4)
    tifffile.imwrite(path, array, metadata={'axes': 'CYX'}, photometric='minisblack')


def test_v1_linescan_client_contract(tmp_path: Path) -> None:
    """Protect every v1 field and binary behavior consumed by the _b client."""
    path = tmp_path / 'linescan-client-contract.tif'
    _write_cyx_tif(path)
    client = TestClient(
        create_app(
            session_store=SessionStore(),
            pick_file_fn=lambda _extensions: str(path.resolve()),
        )
    )

    health = client.get('/api/v1/health')
    assert health.status_code == 200
    assert health.json()['ok'] is True

    response = client.post(
        '/api/v1/pick-and-open',
        json={'calciumChannel': 0, 'vesselChannel': 1},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload['ok'] is True
    assert isinstance(payload['sessionId'], str)
    assert payload['source']['numChannels'] == 2
    assert Path(payload['source']['path']) == path.resolve()

    calcium = payload['channels']['calcium']
    vessels = payload['channels']['vessels']
    for channel in (calcium, vessels):
        assert channel['encoding'] == 'raw-f32-le'
        assert channel['layout'] == 'row-major'
        assert isinstance(channel['height'], int)
        assert isinstance(channel['width'], int)
        assert isinstance(channel['url'], str)

        binary = client.get(channel['url'])
        assert binary.status_code == 200
        assert binary.headers['content-type'].startswith('application/octet-stream')
        assert len(binary.content) == channel['byteLength']
        assert len(binary.content) == channel['height'] * channel['width'] * 4

    calibration = payload['calibration']
    assert isinstance(calibration['msPerLine'], float)
    assert isinstance(calibration['umPerPixel'], float)
    assert 'reference' in payload
