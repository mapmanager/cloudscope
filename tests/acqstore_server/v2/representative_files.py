"""Resolve optional local representative acquisition files for API v2 tests."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class RepresentativeFormat:
    """Configuration for one optional representative acquisition format."""

    name: str
    extension: str
    environment_variable: str


REPRESENTATIVE_FORMATS: tuple[RepresentativeFormat, ...] = (
    RepresentativeFormat('TIFF', '.tif', 'ACQSTORE_SERVER_TEST_TIF'),
    RepresentativeFormat('OIR', '.oir', 'ACQSTORE_SERVER_TEST_OIR'),
    RepresentativeFormat('CZI', '.czi', 'ACQSTORE_SERVER_TEST_CZI'),
    RepresentativeFormat('ND2', '.nd2', 'ACQSTORE_SERVER_TEST_ND2'),
)

TEST_DATA_DIR_ENV = 'ACQSTORE_SERVER_TEST_DATA_DIR'


def resolve_representative_file(spec: RepresentativeFormat) -> Path | None:
    """Return a configured representative file, or ``None`` when unavailable.

    Resolution order:

    1. The format-specific environment variable.
    2. The first case-insensitive extension match below
       ``ACQSTORE_SERVER_TEST_DATA_DIR``.

    An explicitly configured path that does not exist raises ``AssertionError``
    rather than silently skipping. This makes CI and local configuration errors
    visible.
    """
    explicit = os.getenv(spec.environment_variable)
    if explicit:
        path = Path(explicit).expanduser().resolve(strict=False)
        if not path.is_file():
            raise AssertionError(
                f'{spec.environment_variable} points to a missing file: {path}'
            )
        return path

    root_value = os.getenv(TEST_DATA_DIR_ENV)
    if not root_value:
        return None

    root = Path(root_value).expanduser().resolve(strict=False)
    if not root.is_dir():
        raise AssertionError(f'{TEST_DATA_DIR_ENV} is not a directory: {root}')

    suffix = spec.extension.casefold()
    matches = sorted(
        path
        for path in root.rglob('*')
        if path.is_file() and path.suffix.casefold() == suffix
    )
    return matches[0] if matches else None
