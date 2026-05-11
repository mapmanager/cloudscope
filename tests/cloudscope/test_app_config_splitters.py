"""Tests for Home page splitter values stored in AppConfig."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudscope.app_config import (
    DEFAULT_HOME_ANALYSIS_REFERENCE_SPLITTER_PCT,
    DEFAULT_HOME_FILE_LIST_SPLITTER_PCT,
    DEFAULT_HOME_LEFT_TOOLBAR_OPEN_SPLITTER_PCT,
    DEFAULT_HOME_PRIMARY_IMAGE_SPLITTER_PCT,
    AppConfig,
    AppConfigData,
)


def test_app_config_defaults_include_home_splitters(tmp_path: Path) -> None:
    """Default config should expose all Home page splitter values."""
    cfg = AppConfig(path=tmp_path / 'app_config.json')

    assert cfg.get_home_splitter_value('left_toolbar') == DEFAULT_HOME_LEFT_TOOLBAR_OPEN_SPLITTER_PCT
    assert cfg.get_home_splitter_value('file_list') == DEFAULT_HOME_FILE_LIST_SPLITTER_PCT
    assert cfg.get_home_splitter_value('primary_image') == DEFAULT_HOME_PRIMARY_IMAGE_SPLITTER_PCT
    assert cfg.get_home_splitter_value('analysis_reference') == DEFAULT_HOME_ANALYSIS_REFERENCE_SPLITTER_PCT


def test_app_config_home_splitter_values_round_trip(tmp_path: Path) -> None:
    """Splitter values should persist through AppConfig JSON."""
    cfg = AppConfig(path=tmp_path / 'app_config.json')
    cfg.set_home_splitter_value('file_list', 23.5)
    cfg.set_home_splitter_value('primary_image', 70.0)
    cfg.save()

    loaded = AppConfig.load(config_path=cfg.path)

    assert loaded.get_home_splitter_value('file_list') == 23.5
    assert loaded.get_home_splitter_value('primary_image') == 70.0


def test_app_config_reset_home_splitters(tmp_path: Path) -> None:
    """Reset should restore factory splitter values without saving implicitly."""
    cfg = AppConfig(path=tmp_path / 'app_config.json')
    cfg.set_home_splitter_value('file_list', 33.0)
    cfg.set_home_splitter_value('analysis_reference', 66.0)

    cfg.reset_home_splitters()

    assert cfg.get_home_splitter_value('file_list') == DEFAULT_HOME_FILE_LIST_SPLITTER_PCT
    assert cfg.get_home_splitter_value('analysis_reference') == DEFAULT_HOME_ANALYSIS_REFERENCE_SPLITTER_PCT


def test_app_config_unknown_home_splitter_key_raises(tmp_path: Path) -> None:
    """Unknown splitter ids should fail fast."""
    cfg = AppConfig(path=tmp_path / 'app_config.json')

    with pytest.raises(KeyError):
        cfg.get_home_splitter_value('missing')

    with pytest.raises(KeyError):
        cfg.set_home_splitter_value('missing', 12.0)


def test_app_config_data_from_json_accepts_missing_splitter_fields() -> None:
    """Older config payloads should load with default splitter values."""
    data = AppConfigData.from_json_dict({'schema_version': 1})

    assert data.home_file_list_splitter_pct == DEFAULT_HOME_FILE_LIST_SPLITTER_PCT
