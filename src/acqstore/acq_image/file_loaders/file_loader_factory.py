"""Factory for concrete :class:`BaseFileLoader` instances by file path."""

from __future__ import annotations

from pathlib import Path

from acqstore.acq_image.supported_import_extensions import get_allowed_import_extensions

from .base_file_loader import BaseFileLoader
from .czi_file_loader import CziFileLoader
from .oir_file_loader import OirFileLoader
from .tiff_file_loader import TiffFileLoader


def create_file_loader(path: str) -> BaseFileLoader:
    """Return a file loader appropriate for ``path``.

    Only extensions listed in :func:`get_allowed_import_extensions` are supported.
    Comparison is case-insensitive (``.TIF`` is treated as ``tif``). The ``.tiff``
    suffix is not supported.

    Args:
        path: Filesystem path to an acquisition file.

    Returns:
        A concrete loader instance.

    Raises:
        ValueError: If the path suffix is not a supported acquisition extension.
    """
    suffix = Path(path).suffix.lower().lstrip('.')
    allowed = set(get_allowed_import_extensions())
    if suffix not in allowed:
        allowed_text = ', '.join(sorted(allowed))
        raise ValueError(
            f'Unsupported acquisition file extension {suffix!r}; expected one of: {allowed_text}'
        )
    if suffix == 'tif':
        return TiffFileLoader(path, load_olympus_header=True)
    if suffix == 'oir':
        return OirFileLoader(path)
    if suffix == 'czi':
        return CziFileLoader(path)
    raise ValueError(f'No loader registered for extension {suffix!r}')
