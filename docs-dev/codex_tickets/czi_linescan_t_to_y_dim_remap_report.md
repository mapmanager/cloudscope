# CZI line-scan T→Y dim remap report

## Files changed

- `src/acqstore/acq_image/file_loaders/czi_file_loader.py`
- `tests/acqstore/test_czi_file_loader.py`

## Summary of implementation

CZI line-scan kymographs can report header dims `('C', 'T', 'X')` with no `Y` axis.
CloudScope expects 2D image planes as `(Y, X)` after optional `C` / `T` / `Z` selection.

`CziFileLoader._read_czi_header()` now normalizes this CZI subset after
`_image_header_from_scene()` returns:

- When `'Y'` is missing and both `'T'` and `'X'` are present, remap the `T` axis
  label to `Y` in `dims`, move `sizes['T']` to `sizes['Y']`, and update a
  matching `'T'` entry in `physical_units_labels` when present.
- Emit `logger.warning(...)` when the remap occurs.
- Leave headers unchanged when `'Y'` is already present (e.g. `('C', 'T', 'Y', 'X')`
  frame stacks and `('C', 'Y', 'X')` 2D layouts).

Scope is CZI-only; OIR and shared `_image_header_from_scene()` are unchanged.

## Tests added or modified

Added `tests/acqstore/test_czi_file_loader.py`:

- `test_read_czi_header_remaps_linescan_t_to_y`
- `test_read_czi_header_leaves_existing_y_dims_unchanged` (parametrized for
  `('C', 'T', 'Y', 'X')` and `('C', 'Y', 'X')`)

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_czi_file_loader.py -v
```

## Test results

3 passed in 0.02s

## Concerns or follow-ups

- `CziFileLoader._physical_units_for_header()` remains unused dead code; CZI
  physical-unit extraction still uses the shared OIR-oriented helper in
  `_image_header_from_scene()`.
- No integration test against real CZI sample files in this change (samples may
  not be present in all environments).
