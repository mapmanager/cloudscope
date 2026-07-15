"""Tests for static path resolution."""

from __future__ import annotations

from acqstore_server.routes import resolve_demo_index, resolve_static_dir


def test_resolve_static_dir_from_source_tree() -> None:
    static_dir = resolve_static_dir()
    assert static_dir is not None
    assert (static_dir / 'demo' / 'index.html').is_file()
    assert resolve_demo_index() == static_dir / 'demo' / 'index.html'
