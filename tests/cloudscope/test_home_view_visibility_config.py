"""Tests for configurable Home page view visibility."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudscope.app_config import AppConfig, AppConfigData
from cloudscope.views.view_ids import CONFIGURABLE_HOME_VIEWS, ViewId


def test_configurable_home_views_include_initial_main_views() -> None:
    """Configurable Home page view registry should include the first supported views."""
    view_ids = tuple(descriptor.view_id for descriptor in CONFIGURABLE_HOME_VIEWS)

    assert view_ids == (
        ViewId.FILE_LIST,
        ViewId.ACQ_ANALYSIS_PLOT,
        ViewId.REFERENCE_IMAGE,
    )


def test_app_config_home_view_visibility_defaults_true(tmp_path: Path) -> None:
    """Default app config should show every configurable Home page view."""
    config = AppConfig(path=tmp_path / 'app_config.json')

    for descriptor in CONFIGURABLE_HOME_VIEWS:
        assert config.is_home_view_visible(descriptor.view_id.value) is True


def test_app_config_home_view_visibility_round_trip(tmp_path: Path) -> None:
    """Home page view visibility should persist through JSON save/load."""
    path = tmp_path / 'app_config.json'
    config = AppConfig(path=path)
    config.set_home_view_visible(ViewId.ACQ_ANALYSIS_PLOT.value, False)
    config.save()

    loaded = AppConfig.load(config_path=path, reset_on_version_mismatch=False)

    assert loaded.is_home_view_visible(ViewId.FILE_LIST.value) is True
    assert loaded.is_home_view_visible(ViewId.ACQ_ANALYSIS_PLOT.value) is False
    assert loaded.is_home_view_visible(ViewId.REFERENCE_IMAGE.value) is True


def test_app_config_home_view_visibility_ignores_unknown_keys() -> None:
    """Unknown persisted view-visibility keys should be ignored without schema bump."""
    data = AppConfigData.from_json_dict(
        {
            'schema_version': 1,
            'home_view_visible': {
                ViewId.FILE_LIST.value: False,
                'future_view': False,
            },
        }
    )

    assert data.home_view_visible == {
        ViewId.FILE_LIST.value: False,
        ViewId.ACQ_ANALYSIS_PLOT.value: True,
        ViewId.REFERENCE_IMAGE.value: True,
    }


def test_app_config_rejects_setting_non_configurable_home_view(tmp_path: Path) -> None:
    """Only registered configurable Home page views can be set explicitly."""
    config = AppConfig(path=tmp_path / 'app_config.json')

    with pytest.raises(KeyError):
        config.set_home_view_visible(ViewId.PRIMARY_IMAGE.value, False)
