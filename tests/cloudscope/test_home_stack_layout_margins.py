"""Tests for Home page stack layout constants."""

from __future__ import annotations

from cloudscope.app_config import (
    HOME_STACK_MARGIN_LABELS_OFF,
    HOME_STACK_MARGIN_LABELS_ON,
    home_stack_layout_margins_profile,
)


def test_home_stack_margin_constants() -> None:
    """Home stack margins should match the agreed Pass 1 layout contract."""
    assert HOME_STACK_MARGIN_LABELS_ON == {"l": 60, "r": 24, "t": 10, "b": 40}
    assert HOME_STACK_MARGIN_LABELS_OFF == {"l": 8, "r": 8, "t": 8, "b": 8}


def test_home_stack_layout_margins_profile() -> None:
    """Home stack profile should expose fixed margins with automargin disabled."""
    profile = home_stack_layout_margins_profile()

    assert profile.resolve(show_axis_labels=True) == HOME_STACK_MARGIN_LABELS_ON
    assert profile.resolve(show_axis_labels=False) == HOME_STACK_MARGIN_LABELS_OFF
    assert profile.stabilize_axis_automargin is True
