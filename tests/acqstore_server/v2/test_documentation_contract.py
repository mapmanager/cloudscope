"""Regression checks for the API v2 JavaScript handoff documentation."""

from __future__ import annotations

from pathlib import Path


ACQSTORE_DOCS_DIR = Path(__file__).resolve().parents[3] / "docs-dev" / "acqstore_server"
REFERENCE_DIR = ACQSTORE_DOCS_DIR / "reference"


def test_javascript_guide_covers_complete_v2_client_lifecycle() -> None:
    guide = (REFERENCE_DIR / "javascript-client.md").read_text(encoding="utf-8")

    required_contract_terms = (
        "const API = `${SERVER}/api/v2`",
        "`${API}/health`",
        "`${API}/capabilities`",
        "`${API}/pick-and-open`",
        "`${API}/open`",
        "/sessions/${encodeURIComponent(sessionId)}",
        "decodeFloat32LittleEndian",
        "DataView",
        "getFloat32(index * 4, true)",
        "resource.byteLength",
        "plane.shape[0] * plane.shape[1]",
        "transposePlane",
        "deleteSession",
        "session_not_found",
        "/demo/v2/",
    )

    for term in required_contract_terms:
        assert term in guide


def test_api_reference_links_to_authoritative_javascript_guide() -> None:
    api_reference = (REFERENCE_DIR / "api.md").read_text(encoding="utf-8")
    assert "[JavaScript client guide](javascript-client.md)" in api_reference
    assert "biological roles" not in api_reference


def test_root_docs_define_one_clear_onboarding_path() -> None:
    landing = (ACQSTORE_DOCS_DIR / "README.md").read_text(encoding="utf-8")
    roadmap = (ACQSTORE_DOCS_DIR / "client-roadmap.md").read_text(encoding="utf-8")

    assert "[Client roadmap](client-roadmap.md)" in landing
    assert "[API contract](reference/api.md)" in roadmap
    assert "[Complete JavaScript client patterns](reference/javascript-client.md)" in roadmap
    assert "http://127.0.0.1:8767" in roadmap
    assert "uv run python -m acqstore_server" in roadmap
    assert "decodeFloat32LittleEndian" in roadmap
    assert "server does **not** transpose" in roadmap
    assert "channels[].dataUrl" in roadmap
    assert '"error": "cancelled"' in roadmap
    assert "session time-to-live" in roadmap
