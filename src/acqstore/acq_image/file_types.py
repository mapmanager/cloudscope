"""Supported acquisition file types."""

from typing import Literal

AllowedImportExtension = Literal["tif", "oir"]

ALLOWED_IMPORT_EXTENSIONS: tuple[AllowedImportExtension, ...] = ("tif", "oir")
