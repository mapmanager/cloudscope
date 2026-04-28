"""Lightweight tests for ``header_view`` API (no NiceGUI client required)."""

from __future__ import annotations

import inspect

from cloudscope.gui.header_view import CLOUDSCOPE_GITHUB_URL, build_main_header


def test_build_main_header_signature_accepts_title() -> None:
    """Header builder stays a simple page-level hook with configurable title."""
    sig = inspect.signature(build_main_header)
    assert "title" in sig.parameters
    params = sig.parameters["title"]
    assert params.default == "CloudScope"


def test_build_main_header_is_documented_callable() -> None:
    assert callable(build_main_header)
    assert build_main_header.__doc__


def test_header_view_exposes_cloudscope_github_url() -> None:
    assert CLOUDSCOPE_GITHUB_URL == "https://github.com/mapmanager/cloudscope"
