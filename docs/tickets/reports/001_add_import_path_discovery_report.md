# Ticket 001 Report: Add Import Path Discovery

## Files Changed

- `/Users/cudmore/Sites/cloudscope/src/acqstore/__init__.py`
- `/Users/cudmore/Sites/cloudscope/src/acqstore/acq_image/__init__.py`
- `/Users/cudmore/Sites/cloudscope/src/acqstore/acq_image/import_paths.py`
- `/Users/cudmore/Sites/cloudscope/tests/test_import_paths.py`

## Summary

Implemented a backend-only import path discovery utility in `acqstore` for supported acquisition files. The new `find_import_paths(path: str) -> list[str]` API:

- accepts a file or directory path
- supports `.tif` and `.oir` extensions
- matches extensions case-insensitively
- returns absolute file paths
- scans directories non-recursively
- sorts directory results
- raises `FileNotFoundError` for missing paths
- raises `ValueError` for unsupported files or directories with no supported files

Package exports were updated to expose the new API from `acqstore` and `acqstore.acq_image`.

## Tests Added / Modified

Added:

- `/Users/cudmore/Sites/cloudscope/tests/test_import_paths.py`

Coverage added for:

- single `.tif` file
- single `.oir` file
- uppercase `.TIF` file
- unsupported single file raising `ValueError`
- missing path raising `FileNotFoundError`
- directory with mixed files returning only supported files
- directory results returning sorted absolute paths
- directory with no supported files raising `ValueError`

## Test Execution

Exact commands run:

```bash
uv run pytest tests/test_import_paths.py
uv run pytest
```

Results:

- `uv run pytest tests/test_import_paths.py`: passed (`8 passed`)
- `uv run pytest`: passed (`53 passed`)

## Concerns

- No concerns from this ticket scope.
- Assumption made: exporting `find_import_paths` from both package `__init__.py` files was appropriate because those files were explicitly listed in the ticket scope.
