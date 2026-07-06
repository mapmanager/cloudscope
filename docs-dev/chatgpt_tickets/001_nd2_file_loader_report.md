# 001 ND2 File Loader Report

## Files changed

- `pyproject.toml`
- `src/acqstore/acq_image/file_loaders/nd2_file_loader.py`
- `src/acqstore/acq_image/file_loaders/loader_registry.py`
- `tests/acqstore/test_nd2_file_loader.py`
- `tests/acqstore/test_file_loader_factory.py`
- `tests/acqstore/test_supported_import_extensions.py`
- `scripts/acqstore/try_nd2_file_loader.py`

## Summary of implementation

Added an acqstore backend loader for Nikon ND2 files using the `nd2` package.
The loader reads ND2 header metadata without loading pixels, exposes the ND2
axis order reported by `ND2File.sizes`, maps X/Y/Z voxel calibration into
CloudScope `ImageHeader` physical units, and lazily loads pixels through
`ND2File.asarray()`.

Version 1 supports the default acquisition position. If an ND2 file has a
position axis (`P`), the loader records `num_scenes` from the position count,
excludes `P` from the exposed image header, and loads pixels from `position=0`.
Multi-position browsing and one-AcqImage-per-position behavior are left as a
future design ticket.

The new `.nd2` extension is registered through the existing loader registry and
included in supported import extensions. No GUI code, root `README.md`, or
`__init__.py` files were modified.

A local try script was added at `scripts/acqstore/try_nd2_file_loader.py`. It has
no command-line arguments, uses a hard-coded ND2 path, loads an `AcqImage`
lazily, prints header diagnostics, explicitly loads pixels, and prints per-channel
slice diagnostics.

The uploaded `Z---dendrite5.nd2` sample was manually probed through the new
loader. It reported:

- shape: `(19, 2, 512, 512)`
- dims: `('Z', 'C', 'Y', 'X')`
- sizes: `{'Z': 19, 'C': 2, 'Y': 512, 'X': 512}`
- dtype: `uint16`
- num_channels: `2`
- num_scenes: `1`
- physical_units: `(0.25, 1.0, 0.12429611388044776, 0.12429611388044776)`
- physical_units_labels: `('um', 'Pixels', 'um', 'um')`

## Tests added or modified

- Added `tests/acqstore/test_nd2_file_loader.py`
  - header parsing without pixel load
  - lazy pixel loading
  - default-position loading for multi-position ND2 files
  - loaded shape mismatch error
  - inconsistent header shape metadata error
- Updated `tests/acqstore/test_file_loader_factory.py`
  - `.nd2` factory dispatch returns `Nd2FileLoader`
- Updated `tests/acqstore/test_supported_import_extensions.py`
  - supported extension list includes `nd2`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_nd2_file_loader.py tests/acqstore/test_file_loader_factory.py tests/acqstore/test_supported_import_extensions.py
uv run pytest
uv run ruff check src/acqstore/acq_image/file_loaders/nd2_file_loader.py tests/acqstore/test_nd2_file_loader.py tests/acqstore/test_file_loader_factory.py scripts/acqstore/try_nd2_file_loader.py
uv run pytest tests/acqstore/test_nd2_file_loader.py tests/acqstore/test_file_loader_factory.py tests/acqstore/test_supported_import_extensions.py
```

Manual uploaded-sample probe:

```bash
uv run python - <<'PY'
from acqstore.acq_image.file_loaders.nd2_file_loader import Nd2FileLoader
p='/mnt/data/nd2_sample/Z---dendrite5.nd2'
loader=Nd2FileLoader(p)
h=loader.header
print(h.shape,h.dims,h.sizes,h.dtype,h.num_channels,h.num_scenes,h.physical_units,h.physical_units_labels)
arr=loader.load_image_data()
print(arr.shape, arr.dtype, loader.get_slice_data_loaded(0,z=0).shape)
PY
```

## Test results

Focused tests before full suite:

```text
25 passed in 0.10s
```

Full suite:

```text
1771 passed, 17 skipped, 13 warnings in 26.21s
```

Ruff check:

```text
All checks passed!
```

Focused tests after lint cleanup:

```text
25 passed in 0.10s
```

Manual uploaded-sample probe:

```text
(19, 2, 512, 512) ('Z', 'C', 'Y', 'X') {'Z': 19, 'C': 2, 'Y': 512, 'X': 512} uint16 2 1 (0.25, 1.0, 0.12429611388044776, 0.12429611388044776) ('um', 'Pixels', 'um', 'um')
(19, 2, 512, 512) uint16 (512, 512)
```

## Any concerns or follow-ups

- Multi-position ND2 files are intentionally limited to position `0` in this
  implementation. A future ticket should decide whether each position becomes a
  separate `AcqImage`, a selectable scene, or an `AcqImageList` expansion.
- ND2 time-axis calibration is not implemented in this first pass. Non-spatial
  axes use existing default pixel-style calibration.
- No ND2 reference-image or ROI metadata integration was added.
