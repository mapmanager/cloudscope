"""Canonical identifiers for CloudScope views."""

from __future__ import annotations

from enum import StrEnum


class ViewId(StrEnum):
    """Stable identifiers for views managed by ``ViewManager``."""

    LEFT_TOOLBAR = "left_toolbar"
    METADATA = "metadata"
    APP_CONFIG = "app_config"
    VELOCITY_ANALYSIS = "velocity_analysis"

    # main page
    LOAD_SAVE = "load_save"
    FILE_LIST = "file_list"
    IMAGE_TOOLBAR = "image_toolbar"
    PRIMARY_IMAGE = "primary_image"
    FOOTER = "footer"
