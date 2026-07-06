# OIR folder load performance report

## Files changed

- `src/acqstore/acq_image/file_loaders/oir_file_loader.py`
- `src/acqstore/acq_image/file_loaders/base_file_loader.py`
- `src/acqstore/acq_image/acq_image.py`
- `tests/acqstore/test_oir_file_loader.py`
- `docs-dev/codex_tickets/oir_folder_load_perf_report.md`

## Summary of implementation

Folder-load slowness for OIR files came from redundant work during metadata
passes, not primary pixel loading (`load_images=False` in the GUI).

Changes:

1. **Single OIR open during header read** — `_read_oir_header` probes
   `oir.reference is not None` and caches `_has_reference_image` without
   decoding reference pixels.
2. **`has_reference_image` API** — `BaseFileLoader` default delegates to
   `reference_image`; `OirFileLoader` overrides with the cached metadata probe.
   CZI behavior is unchanged (still uses the base default).
3. **File-list schema row** — `AcqImage.get_schema_row()` uses
   `has_reference_image` so the reference ✅ column does not reopen OIR files.
4. **Skip `coords` during header** — `_physical_units_for_oir_header` only
   accesses `scene.coords` when `coord_scales` is missing for a dimension.

Full reference decode remains lazy via `OirFileLoader.reference_image`.

## Tests added or modified

- `tests/acqstore/test_oir_file_loader.py`
  - coords skipped when scales complete
  - cached `has_reference_image` without decoded snapshot
  - `get_schema_row` does not reopen OIR
  - lazy `reference_image` decode still works

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_oir_file_loader.py tests/acqstore/test_czi_file_loader.py
```

## Test results

```
uv run pytest tests/acqstore/test_oir_file_loader.py tests/acqstore/test_czi_file_loader.py -v
16 passed in 0.34s
```

## Benchmark notes

18 OIR fixtures (`tests/acqstore/data/oir-samples/`):

| Phase | Before (approx.) | After |
|-------|------------------|-------|
| `load_safe` | ~1047 ms | ~646 ms |
| `get_schema_rows` | ~442 ms | ~1 ms |
| **Total** | **~1500 ms** | **~647 ms** |

## Concerns or follow-ups

- CZI folder loads still use the base `has_reference_image` fallback (opens
  reference attachments for the ✅ column); optimize separately if needed.
- Pre-built header injection on `OirFileLoader` leaves
  `_has_reference_image=False` unless `read_header` runs.
