"""Canonical supported acquisition import extensions (no leading dot).

These values are used for directory discovery and for :func:`create_file_loader`
validation. Extensions are compared case-insensitively on disk (``.TIF`` maps to
``tif``).
"""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_IMPORT_EXTENSIONS: tuple[str, ...] = ('tif', 'oir', 'czi')
_runtime_import_extensions: set[str] = set(DEFAULT_IMPORT_EXTENSIONS)


def _normalize_extension(extension: str) -> str:
    """Normalize one extension to canonical storage form."""
    return extension.strip().lower().lstrip('.')


def get_allowed_import_extensions() -> tuple[str, ...]:
    """Return runtime allowed import extensions in sorted order."""
    return tuple(sorted(_runtime_import_extensions))


def set_allowed_import_extensions(extensions: Iterable[str]) -> None:
    """Replace runtime allowed import extensions.

    Args:
        extensions: Iterable of extensions with or without leading dots.

    Raises:
        ValueError: If the normalized set is empty.
    """
    normalized = {
        _normalize_extension(extension)
        for extension in extensions
        if extension.strip()
    }
    if not normalized:
        raise ValueError('Allowed import extensions must not be empty')
    _runtime_import_extensions.clear()
    _runtime_import_extensions.update(normalized)


def add_allowed_import_extension(extension: str) -> None:
    """Add one runtime allowed import extension."""
    normalized = _normalize_extension(extension)
    if not normalized:
        raise ValueError('Extension must not be empty')
    _runtime_import_extensions.add(normalized)


def remove_allowed_import_extension(extension: str) -> None:
    """Remove one runtime allowed import extension.

    Raises:
        KeyError: If extension is not currently allowed.
    """
    _runtime_import_extensions.remove(_normalize_extension(extension))


def reset_allowed_import_extensions() -> None:
    """Reset runtime allowed import extensions to defaults."""
    _runtime_import_extensions.clear()
    _runtime_import_extensions.update(DEFAULT_IMPORT_EXTENSIONS)
