"""Tests for AppInfoView log controls."""

from __future__ import annotations

import pytest

from cloudscope.views.app_info_view import AppInfoView


@pytest.mark.parametrize(
    ('remote_value', 'expected'),
    [
        (None, True),
        ('0', True),
        ('false', True),
        ('1', False),
        ('true', False),
        ('yes', False),
        ('on', False),
    ],
)
def test_can_open_log_file_respects_cloudscope_remote(
    monkeypatch: pytest.MonkeyPatch,
    remote_value: str | None,
    expected: bool,
) -> None:
    """Open Logs should be disabled only for remote/server deployments."""
    if remote_value is None:
        monkeypatch.delenv('CLOUDSCOPE_REMOTE', raising=False)
    else:
        monkeypatch.setenv('CLOUDSCOPE_REMOTE', remote_value)

    assert AppInfoView._can_open_log_file() is expected
