"""Native quit confirmation dialogs for Option C desktop."""

from __future__ import annotations

import enum
import sys
from collections.abc import Callable

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)


class QuitChoice(enum.Enum):
    """User choice from the quit-with-unsaved-changes dialog."""

    SAVE = 'save'
    DISCARD = 'discard'
    CANCEL = 'cancel'


QuitDialogFn = Callable[[str, str], QuitChoice]


def ask_quit_with_unsaved_changes(
    *,
    title: str = 'Quit CloudScope',
    message: str = 'You have unsaved changes. Do you want to save them before quitting?',
    dialog_fn: QuitDialogFn | None = None,
) -> QuitChoice:
    """Show a native Save / Don't Save / Cancel quit dialog.

    Args:
        title: Dialog title text.
        message: Dialog body text.
        dialog_fn: Optional backend override for tests.

    Returns:
        Selected quit action.
    """
    backend = dialog_fn or _default_quit_dialog
    return backend(title, message)


def _default_quit_dialog(title: str, message: str) -> QuitChoice:
    """Dispatch to the platform-native quit dialog implementation.

    Args:
        title: Dialog title text.
        message: Dialog body text.

    Returns:
        Selected quit action.
    """
    platform = sys.platform
    if platform == 'darwin':
        return _ask_quit_darwin(title, message)
    if platform in {'win32', 'cygwin'}:
        return _ask_quit_win32(title, message)
    logger.warning('Unsupported platform %r for native quit dialog; cancelling quit', platform)
    return QuitChoice.CANCEL


def _ask_quit_darwin(title: str, message: str) -> QuitChoice:
    """Show a three-button quit dialog on macOS.

    Args:
        title: Dialog title text.
        message: Dialog body text.

    Returns:
        Selected quit action.
    """
    import AppKit

    AppKit.NSApplication.sharedApplication()
    AppKit.NSRunningApplication.currentApplication().activateWithOptions_(
        AppKit.NSApplicationActivateIgnoringOtherApps
    )
    alert = AppKit.NSAlert.alloc().init()
    alert.addButtonWithTitle_('Save')
    alert.addButtonWithTitle_("Don't Save")
    alert.addButtonWithTitle_('Cancel')
    alert.setMessageText_(title)
    alert.setInformativeText_(message)
    alert.setAlertStyle_(AppKit.NSWarningAlertStyle)
    result = alert.runModal()
    if result == AppKit.NSAlertFirstButtonReturn:
        return QuitChoice.SAVE
    if result == AppKit.NSAlertSecondButtonReturn:
        return QuitChoice.DISCARD
    return QuitChoice.CANCEL


def _ask_quit_win32(title: str, message: str) -> QuitChoice:
    """Show a three-button quit dialog on Windows.

    Args:
        title: Dialog title text.
        message: Dialog body text.

    Returns:
        Selected quit action.
    """
    import ctypes

    MB_YESNOCANCEL = 0x00000003
    MB_ICONWARNING = 0x00000030
    IDYES = 6
    IDNO = 7
    result = ctypes.windll.user32.MessageBoxW(0, message, title, MB_YESNOCANCEL | MB_ICONWARNING)
    if result == IDYES:
        return QuitChoice.SAVE
    if result == IDNO:
        return QuitChoice.DISCARD
    return QuitChoice.CANCEL
