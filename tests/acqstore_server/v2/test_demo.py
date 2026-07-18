"""Static JavaScript demo coverage for API v2."""

from fastapi.testclient import TestClient

from acqstore_server.app import create_app
from acqstore_server.v2.demo import resolve_v2_demo_index


def test_v2_demo_file_exists_and_exercises_client_lifecycle() -> None:
    path = resolve_v2_demo_index()
    assert path is not None
    html = path.read_text(encoding='utf-8')

    assert "const API = '/api/v2'" in html
    assert '/api/v1' not in html
    assert 'calciumChannel' not in html
    assert 'vesselChannel' not in html

    required_contract_terms = (
        '`${API}/health`',
        '`${API}/capabilities`',
        '`${API}/pick-and-open`',
        '`${API}/open`',
        '`${API}/sessions/${encodeURIComponent(payload.sessionId)}`',
        "method:'DELETE'",
        'dataUrl',
        'resource.byteLength',
        'plane.shape',
        'currentSessionId',
        'sessionPre',
    )
    for term in required_contract_terms:
        assert term in html

    assert 'function transposePlane(values, shape)' in html
    assert 'const displayPlane = transposePlane(values, plane.shape)' in html
    assert 'drawPlane(canvas, displayPlane.values, displayPlane.shape)' in html
    assert 'array dimension 1 horizontally' not in html


def test_v2_demo_is_served_at_versioned_path() -> None:
    client = TestClient(create_app())
    response = client.get('/demo/v2/')
    assert response.status_code == 200
    assert 'AcqStore Server API v2 demo' in response.text
    assert response.headers['content-type'].startswith('text/html')
