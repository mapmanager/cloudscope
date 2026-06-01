"""Tests for AppConfig contrast percentile and default LUT fields."""

from __future__ import annotations

import json
from pathlib import Path

from cloudscope.app_config import (
    DEFAULT_CONTRAST_AUTO_PERCENTILE_HIGH,
    DEFAULT_CONTRAST_AUTO_PERCENTILE_LOW,
    DEFAULT_FALLBACK_COLOR_LUT,
    AppConfig,
    AppConfigData,
)


def test_default_contrast_percentiles() -> None:
    data = AppConfigData()
    assert data.contrast_auto_percentile_low == DEFAULT_CONTRAST_AUTO_PERCENTILE_LOW
    assert data.contrast_auto_percentile_high == DEFAULT_CONTRAST_AUTO_PERCENTILE_HIGH


def test_default_channel_color_lut_factory() -> None:
    data = AppConfigData()
    assert data.default_channel_color_lut == {'0': 'Green', '1': 'Red', '2': 'Blue'}


def test_get_contrast_auto_percentiles_returns_floats(tmp_path: Path) -> None:
    cfg = AppConfig(path=tmp_path / 'cfg.json')
    low, high = cfg.get_contrast_auto_percentiles()
    assert isinstance(low, float)
    assert isinstance(high, float)
    assert low < high


def test_set_contrast_auto_percentiles_swaps_inverted_pair(tmp_path: Path) -> None:
    cfg = AppConfig(path=tmp_path / 'cfg.json')
    cfg.set_contrast_auto_percentiles(99.0, 1.0)
    low, high = cfg.get_contrast_auto_percentiles()
    assert (low, high) == (1.0, 99.0)


def test_set_contrast_auto_percentiles_clamps_to_range(tmp_path: Path) -> None:
    cfg = AppConfig(path=tmp_path / 'cfg.json')
    cfg.set_contrast_auto_percentiles(-5.0, 150.0)
    low, high = cfg.get_contrast_auto_percentiles()
    assert (low, high) == (0.0, 100.0)


def test_get_default_channel_color_lut_known_channel(tmp_path: Path) -> None:
    cfg = AppConfig(path=tmp_path / 'cfg.json')
    assert cfg.get_default_channel_color_lut(0) == 'Green'
    assert cfg.get_default_channel_color_lut(1) == 'Red'
    assert cfg.get_default_channel_color_lut(2) == 'Blue'


def test_get_default_channel_color_lut_unknown_channel_uses_fallback(tmp_path: Path) -> None:
    cfg = AppConfig(path=tmp_path / 'cfg.json')
    assert cfg.get_default_channel_color_lut(5) == DEFAULT_FALLBACK_COLOR_LUT


def test_set_default_channel_color_lut_updates_value(tmp_path: Path) -> None:
    cfg = AppConfig(path=tmp_path / 'cfg.json')
    cfg.set_default_channel_color_lut(3, 'Plasma')
    assert cfg.get_default_channel_color_lut(3) == 'Plasma'


def test_load_payload_with_invalid_channel_keys_falls_back_to_defaults(tmp_path: Path) -> None:
    """Unparseable channel keys are skipped; known defaults remain intact."""
    cfg_path = tmp_path / 'cfg.json'
    cfg_path.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'default_channel_color_lut': {
                    '0': 'Plasma',
                    'oops': 'Whatever',
                    '3': 'Hot',
                },
            }
        ),
        encoding='utf-8',
    )
    cfg = AppConfig.load(config_path=cfg_path)
    assert cfg.get_default_channel_color_lut(0) == 'Plasma'
    assert cfg.get_default_channel_color_lut(3) == 'Hot'
    # 'oops' was skipped; 1 and 2 keep factory defaults.
    assert cfg.get_default_channel_color_lut(1) == 'Red'
    assert cfg.get_default_channel_color_lut(2) == 'Blue'


def test_load_clamps_invalid_percentiles(tmp_path: Path) -> None:
    cfg_path = tmp_path / 'cfg.json'
    cfg_path.write_text(
        json.dumps(
            {
                'schema_version': 1,
                'contrast_auto_percentile_low': -10.0,
                'contrast_auto_percentile_high': 200.0,
            }
        ),
        encoding='utf-8',
    )
    cfg = AppConfig.load(config_path=cfg_path)
    low, high = cfg.get_contrast_auto_percentiles()
    assert (low, high) == (0.0, 100.0)


def test_round_trip_through_save_load(tmp_path: Path) -> None:
    cfg_path = tmp_path / 'cfg.json'
    cfg = AppConfig(path=cfg_path)
    cfg.set_contrast_auto_percentiles(2.5, 97.5)
    cfg.set_default_channel_color_lut(1, 'Hot')
    cfg.save()

    loaded = AppConfig.load(config_path=cfg_path)
    assert loaded.get_contrast_auto_percentiles() == (2.5, 97.5)
    assert loaded.get_default_channel_color_lut(1) == 'Hot'
