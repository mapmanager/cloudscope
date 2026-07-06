# 001 — Olympus split-channel TIFF merge

## Files changed

- `src/acqstore/acq_image/file_loaders/tiff_file_loader.py`
- `tests/acqstore/test_tiff_file_loader.py`
- `docs-dev/codex_tickets/001_olympus_split_channel_tiff_report.md`

## Summary of implementation

Olympus kymograph exports that store each channel in a separate `_C001T…` /
`_C002T…` TIFF sibling (with a shared `.txt` sidecar) are now loaded as one
logical `(C, Y, X)` volume by `TiffFileLoader`.

Discovery reuses existing `read_olympus_txt_dict` output (`tifChannelPaths`).
When every expected sibling path exists, the loader:

1. Stores ordered channel paths on the instance.
2. Upgrades the Olympus header to `dims=("C", "Y", "X")` and
   `shape=(num_channels, Y, X)`.
3. Loads each sibling with `tifffile.imread` and `np.stack`s them on first
   pixel load.

Opening either `…_C001T001.tif` or `…_C002T001.tif` yields the same merged
volume. Single-channel Olympus kymographs remain `(Y, X)`.

**Deferred (follow-up ticket):** when the sidecar reports multiple channels but
one or more sibling TIFFs are missing or the filename pattern does not resolve,
behavior is unchanged from before (header may report `num_channels > 1` with
`(Y, X)` dims). Policy for strict fail vs single-channel degrade is not decided
in this ticket.

## Tests added or modified

- `test_tiff_loader_olympus_split_channels_merge_from_c001`
- `test_tiff_loader_olympus_split_channels_merge_from_c002`
- `test_tiff_loader_single_channel_olympus_sidecar_unchanged`
- Helpers: `_write_minimal_olympus_txt`, `_write_olympus_split_channel_fixture`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_tiff_file_loader.py -q
uv run pytest tests/acqstore/test_read_olympus_txt.py -q
uv run pytest tests/acqstore/ -q
```

Manual verification on local data:

```bash
uv run python -c "
from acqstore.acq_image.file_loaders.tiff_file_loader import TiffFileLoader
p = '.../cell 05_C001T001.tif'
loader = TiffFileLoader(p)
loader.load_image_data()
loader.get_slice_data(0)
loader.get_slice_data(1)
"
```

## Test results

- `tests/acqstore/test_tiff_file_loader.py`: 11 passed
- `tests/acqstore/test_read_olympus_txt.py`: unchanged, passed with suite
- Full `tests/acqstore/`: passed
- Manual `cell 05_C001T001.tif`: `dims ('C', 'Y', 'X')`, `shape (2, 1000, 443)`,
  both channel slices load

## Concerns or follow-ups

- **Incomplete sibling pairs:** decide strict fail vs degrade to single-channel
  when `numChannels > 1` but `tifChannelPaths` contains `None`.
- **AcqImageList duplication:** folder listing still shows both `_C001` and
  `_C002` files as separate entries.
- **Filename patterns:** sibling discovery requires `_C001T` / `_C002T` /
  `_C003T` in the basename; other Olympus naming schemes need explicit support.
- **Pre-built headers:** callers passing `header=` without re-parsing Olympus
  sidecars do not get merge behavior.
