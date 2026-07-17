# API v2 JavaScript demo

The maintained browser demo is a generic thin client served at:

```text
/demo/v2/
```

Its source is:

```text
src/acqstore_server/static/demo/v2/index.html
```

It requires a running AcqStore Server. The server may be started from a Python development checkout or by launching the packaged desktop application.

The intended workflow is:

```text
Click Pick and open
→ server shows a native file dialog
→ AcqStore opens the selected acquisition through AcqImage
→ server returns metadata and session URLs
→ browser downloads and renders selected planes
```

The v2 demo is intentionally separate from the frozen v1 demo at `/demo/`. It is not tied to any particular biological analysis or external application.

The demo exercises the public v2 contract:

- `POST /api/v2/open`
- `POST /api/v2/pick-and-open`
- `channels[].dataUrl`
- `reference.channels[].dataUrl`
- `plane.shape`
- `plane.axes`
- raw little-endian float32 decoding

The canvas renders array dimension 1 horizontally and array dimension 0 vertically. That is a client display decision. The server does not transpose arrays or swap reference coordinates.

Keep this demo synchronized with every intentional v2 contract change. Tests verify that it targets only `/api/v2` and does not contain v1 role fields.


## Header display

After an acquisition opens, the demo displays the AcqStore image header separately
from the complete open response. This gives client developers a direct example of
using `header.dims`, `header.sizes`, `header.physicalUnits`, and related metadata.
