"""Tests for CloudScope build-info runtime fallback."""

from __future__ import annotations

from cloudscope.build_info import BuildInfo, get_build_info, get_build_info_rows


def test_get_build_info_returns_build_info() -> None:
    """Build-info API should always return a BuildInfo object.

    Returns:
        None.
    """
    info = get_build_info()
    assert isinstance(info, BuildInfo)
    assert info.app_name == 'CloudScope'
    assert info.version


def test_get_build_info_rows_include_version_and_git_commit() -> None:
    """Display rows should include common release identity fields.

    Returns:
        None.
    """
    rows = dict(get_build_info_rows())
    assert rows['App'] == 'CloudScope'
    assert rows['Version']
    assert 'Git commit' in rows
    assert 'Built UTC' in rows
