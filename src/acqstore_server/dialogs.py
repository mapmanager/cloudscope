"""Native file pickers for AcqStore Server (localhost lab tool)."""

from __future__ import annotations

import platform
import subprocess
from collections.abc import Sequence
from pathlib import Path

from acqstore.acq_image.supported_import_extensions import get_supported_import_extensions
from acqstore_server.open_service import OpenServiceError


def default_extensions() -> list[str]:
    """Return dotted extensions for the file dialog filter.

    Returns:
        List like ``['.oir', '.czi', '.tif', ...]``.
    """
    return [f'.{ext}' for ext in get_supported_import_extensions()]


def normalize_extensions(extensions: Sequence[str] | None) -> list[str]:
    """Normalize optional client extension list to dotted lowercase forms.

    Args:
        extensions: Values with or without a leading dot; ``None`` uses defaults.

    Returns:
        Normalized dotted extensions.
    """
    if not extensions:
        return default_extensions()
    out: list[str] = []
    for item in extensions:
        text = str(item).strip().lower()
        if not text:
            continue
        if not text.startswith('.'):
            text = f'.{text}'
        out.append(text)
    return out or default_extensions()


def pick_acquisition_file(extensions: Sequence[str] | None = None) -> str | None:
    """Show a native open dialog and return an absolute path, or ``None`` if cancelled.

    Args:
        extensions: Optional filter list (dotted or bare). Used as a soft hint;
            some platforms cannot hard-filter proprietary types.

    Returns:
        Absolute filesystem path, or ``None`` when the user cancels.

    Raises:
        OpenServiceError: If the dialog cannot be shown.
    """
    exts = normalize_extensions(extensions)
    system = platform.system()
    if system == 'Darwin':
        return _pick_file_macos(exts)
    if system == 'Windows':
        return _pick_file_tkinter(exts)
    return _pick_file_tkinter(exts)


def _pick_file_macos(extensions: Sequence[str]) -> str | None:
    """Open macOS ``choose file`` via osascript.

    Args:
        extensions: Dotted extensions (soft filter via prompt text only).

    Returns:
        Path or ``None`` on cancel.
    """
    ext_hint = ', '.join(sorted({e.lstrip('.') for e in extensions}))
    prompt = f'Open acquisition file ({ext_hint})'
    script = f'POSIX path of (choose file with prompt { _applescript_string(prompt) })'
    try:
        completed = subprocess.run(
            ['osascript', '-e', script],
            check=False,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except FileNotFoundError as exc:
        raise OpenServiceError(
            'decode_failed',
            'osascript not found; cannot show macOS file dialog',
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise OpenServiceError('decode_failed', 'File dialog timed out') from exc

    if completed.returncode != 0:
        # User cancel typically exits non-zero with empty/stderr chatter.
        return None
    path = completed.stdout.strip()
    if not path:
        return None
    return str(Path(path).expanduser().resolve(strict=False))


def _applescript_string(value: str) -> str:
    """Quote a string for AppleScript."""
    escaped = value.replace('\\', '\\\\').replace('"', '\\"')
    return f'"{escaped}"'


def _pick_file_tkinter(extensions: Sequence[str]) -> str | None:
    """Fallback native dialog via tkinter (Windows / Linux / last resort).

    Args:
        extensions: Dotted extensions for the filetypes filter.

    Returns:
        Path or ``None`` on cancel.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:  # noqa: BLE001
        raise OpenServiceError(
            'decode_failed',
            f'tkinter file dialog unavailable: {exc}',
        ) from exc

    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes('-topmost', True)
    except Exception:  # noqa: BLE001 — best effort
        pass

    patterns = ' '.join(f'*{ext}' for ext in extensions)
    filetypes = [
        ('Acquisition files', patterns),
        ('All files', '*.*'),
    ]
    try:
        selected = filedialog.askopenfilename(title='Open acquisition file', filetypes=filetypes)
    finally:
        root.destroy()

    if not selected:
        return None
    return str(Path(selected).expanduser().resolve(strict=False))
