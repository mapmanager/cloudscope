"""Operating-system file-manager helpers."""

from __future__ import annotations

import os
import platform
import subprocess
from pathlib import Path


def reveal_in_file_manager(path: str | os.PathLike[str]) -> None:
    """Reveal a file-system path in the platform file manager.

    macOS reveals and selects the item in Finder. Windows reveals and selects
    the item in Explorer. Linux opens the containing folder because item
    selection support varies across desktop environments.

    Args:
        path: File or folder path to reveal.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
    """
    resolved_path = Path(path).expanduser().resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(str(resolved_path))

    system = platform.system()
    if system == "Darwin":
        subprocess.run(["open", "-R", str(resolved_path)], check=False)
        return

    if system == "Windows":
        subprocess.run(["explorer", f'/select,"{resolved_path}"'], check=False, shell=True)
        return

    folder = resolved_path if resolved_path.is_dir() else resolved_path.parent
    subprocess.run(["xdg-open", str(folder)], check=False)
