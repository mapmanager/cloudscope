"""Tests for the optional home-page right velocity pool splitter panel."""

from __future__ import annotations

from cloudscope.pages import home_page


def test_velocity_pool_right_panel_flag_defaults_on() -> None:
    assert home_page.SHOW_VELOCITY_POOL_RIGHT_PANEL is True
    assert home_page.SHOW_EMBEDDED_VELOCITY_POOL is False
