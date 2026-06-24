"""Tests for the optional home-page velocity pool right drawer spike."""

from __future__ import annotations

import inspect

from cloudscope.pages import home_page
from cloudscope.views.header_view import build_main_header


def test_velocity_pool_right_drawer_flag_defaults_off() -> None:
    assert home_page.SHOW_VELOCITY_POOL_RIGHT_DRAWER is False
    assert home_page.SHOW_EMBEDDED_VELOCITY_POOL is False


def test_velocity_pool_right_drawer_width_constant() -> None:
    assert home_page.VELOCITY_POOL_RIGHT_DRAWER_WIDTH_PX == 560


def test_build_main_header_pool_drawer_toggle_defaults_to_none() -> None:
    sig = inspect.signature(build_main_header)
    assert sig.parameters["on_pool_drawer_toggle"].default is None
