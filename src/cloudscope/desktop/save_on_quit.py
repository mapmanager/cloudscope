"""Synchronous save helpers for Option C desktop quit flow."""

from __future__ import annotations

from acqstore.acq_image.acq_image_list import AcqImageList

from cloudscope.runtime import get_current_runtime


def get_acq_image_list() -> AcqImageList | None:
    """Return the loaded acquisition list for the active desktop runtime.

    Returns:
        Current ``AcqImageList``, or ``None`` when no files are loaded.
    """
    runtime = get_current_runtime()
    return runtime.home_page_controller.state.acq_image_list


def has_dirty_files() -> bool:
    """Return whether any loaded acquisition file has unsaved changes.

    Returns:
        True when at least one loaded file is dirty.
    """
    acq_list = get_acq_image_list()
    if acq_list is None:
        return False
    return acq_list.has_dirty_files()


def save_all_dirty_files_sync() -> None:
    """Save all dirty files in the current ``AcqImageList``.

    Raises:
        Exception: Propagates failures from ``AcqImage.save()``.
    """
    acq_list = get_acq_image_list()
    if acq_list is None:
        return
    for acq_file in acq_list.get_dirty_files():
        acq_file.save()
