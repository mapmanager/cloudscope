# `acqstore` — acquisition backend

Python package for **acquisition-backed files**: discovery, loading, ROI models, metadata, and schema-backed list APIs. It does **not** depend on NiceGUI or CloudScope UI code.

## Layout (high level)

| Area | Module path (examples) |
|------|-------------------------|
| File list / discovery | `acqstore.acq_image.acq_image_list` (`AcqImageList`, bounded-depth directory listing) |
| Single file handle | `acqstore.acq_image.acq_image` (`AcqImage`) |
| ROI models | `acqstore.acq_image.roi` |
| Loaders / factory | `acqstore.acq_image.file_loaders`, `acqstore.acq_image.file_loader_factory` |
| Schema | `acqstore.schema` |

## Using `AcqImageList`

- **Single file:** pass a path to one supported file; the list has length **1**.
- **Directory:** pass a directory path; files are collected up to **`folder_depth`** (default **4**). Depth `1` is only the top folder; each increment includes one more level of subdirectories.

```python
from acqstore.acq_image.acq_image_list import AcqImageList

lst = AcqImageList('/path/to/folder', folder_depth=2)
single = AcqImageList('/path/to/file.tif')
```

## Documentation index

- Repo hub: [`docs/packages/README.md`](../../docs/packages/README.md)
- Schemas: [`docs/acqstore/schemas.md`](../../docs/acqstore/schemas.md)
- Architecture: [`docs/architecture.md`](../../docs/architecture.md)
