"""Tests for CloudScope build-info runtime fallback."""

from __future__ import annotations

import sys
from importlib import metadata

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


def test_get_build_info_uses_live_python_and_nicegui(
    monkeypatch,
) -> None:
    """Python/NiceGUI should ignore host stamp values and use the live process.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.
    """
    monkeypatch.setattr(
        'cloudscope.build_info._load_generated_build_info',
        lambda: {
            'app_name': 'CloudScope',
            'version': '9.9.9',
            'git_tag': None,
            'git_commit': 'abc123',
            'git_commit_short': 'abc123',
            'git_branch': 'main',
            'git_state': 'clean',
            'build_timestamp_utc': '2026-01-01T00:00:00Z',
            'build_timestamp_local': '2026-01-01T00:00:00+0000',
            'build_bundle_version': '9.9.9',
            'python_version': '3.10.12',
            'nicegui_version': 'unknown',
            'pyinstaller_version': 'n/a',
            'platform': 'host-stamp-platform',
        },
    )

    info = get_build_info()
    assert info.version == '9.9.9'
    assert info.git_commit == 'abc123'
    assert info.python_version == sys.version.split()[0]
    assert info.python_version != '3.10.12'
    assert info.nicegui_version == metadata.version('nicegui')
    assert info.nicegui_version != 'unknown'
    assert info.pyinstaller_version == 'n/a'
    assert info.platform == 'host-stamp-platform'
