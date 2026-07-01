"""Tests for shared contrast seeding helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np

from cloudscope.app_config import AppConfig
from cloudscope.contrast_seeding import ensure_channel_contrast_from_plane


def test_ensure_channel_contrast_from_plane_passes_app_config_values(tmp_path: Path) -> None:
    cfg = AppConfig(path=tmp_path / 'app_config.json')
    cfg.set_default_channel_color_lut(0, 'Green')
    cfg.set_contrast_auto_percentiles(5.0, 95.0)

    acq = MagicMock()
    plane = np.arange(4, dtype=np.uint16).reshape(2, 2)

    ensure_channel_contrast_from_plane(acq, 0, plane, cfg)

    acq.ensure_image_contrast_from_plane.assert_called_once_with(
        0,
        plane,
        default_color_lut='Green',
        percentile_low=5.0,
        percentile_high=95.0,
    )
