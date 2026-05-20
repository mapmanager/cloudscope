"""Canonical identifiers for CloudScope views."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ViewId(StrEnum):
    """Stable identifiers for views managed by ``ViewManager``."""

    LEFT_TOOLBAR = "left_toolbar"
    METADATA = "metadata"
    APP_CONFIG = "app_config"
    APP_INFO = "app_info"
    VELOCITY_ANALYSIS = "velocity_analysis"
    DIAMETER_ANALYSIS = "diameter_analysis"
    ACQ_ANALYSIS_PLOT = "acq_analysis_plot"

    # main page
    LOAD_SAVE = "load_save"
    FILE_LIST = "file_list"
    IMAGE_TOOLBAR = "image_toolbar"
    PRIMARY_IMAGE = "primary_image"
    REFERENCE_IMAGE = "reference_image"
    FOOTER = "footer"
    TASK_PROGRESS_DIALOG = "task_progress_dialog"


@dataclass(frozen=True, slots=True)
class ViewDescriptor:
    """Metadata describing a CloudScope view.

    Args:
        view_id: Stable view identifier.
        label: Human-readable view label for menus and settings.
    """

    view_id: ViewId
    label: str


CONFIGURABLE_HOME_VIEWS: tuple[ViewDescriptor, ...] = (
    ViewDescriptor(ViewId.FILE_LIST, 'File list'),
    ViewDescriptor(ViewId.ACQ_ANALYSIS_PLOT, 'Analysis plot'),
    ViewDescriptor(ViewId.REFERENCE_IMAGE, 'Reference image'),
)

CONFIGURABLE_HOME_VIEW_IDS: frozenset[str] = frozenset(
    descriptor.view_id.value for descriptor in CONFIGURABLE_HOME_VIEWS
)
