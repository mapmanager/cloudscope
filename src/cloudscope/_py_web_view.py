from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

from nicegui import app, run

from cloudscope.utils.logging import get_logger

logger = get_logger(__name__)


def _normalize_file_dialog_extensions(
    *,
    file_extension: str | None,
    file_extensions: Sequence[str] | None,
) -> tuple[str, ...]:
    """Return normalized dotted extensions for a native file dialog."""
    if file_extension is not None and file_extensions is not None:
        raise ValueError('Pass either file_extension or file_extensions, not both')
    raw_extensions = (
        file_extensions
        if file_extensions is not None
        else ('.tif',)
        if file_extension is None
        else (file_extension,)
    )
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_extension in raw_extensions:
        ext = raw_extension.strip()
        if not ext:
            raise ValueError('File dialog extension must not be empty')
        if not ext.startswith('.'):
            ext = f'.{ext}'
        ext = ext.lower()
        if ext in seen:
            continue
        seen.add(ext)
        normalized.append(ext)
    if not normalized:
        raise ValueError('File dialog extensions must not be empty')
    return tuple(normalized)


def _format_file_type_filter(extensions: Sequence[str], *, label: str | None) -> str:
    """Return one pywebview file-type filter for ``extensions``."""
    patterns = ';'.join(f'*{extension}' for extension in extensions)
    if label is not None:
        display = label
    elif len(extensions) == 1:
        display = f'{extensions[0][1:].upper()} files'
    else:
        display = 'Supported files'
    return f'{display} ({patterns})'


def _resolve_dialog_window() -> Any | None:
    """Return the pywebview window or NiceGUI proxy used for native file dialogs.

    Returns:
        NiceGUI ``WindowProxy`` for legacy single-window native mode, the Option C
        main pywebview window, or ``None`` when no desktop shell is active.
    """
    native = getattr(app, 'native', None)
    proxy = getattr(native, 'main_window', None) if native is not None else None
    if proxy is not None:
        return proxy
    from cloudscope.desktop_launcher import get_pool_launcher

    launcher = get_pool_launcher()
    if launcher is not None:
        return launcher.main_window
    return None


async def _create_file_dialog(
    window: Any,
    dialog_type_enum: int,
    *,
    dialog_params: dict[str, Any],
) -> Any:
    """Invoke ``create_file_dialog`` on a NiceGUI proxy or real pywebview window.

    Args:
        window: NiceGUI ``WindowProxy`` or pywebview window.
        dialog_type_enum: pywebview dialog type constant.
        dialog_params: Keyword arguments for ``create_file_dialog``.

    Returns:
        Dialog selection payload from pywebview.
    """
    native = getattr(app, 'native', None)
    if native is not None and window is native.main_window:
        return await window.create_file_dialog(  # type: ignore[attr-defined]
            dialog_type_enum,
            **dialog_params,
        )
    return await run.io_bound(
        window.create_file_dialog,
        dialog_type_enum,
        **dialog_params,
    )


async def _prompt_for_path(
    initial: Path,
    *,
    dialog_type: Literal['folder', 'file'] = 'folder',
    file_extension: str | None = None,
    file_extensions: Sequence[str] | None = None,
    file_type_label: str | None = None,
) -> str | None:
    """Open native folder or file picker dialog using pywebview.

    Args:
        initial: Initial directory for the dialog.
        dialog_type: Type of dialog to open - "folder" or "file". Defaults to "folder".
        file_extension: File extension to filter for when dialog_type="file"
            (e.g., ".tif", ".csv"). Defaults to ".tif" if not provided for file dialogs.
        file_extensions: Multiple file extensions to filter for when
            dialog_type="file". Mutually exclusive with ``file_extension``.
        file_type_label: Optional label for the pywebview file type filter.

    Returns:
        Selected path as string, or None if cancelled or error.
    """
    main_window = _resolve_dialog_window()
    if main_window is None:
        logger.warning('[picker] no pywebview dialog window available')
        return None

    log_prefix = 'dialog'

    try:
        import webview  # type: ignore

        if dialog_type == 'folder':
            try:
                dialog_type_enum = webview.FileDialog.FOLDER  # type: ignore[attr-defined]
                logger.debug('[picker] using webview.FileDialog.FOLDER')
            except Exception:
                dialog_type_enum = webview.FOLDER_DIALOG  # type: ignore[attr-defined]
                logger.debug('[picker] using deprecated webview.FOLDER_DIALOG')

            dialog_params = {
                'directory': str(initial),
                'allow_multiple': False,
            }
            log_prefix = 'folder'
        else:
            dialog_type_enum = webview.FileDialog.OPEN  # type: ignore[attr-defined]

            extensions = _normalize_file_dialog_extensions(
                file_extension=file_extension,
                file_extensions=file_extensions,
            )
            file_type_filter = _format_file_type_filter(extensions, label=file_type_label)
            ext_display = (
                file_type_label
                if file_type_label is not None
                else extensions[0][1:].upper()
                if len(extensions) == 1
                else 'supported'
            )

            dialog_params = {
                'directory': str(initial),
                'allow_multiple': False,
                'file_types': (file_type_filter,),
            }
            log_prefix = f'{ext_display} file'
            logger.debug(f'[picker] using webview.FileDialog.OPEN for {ext_display} file dialog')

        logger.info(f'[picker] opening {log_prefix} dialog (initial={initial})')

        selection = await _create_file_dialog(
            main_window,
            dialog_type_enum,
            dialog_params=dialog_params,
        )

        logger.debug(f'[picker] dialog returned: type={type(selection)} value={selection}')

        if not selection:
            logger.info('[picker] user cancelled (no selection)')
            return None

        if isinstance(selection, (list, tuple)):
            first = selection[0] if selection else None
            if first is None:
                return None
            result = str(first)
            logger.info(f'[picker] selected {log_prefix}: {result}')
            return result

        result = str(selection)
        logger.info(f'[picker] selected {log_prefix}: {result}')
        return result

    except Exception:
        logger.exception(f'[picker] pywebview {log_prefix} dialog failed')
        return None


async def _prompt_for_save_path(
    initial: Path,
    *,
    suggested_filename: str = 'kym_event_db.csv',
    file_extension: str = '.csv',
) -> str | None:
    """Open native save-file dialog using pywebview and return selected path.

    Args:
        initial: Initial directory for the dialog.
        suggested_filename: Default filename shown in the save dialog.
        file_extension: Extension filter for the save dialog.

    Returns:
        Selected save path as string, or None if cancelled or error.
    """
    main_window = _resolve_dialog_window()
    if main_window is None:
        logger.warning('[save_picker] no pywebview dialog window available')
        return None

    ext = file_extension.strip()
    if not ext.startswith('.'):
        ext = f'.{ext}'
    ext_display = ext[1:].upper()

    try:
        import webview  # type: ignore

        try:
            dialog_type_enum = webview.FileDialog.SAVE  # type: ignore[attr-defined]
        except Exception:
            dialog_type_enum = webview.SAVE_DIALOG  # type: ignore[attr-defined]
        dialog_params = {
            'directory': str(initial),
            'allow_multiple': False,
            'save_filename': suggested_filename,
            'file_types': (f'{ext_display} files (*{ext})',),
        }

        selection = await _create_file_dialog(
            main_window,
            dialog_type_enum,
            dialog_params=dialog_params,
        )

        if not selection:
            logger.info('[save_picker] user cancelled (no selection)')
            return None

        if isinstance(selection, (list, tuple)):
            first = selection[0] if selection else None
            if first is None:
                return None
            return str(first)
        return str(selection)
    except Exception:
        logger.exception('[save_picker] pywebview save dialog failed')
        return None
