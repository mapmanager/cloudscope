"""Canonical supported acquisition import extensions (no leading dot).

These values are used for directory discovery and for :func:`create_file_loader`
validation. Extensions are compared case-insensitively on disk. Directory-backed
Zarr stores use compound suffixes such as ``ome.zarr`` and ``cs.ome.zarr``.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

DEFAULT_IMPORT_EXTENSIONS: tuple[str, ...] = ('tif', 'oir', 'czi', 'ome.zarr', 'cs.ome.zarr')
_runtime_import_extensions: set[str] = set(DEFAULT_IMPORT_EXTENSIONS)
_COMPOUND_ZARR_EXTENSIONS = ('cs.ome.zarr', 'ome.zarr')


def _normalize_extension(extension: str) -> str:
    """Normalize one extension to canonical storage form."""
    return extension.strip().lower().lstrip('.')


def normalize_import_extension_for_path(path: str | Path) -> str:
    """Return the supported import extension represented by ``path``.

    ``Path.suffix`` only reports ``.zarr`` for OME-Zarr directory stores, so
    acqstore uses this helper wherever extension checks need to recognize
    compound store names.
    """
    name = Path(path).name.lower()
    for compound in _COMPOUND_ZARR_EXTENSIONS:
        if name.endswith(f'.{compound}'):
            return compound
    return Path(name).suffix.lower().lstrip('.')


def path_has_allowed_import_extension(path: str | Path) -> bool:
    """Return whether ``path`` uses one of the currently allowed import extensions."""
    return normalize_import_extension_for_path(path) in _runtime_import_extensions


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
