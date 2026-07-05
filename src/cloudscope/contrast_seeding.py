"""Shared contrast seeding helpers for CloudScope raster views."""

from __future__ import annotations

import numpy as np

from acqstore.acq_image.acq_image import AcqImage
from acqstore.acq_image.image_contrast import ImageContrast, contrast_clip_min_max
from cloudscope.app_config import AppConfig


def contrast_auto_percentiles(app_config: AppConfig | None) -> tuple[float, float]:
    """Return configured auto-contrast percentile bounds.

    Args:
        app_config: Shared application config, or ``None`` for factory defaults.

    Returns:
        ``(percentile_low, percentile_high)`` in ``[0, 100]``.
    """
    if app_config is None:
        return 1.0, 99.5
    return app_config.get_contrast_auto_percentiles()


def default_channel_color_lut(app_config: AppConfig | None, channel: int) -> str:
    """Return the default LUT identifier for one channel.

    Args:
        app_config: Shared application config, or ``None`` for gray fallback.
        channel: Zero-based channel index.

    Returns:
        LUT identifier string.
    """
    if app_config is None:
        return 'Gray'
    return app_config.get_default_channel_color_lut(int(channel))


def ephemeral_auto_contrast_from_plane(
    plane: np.ndarray,
    app_config: AppConfig | None,
) -> tuple[int, int]:
    """Return ephemeral auto ``(value_min, value_max)`` for one display plane.

    Does not read or write :class:`AcqImage` contrast state.

    Args:
        plane: 2D ``(Y, X)`` display plane.
        app_config: Shared application config for percentile defaults.

    Returns:
        Integer intensity window derived from ``plane`` histogram percentiles.
    """
    percentile_low, percentile_high = contrast_auto_percentiles(app_config)
    return contrast_clip_min_max(
        plane,
        percentile_low=percentile_low,
        percentile_high=percentile_high,
    )


def ensure_channel_contrast_from_plane(
    acq_image: AcqImage,
    channel: int,
    plane: np.ndarray,
    app_config: AppConfig | None,
) -> ImageContrast:
    """Seed or return stored contrast for one channel from a decoded plane.

    Args:
        acq_image: Acquisition image owning contrast state.
        channel: Zero-based channel index.
        plane: 2D display plane used for seeding when contrast is missing.
        app_config: Shared application config for LUT and percentile defaults.

    Returns:
        Stored or newly seeded :class:`ImageContrast` for ``channel``.
    """
    percentile_low, percentile_high = contrast_auto_percentiles(app_config)
    return acq_image.ensure_image_contrast_from_plane(
        int(channel),
        plane,
        default_color_lut=default_channel_color_lut(app_config, channel),
        percentile_low=percentile_low,
        percentile_high=percentile_high,
    )
