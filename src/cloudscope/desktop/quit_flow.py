"""Option C main-window quit orchestration."""

from __future__ import annotations

from collections.abc import Callable

from cloudscope.desktop.quit_dialog import QuitChoice, ask_quit_with_unsaved_changes
from cloudscope.desktop.save_on_quit import has_dirty_files, save_all_dirty_files_sync
from cloudscope.window_geometry import WindowGeometryTracker


def handle_main_window_closing(
    geometry_tracker: WindowGeometryTracker,
    *,
    has_dirty: Callable[[], bool] = has_dirty_files,
    ask_quit: Callable[[], QuitChoice] = ask_quit_with_unsaved_changes,
    save_dirty: Callable[[], None] = save_all_dirty_files_sync,
) -> bool:
    """Handle pywebview ``closing`` for the main Option C window.

    When quit is allowed, sync live window geometry into memory and flush
    ``AppConfig`` to disk. Move/resize handlers update memory only during the
    session; this is the intentional disk persist point.

    Args:
        geometry_tracker: Main-window geometry tracker.
        has_dirty: Callable that reports whether any loaded file is dirty.
        ask_quit: Callable that prompts the user when dirty files exist.
        save_dirty: Callable that saves all dirty files synchronously.

    Returns:
        ``False`` to veto window close, otherwise ``True``.
    """
    if has_dirty():
        choice = ask_quit()
        if choice is QuitChoice.CANCEL:
            return False
        if choice is QuitChoice.SAVE:
            save_dirty()
    geometry_tracker.sync_from_window()
    geometry_tracker.persist()
    return True
