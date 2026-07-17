# API v2 JavaScript demo

The maintained browser demo is served at:

```text
/demo/v2/
```

Its source is:

```text
src/acqstore_server/static/demo/v2/index.html
```

The v2 demo is intentionally separate from the frozen v1 demo at `/demo/`.
It is a generic client and does not assign biological roles to channels.

The demo exercises the public v2 contract:

- `POST /api/v2/open`
- `POST /api/v2/pick-and-open`
- `channels[].dataUrl`
- `reference.channels[].dataUrl`
- `plane.shape`
- `plane.axes`
- raw little-endian float32 decoding

The canvas renders array dimension 1 horizontally and array dimension 0 vertically.
That is a client display decision. The server does not transpose arrays or swap
reference coordinates.

Keep this demo synchronized with every intentional v2 contract change. Tests verify
that it targets only `/api/v2` and does not contain v1 role fields.
