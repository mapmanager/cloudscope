# Ticket Report: 005 Runtime Import Extensions Configuration

## Files changed

- `src/acqstore/acq_image/supported_import_extensions.py`
- `src/acqstore/acq_image/file_loaders/file_loader_factory.py`
- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/acq_image_list.py`
- `tests/acqstore/conftest.py`
- `tests/acqstore/test_file_loader_factory.py`
- `tests/acqstore/test_supported_import_extensions.py`

## Summary of implementation

- Replaced static `Literal`-based extension constants with a small process-wide runtime API:
  - `get_allowed_import_extensions()`
  - `set_allowed_import_extensions()`
  - `add_allowed_import_extension()`
  - `remove_allowed_import_extension()`
  - `reset_allowed_import_extensions()`
- Kept `DEFAULT_IMPORT_EXTENSIONS` as immutable defaults.
- Updated factory and list discovery to read allowed extensions via the runtime getter.
- Updated `acq_image` re-exports to expose the runtime extension API.

## Tests added or modified

- Added `tests/acqstore/conftest.py` with an autouse reset fixture to prevent test cross-contamination.
- Updated `tests/acqstore/test_file_loader_factory.py` with runtime mutation behavior checks.
- Added `tests/acqstore/test_supported_import_extensions.py` for runtime API behavior and normalization.

## Exact test commands run

- `uv run pytest`

## Test results

- `72 passed` using `uv run pytest`.

## Concerns or follow-ups

- Runtime extension mutation is process-wide state by design; callers should reset after temporary changes in scripts or long-running sessions.
