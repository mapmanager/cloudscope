from __future__ import annotations

from pathlib import Path
from typing import Literal

from nicegui import app

from cloudscope.core.utils.logging import get_logger

logger = get_logger(__name__)

async def _prompt_for_path(
    initial: Path,
    *,
    dialog_type: Literal["folder", "file"] = "folder",
    file_extension: str | None = None,
) -> str | None:
    """Open native folder or file picker dialog using pywebview (NiceGUI native mode).

    Fix: cooperatively blocks rect polling (and any other gated native ops)
    while the dialog is active, preventing callback collisions.

    Args:
        initial: Initial directory for the dialog.
        dialog_type: Type of dialog to open - "folder" or "file". Defaults to "folder".
        file_extension: File extension to filter for when dialog_type="file"
            (e.g., ".tif", ".csv"). Defaults to ".tif" if not provided for file dialogs.

    Returns:
        Selected path as string, or None if cancelled or error.
    """
    native = getattr(app, "native", None)
    if not native:
        logger.warning("[picker] app.native not available (not native mode?)")
        return None

    main_window = getattr(native, "main_window", None)
    if not main_window:
        logger.warning("[picker] app.native.main_window not available")
        return None

    # Initialize log_prefix for error handling
    log_prefix = "dialog"  # fallback if exception occurs before setting

    try:
        # Import webview inside function to avoid spawn/pickling issues
        import webview  # type: ignore

        # Determine dialog type and parameters
        if dialog_type == "folder":
            # pywebview 6.1+: FileDialog.FOLDER; older: FOLDER_DIALOG
            try:
                dialog_type_enum = webview.FileDialog.FOLDER  # type: ignore[attr-defined]
                logger.debug("[picker] using webview.FileDialog.FOLDER")
            except Exception:
                dialog_type_enum = webview.FOLDER_DIALOG  # type: ignore[attr-defined]
                logger.debug("[picker] using deprecated webview.FOLDER_DIALOG")
            
            dialog_params = {
                "directory": str(initial),
                "allow_multiple": False,
            }
            log_prefix = "folder"
        else:  # dialog_type == "file"
            dialog_type_enum = webview.FileDialog.OPEN  # type: ignore[attr-defined]
            
            # Normalize file extension
            if file_extension is None:
                ext = ".tif"
            else:
                ext = file_extension.strip()
                if not ext.startswith("."):
                    ext = f".{ext}"
            
            # For display name, use extension without dot, uppercase
            ext_display = ext[1:].upper()
            
            dialog_params = {
                "directory": str(initial),
                "allow_multiple": False,
                "file_types": (f"{ext_display} files (*{ext})",),
            }
            log_prefix = f"{ext_display} file"
            logger.debug(f"[picker] using webview.FileDialog.OPEN for {ext_display} file dialog")

        logger.info(f"[picker] opening {log_prefix} dialog (initial={initial})")

        selection = await main_window.create_file_dialog(  # type: ignore[attr-defined]
            dialog_type_enum,
            **dialog_params,
            )

        logger.debug(f"[picker] dialog returned: type={type(selection)} value={selection}")

        if not selection:
            logger.info("[picker] user cancelled (no selection)")
            return None

        # pywebview on macOS often returns tuple; sometimes list
        if isinstance(selection, (list, tuple)):
            first = selection[0] if selection else None
            if first is None:
                return None
            result = str(first)
            logger.info(f"[picker] selected {log_prefix}: {result}")
            return result

        result = str(selection)
        logger.info(f"[picker] selected {log_prefix}: {result}")
        return result

    except Exception as exc:
        logger.exception(f"[picker] pywebview {log_prefix} dialog failed: {exc}")
        return None


async def _prompt_for_save_path(
    initial: Path,
    *,
    suggested_filename: str = "kym_event_db.csv",
    file_extension: str = ".csv",
) -> str | None:
    """Open native save-file dialog using pywebview and return selected path.

    Args:
        initial: Initial directory for the dialog.
        suggested_filename: Default filename shown in the save dialog.
        file_extension: Extension filter for the save dialog.

    Returns:
        Selected save path as string, or None if cancelled or error.
    """
    native = getattr(app, "native", None)
    if not native:
        logger.warning("[save_picker] app.native not available (not native mode?)")
        return None

    main_window = getattr(native, "main_window", None)
    if not main_window:
        logger.warning("[save_picker] app.native.main_window not available")
        return None

    ext = file_extension.strip()
    if not ext.startswith("."):
        ext = f".{ext}"
    ext_display = ext[1:].upper()

    try:
        import webview  # type: ignore

        try:
            dialog_type_enum = webview.FileDialog.SAVE  # type: ignore[attr-defined]
        except Exception:
            dialog_type_enum = webview.SAVE_DIALOG  # type: ignore[attr-defined]
        dialog_params = {
            "directory": str(initial),
            "allow_multiple": False,
            "save_filename": suggested_filename,
            "file_types": (f"{ext_display} files (*{ext})",),
        }

        selection = await main_window.create_file_dialog(  # type: ignore[attr-defined]
            dialog_type_enum,
            **dialog_params,
        )

        if not selection:
            logger.info("[save_picker] user cancelled (no selection)")
            return None

        if isinstance(selection, (list, tuple)):
            first = selection[0] if selection else None
            if first is None:
                return None
            return str(first)
        return str(selection)
    except Exception as exc:
        logger.exception(f"[save_picker] pywebview save dialog failed: {exc}")
        return None
