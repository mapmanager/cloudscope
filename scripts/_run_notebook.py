"""Execute a notebook in place, tolerating legacy non-conformant outputs.

Usage:
    uv run --with jupyter --with ipykernel python scripts/_run_notebook.py <nb.ipynb> [<nb.ipynb> ...]

This is a throwaway docs helper (not shipped, not imported by the package). It
reads each notebook leniently, normalizes it, runs all cells, and writes valid
nbformat back so mkdocs-jupyter can render fresh outputs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def run(path: Path) -> None:
    nb = nbformat.read(path, as_version=4)
    nbformat.validator.normalize(nb)
    client = NotebookClient(
        nb,
        timeout=600,
        kernel_name="python3",
        resources={"metadata": {"path": str(path.parent)}},
    )
    client.execute()
    nbformat.write(nb, path)
    print(f"executed: {path}")


def main() -> None:
    for arg in sys.argv[1:]:
        run(Path(arg))


if __name__ == "__main__":
    main()
