"""Docker/remote preset dataset paths for one-click folder loads."""

from __future__ import annotations

import os
from pathlib import Path

from acqstore.acq_image.supported_import_extensions import (
    get_allowed_import_extensions,
    normalize_import_extension_for_path,
)

PRESET_MANNING_ENV = 'CLOUDSCOPE_PRESET_DATA_MANNING'


def get_manning_preset_path() -> Path | None:
    """Return the Manning velocity preset folder when configured.

    Returns:
        Configured preset directory, or ``None`` when the env var is unset.
    """
    raw = os.getenv(PRESET_MANNING_ENV)
    if raw is None or not raw.strip():
        return None
    return Path(raw).expanduser()


def is_loadable_preset_folder(path: Path) -> bool:
    """Return whether ``path`` is a directory containing importable acquisition files.

    Args:
        path: Candidate preset directory.

    Returns:
        True when at least one allowed import file or store exists under ``path``.
    """
    if not path.is_dir():
        return False
    allowed = frozenset(get_allowed_import_extensions())
    for root, dirnames, filenames in os.walk(path):
        root_path = Path(root)
        for name in filenames:
            if normalize_import_extension_for_path(root_path / name) in allowed:
                return True
        for name in dirnames:
            if normalize_import_extension_for_path(root_path / name) in allowed:
                return True
    return False
