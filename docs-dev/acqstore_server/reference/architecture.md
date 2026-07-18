# API v2 architecture

## Version isolation

V1 remains implemented by the unversioned legacy modules under `src/acqstore_server/`. V2 is independently implemented under `src/acqstore_server/v2/`. The two versions share application composition and the read-only AcqStore package, but v2 does not call v1 services or stores.

## Layering

```text
FastAPI routes and public schemas
            ↓
transport encoding + v2 session store
            ↓
transport-neutral v2 models/open service
            ↓
read-only AcqStore public API
```

`models.py` contains NumPy arrays and acquisition metadata, but no URLs, JSON aliases, FastAPI objects, or display transforms. `routes.py` owns URL construction, response schemas, error envelopes, session registration, and binary responses.

## AcqStore API boundary

The current implementation uses these verified AcqStore APIs:

- `AcqImage(..., load_images=True, load_analysis_csv=False)`;
- `AcqImage.pixels`;
- `pixels.num_channels` and `pixels.get_plane(c=index)`;
- `AcqImage.get_image_physical_units()`;
- `AcqImage.images.header`;
- `AcqImage.images.has_reference_image` and `.reference_image`;
- `ReferenceImage.get_plane()` and `get_scan_path_plot()`;
- `get_supported_import_extensions()`;
- `get_allowed_import_extensions()`;
- `normalize_import_extension_for_path()`.

Before adding another AcqStore call, inspect its implementation in `src/acqstore/`. That directory is not edited by this server project.

## Session lifecycle

Opening an acquisition converts selected source/reference planes to raw float32 buffers and stores them in an opaque in-memory session. The response contains binary resource URLs. Sessions expire automatically and can also be explicitly deleted. Session metadata never exposes the binary payloads.

## Orientation

The server serves row-major arrays with shape `[dimension0, dimension1]`. Client rendering choices such as canvas axis direction or Plotly transpose are not server semantics.
