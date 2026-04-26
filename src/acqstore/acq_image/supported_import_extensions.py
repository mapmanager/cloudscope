"""Canonical supported acquisition import extensions (no leading dot).

These values are used for directory discovery and for :func:`create_file_loader`
validation. Extensions are compared case-insensitively on disk (``.TIF`` maps to
``tif``).
"""

from __future__ import annotations

from typing import Literal

AllowedImportExtension = Literal['tif', 'oir', 'czi']
ALLOWED_IMPORT_EXTENSIONS: tuple[AllowedImportExtension, ...] = ('tif', 'oir', 'czi')
