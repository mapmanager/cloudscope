"""HTTP API tests for AcqStore Server v1."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import tifffile
from fastapi.testclient import TestClient

from acqstore_server.app import create_app
from acqstore_server.session_store import SessionStore


def _write_cyx_tif(path: Path) -> None:
    arr = np.arange(2 * 5 * 4, dtype=np.uint16).reshape(2, 5, 4)
    tifffile.imwrite(path, arr, metadata={'axes': 'CYX'}, photometric='minisblack')


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is True
    assert body['app'] == 'acqstore_server'
    assert body['version'] == '0.1.0'
    assert 'bind' in body


def test_open_and_fetch_channels(tmp_path: Path) -> None:
    path = tmp_path / 'api_dual.tif'
    _write_cyx_tif(path)
    client = TestClient(create_app(session_store=SessionStore()))

    opened = client.post('/api/v1/open', json={'path': str(path.resolve())})
    assert opened.status_code == 200
    payload = opened.json()
    assert payload['ok'] is True
    assert payload['source']['numChannels'] == 2
    assert 'vessels' in payload['channels']
    assert payload.get('reference') is None

    calcium_url = payload['channels']['calcium']['url']
    vessels_url = payload['channels']['vessels']['url']
    assert payload['channels']['calcium']['byteLength'] == 5 * 4 * 4

    calcium_resp = client.get(calcium_url)
    vessels_resp = client.get(vessels_url)
    assert calcium_resp.status_code == 200
    assert vessels_resp.status_code == 200
    assert calcium_resp.headers['content-type'].startswith('application/octet-stream')
    assert len(calcium_resp.content) == 5 * 4 * 4
    assert len(vessels_resp.content) == 5 * 4 * 4

    arr_c = np.frombuffer(calcium_resp.content, dtype='<f4').reshape(5, 4)
    assert arr_c.shape == (5, 4)


def test_open_missing_path() -> None:
    client = TestClient(create_app())
    response = client.post('/api/v1/open', json={'path': '/tmp/missing-acqstore-server.tif'})
    assert response.status_code == 404
    body = response.json()
    assert body['ok'] is False
    assert body['error'] == 'path_not_found'


def test_pick_and_open_cancelled(tmp_path: Path) -> None:
    client = TestClient(create_app(pick_file_fn=lambda _exts: None))
    response = client.post('/api/v1/pick-and-open', json={})
    assert response.status_code == 200
    body = response.json()
    assert body['ok'] is False
    assert body['error'] == 'cancelled'


def test_pick_and_open_success(tmp_path: Path) -> None:
    path = tmp_path / 'picked.tif'
    _write_cyx_tif(path)
    client = TestClient(
        create_app(
            session_store=SessionStore(),
            pick_file_fn=lambda _exts: str(path.resolve()),
        )
    )
    response = client.post(
        '/api/v1/pick-and-open',
        json={'calciumChannel': 0, 'vesselChannel': 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['source']['numChannels'] == 2
    assert 'vessels' in payload['channels']
    assert Path(payload['source']['path']) == path.resolve()


def test_cors_header_present() -> None:
    client = TestClient(create_app())
    response = client.options(
        '/api/v1/health',
        headers={
            'Origin': 'null',
            'Access-Control-Request-Method': 'GET',
        },
    )
    # Starlette CORS answers preflight with 200 and allow headers.
    assert response.status_code in {200, 204}
    assert response.headers.get('access-control-allow-origin') == '*'


def test_demo_page_served() -> None:
    client = TestClient(create_app())
    response = client.get('/demo/')
    assert response.status_code == 200
    assert b'AcqStore Server demo' in response.content
    assert b'pick-and-open' in response.content
    assert b'transpose' in response.content


def test_openapi_docs_available() -> None:
    client = TestClient(create_app())
    docs = client.get('/docs')
    assert docs.status_code == 200
    openapi = client.get('/openapi.json')
    assert openapi.status_code == 200
    body = openapi.json()
    assert body['info']['title'] == 'AcqStore Server'
    paths = body['paths']
    assert '/api/v1/health' in paths
    assert '/api/v1/open' in paths
    assert '/api/v1/pick-and-open' in paths
    assert '/api/v1/session/{session_id}/reference/channel/{channel}' in paths
    assert '/api/v1/session/{session_id}/reference/plane' not in paths


def test_reference_channel_endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from acqstore.acq_image.file_loaders.base_file_loader import BaseFileLoader, ReferenceImage

    path = tmp_path / 'ref_api.tif'
    arr = np.arange(10 * 6, dtype=np.uint16).reshape(10, 6)
    tifffile.imwrite(path, arr, metadata={'axes': 'YX'}, photometric='minisblack')

    reference = ReferenceImage(
        array=np.ones((4, 5), dtype=np.float32),
        dims=('Y', 'X'),
        num_channels=1,
        line_roi=None,
        coord_units=(('X', 'Pixels'), ('Y', 'Pixels')),
        coord_scales=(('X', 1.0), ('Y', 1.0)),
        coords=(),
        scan_path=None,
    )
    monkeypatch.setattr(BaseFileLoader, 'has_reference_image', property(lambda self: True))
    monkeypatch.setattr(BaseFileLoader, 'reference_image', property(lambda self: reference))

    client = TestClient(create_app(session_store=SessionStore()))
    opened = client.post('/api/v1/open', json={'path': str(path.resolve())})
    assert opened.status_code == 200
    payload = opened.json()
    assert payload['reference'] is not None
    assert payload['reference']['numChannels'] == 1
    assert 'url' not in payload['reference']
    assert len(payload['reference']['channels']) == 1
    ch0_url = payload['reference']['channels'][0]['url']
    assert ch0_url.endswith('/reference/channel/0')
    ch0 = client.get(ch0_url)
    assert ch0.status_code == 200
    assert len(ch0.content) == 4 * 5 * 4
    # Removed alias route must 404.
    sid = payload['sessionId']
    assert client.get(f'/api/v1/session/{sid}/reference/plane').status_code == 404


def test_open_load_timeout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Soft open timeout returns load_timeout without hanging the event loop."""
    import time

    import acqstore_server.routes as routes_mod

    path = tmp_path / 'slow.tif'
    _write_cyx_tif(path)

    def _slow_open(*_args: object, **_kwargs: object) -> dict[str, object]:
        time.sleep(0.35)
        return {'ok': True}

    monkeypatch.setenv('ACQSTORE_SERVER_OPEN_TIMEOUT_S', '0.05')
    monkeypatch.setattr(routes_mod, 'open_path', _slow_open)

    client = TestClient(create_app(session_store=SessionStore()))
    response = client.post('/api/v1/open', json={'path': str(path.resolve())})
    assert response.status_code == 504
    body = response.json()
    assert body['ok'] is False
    assert body['error'] == 'load_timeout'


def test_reference_multi_channel_endpoints(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from acqstore.acq_image.file_loaders.base_file_loader import BaseFileLoader, ReferenceImage

    path = tmp_path / 'ref_multi_api.tif'
    arr = np.arange(10 * 6, dtype=np.uint16).reshape(10, 6)
    tifffile.imwrite(path, arr, metadata={'axes': 'YX'}, photometric='minisblack')

    ch0 = np.ones((3, 4), dtype=np.float32)
    ch1 = np.full((3, 4), 2.0, dtype=np.float32)
    reference = ReferenceImage(
        array=np.stack([ch0, ch1], axis=0),
        dims=('C', 'Y', 'X'),
        num_channels=2,
        line_roi=None,
        coord_units=(('X', 'Pixels'), ('Y', 'Pixels')),
        coord_scales=(('X', 1.0), ('Y', 1.0)),
        coords=(),
        scan_path=None,
    )
    monkeypatch.setattr(BaseFileLoader, 'has_reference_image', property(lambda self: True))
    monkeypatch.setattr(BaseFileLoader, 'reference_image', property(lambda self: reference))

    client = TestClient(create_app(session_store=SessionStore()))
    opened = client.post('/api/v1/open', json={'path': str(path.resolve())})
    payload = opened.json()
    assert payload['reference']['numChannels'] == 2
    urls = [c['url'] for c in payload['reference']['channels']]
    r0 = client.get(urls[0])
    r1 = client.get(urls[1])
    assert r0.status_code == 200 and r1.status_code == 200
    a0 = np.frombuffer(r0.content, dtype='<f4').reshape(3, 4)
    a1 = np.frombuffer(r1.content, dtype='<f4').reshape(3, 4)
    np.testing.assert_allclose(a0, 1.0)
    np.testing.assert_allclose(a1, 2.0)
