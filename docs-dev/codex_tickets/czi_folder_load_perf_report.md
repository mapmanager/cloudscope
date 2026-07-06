# CZI folder load performance report

## Files changed

- `src/acqstore/acq_image/file_loaders/czi_file_loader.py`
- `tests/acqstore/test_czi_file_loader.py`
- `docs-dev/codex_tickets/czi_folder_load_perf_report.md`

## Summary of implementation

Mirrored the OIR folder-load optimization for CZI:

1. **Single CZI open during header read** — `_read_czi_header` calls
   `_find_czi_reference_array` while the file is already open.
2. **Cached probe state** — `_has_reference_image` and
   `_cached_reference_array` are set during header read (one decode when a
   reference attachment exists).
3. **`has_reference_image` override** — file-list ✅ column uses the cached
   flag via existing `AcqImage.get_schema_row()` (`has_reference_image`).
4. **Lazy `reference_image`** — reuses `_cached_reference_array` when building
   the snapshot so reference pixels are not decoded twice.

Accurate reference detection still requires attachment decode (shape heuristic
distinguishes reference images from scan-path `Image`/`ZISRAW` attachments).

OIR loader and `czi_file_loader` shared header helpers are unchanged.

## Tests added or modified

- `tests/acqstore/test_czi_file_loader.py`
  - cached `has_reference_image` during header read
  - scan-path-only files keep `has_reference_image` false
  - `get_schema_row` does not reopen CZI
  - `reference_image` reuses cached array (`_find_czi_reference_array` not
    called again)

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_czi_file_loader.py tests/acqstore/test_oir_file_loader.py
```

## Test results

20 passed in 0.79s (`test_czi_file_loader.py` 9, `test_oir_file_loader.py` 11).

## Concerns or follow-ups

- No `.czi` fixtures in-repo for integration benchmarks; tests use mocked
  attachments.
- `reference_image` still opens CZI once more for XML scaling and scan-path
  attachment decode (unavoidable with current snapshot builder).
- Pre-injected `header=` on `CziFileLoader` skips `read_header`; reference probe
  remains unset unless `read_header` runs.
