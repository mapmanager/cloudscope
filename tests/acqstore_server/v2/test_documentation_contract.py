"""Regression checks for the API v2 JavaScript handoff documentation."""

from __future__ import annotations

from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parents[3] / 'docs-dev' / 'acqstore_server' / 'v2'


def test_javascript_guide_covers_complete_v2_client_lifecycle() -> None:
    guide = (DOCS_DIR / 'javascript-client.md').read_text(encoding='utf-8')

    required_contract_terms = (
        "const API = `${SERVER}/api/v2`",
        '`${API}/health`',
        '`${API}/capabilities`',
        '`${API}/pick-and-open`',
        '`${API}/open`',
        '/sessions/${encodeURIComponent(sessionId)}',
        'decodeFloat32LittleEndian',
        'DataView',
        'getFloat32(index * 4, true)',
        'resource.byteLength',
        'plane.shape[0] * plane.shape[1]',
        'transposePlane',
        'deleteSession',
        'session_not_found',
        '/demo/v2/',
    )

    for term in required_contract_terms:
        assert term in guide


def test_api_reference_links_to_authoritative_javascript_guide() -> None:
    api_reference = (DOCS_DIR / 'api.md').read_text(encoding='utf-8')
    assert '[JavaScript client guide](javascript-client.md)' in api_reference
    assert 'biological roles' not in api_reference
