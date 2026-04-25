# Ticket 001 — Add acquisition import file discovery

## Goal

Add a small, tested backend utility that discovers importable acquisition files from a path.

This ticket is intentionally limited to file type constants and path discovery. Do not implement `AcqImage` or `AcqImageList` in this ticket.

## Package Boundary

This is backend acquisition/data-model work and belongs in `src/acqstore/`.

Do not modify GUI files.

## Files to Create or Modify

Create or update:

```text
src/acqstore/__init__.py
src/acqstore/acq_image/__init__.py
src/acqstore/acq_image/file_types.py
src/acqstore/acq_image/import_paths.py
tests/test_import_paths.py
```

## Guardrails

- Do not modify `src/cloudscope/gui/`.
- Do not modify `src/cloudscope/core/controller.py`.
- Do not modify `src/cloudscope/core/event_bus.py`.
- Do not modify `src/cloudscope/core/events.py`.
- Do not modify `src/cloudscope/core/state.py`.
- Do not modify ROI files.
- Do not modify CloudScope contracts.
- Do not implement `AcqImageList`.
- Do not implement `AcqImage`.
- Keep this ticket limited to supported file type constants and path discovery.
- All public functions must be typed.
- All public functions must have Google-style docstrings.
- Add unit tests.
- Run tests with `uv run pytest`.

## Required API

In `src/acqstore/acq_image/file_types.py`:

```python
"""Supported acquisition file types."""

from typing import Literal

AllowedImportExtension = Literal["tif", "oir"]

ALLOWED_IMPORT_EXTENSIONS: tuple[AllowedImportExtension, ...] = ("tif", "oir")
```

In `src/acqstore/acq_image/import_paths.py`:

```python
def find_import_paths(path: str) -> list[str]:
    """Return absolute importable acquisition file paths for a file or folder.

    Args:
        path: File or directory path to inspect.

    Returns:
        Sorted list of absolute file paths for supported acquisition files.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If path is an unsupported file or contains no supported files.
    """
```

## Behavior Rules

- Supported extensions for v1 are `"tif"` and `"oir"`.
- Extension matching is case-insensitive.
- Returned paths are absolute strings.
- If `path` is a supported file, return a one-item list.
- If `path` is an unsupported file, raise `ValueError`.
- If `path` is a directory, scan it non-recursively.
- Directory results must be sorted.
- Directory results must include only supported files.
- If `path` does not exist, raise `FileNotFoundError`.
- If a directory contains no supported files, raise `ValueError`.

## Tests

Add `tests/test_import_paths.py` with tests for:

- single `.tif` file
- single `.oir` file
- uppercase `.TIF` file
- unsupported single file raises `ValueError`
- missing path raises `FileNotFoundError`
- directory with mixed files returns only supported files
- directory results are sorted absolute paths
- directory with no supported files raises `ValueError`

Use `tmp_path` fixtures for filesystem tests.

## Acceptance Criteria

- `uv run pytest tests/test_import_paths.py` passes.
- `uv run pytest` passes.
- No GUI files changed.
- No controller/event/state files changed.
- No ROI files changed.
- No contract files changed.

## Report Format

When finished, report:

- Files changed
- Summary of implementation
- Tests run
- Any concerns
