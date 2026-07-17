# AcqStore Server client roadmap

This is the complete onboarding path for a new browser or JavaScript client.

**Goal:** open one acquisition, read its AcqStore header, fetch one source image plane, display it, and delete the server session.

The API is deliberately small. A first client needs only health, capabilities, open, one binary data request, and session deletion.

## 1. Start the server

External developers normally run the packaged **AcqStore Server.app** supplied by the AcqStore Server developers.

From a CloudScope source checkout, start the equivalent server with:

```bash
uv run python -m acqstore_server
```

The default addresses are:

```javascript
const SERVER = 'http://127.0.0.1:8767';
const API = `${SERVER}/api/v2`;
```

The maintained reference client is available while the server is running:

```text
http://127.0.0.1:8767/demo/v2/
```

## 2. Verify health and discover capabilities

```javascript
const health = await fetch(`${API}/health`).then((response) => response.json());
const capabilities = await fetch(`${API}/capabilities`).then((response) => response.json());

if (!health.ok) {
  throw new Error('AcqStore Server is not healthy');
}
```

Read capabilities at runtime rather than hard-coding supported acquisition formats. Capabilities also reports the session time-to-live.

## 3. Open an acquisition

There are two supported workflows.

### Native picker on the server machine

```javascript
const response = await fetch(`${API}/pick-and-open`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({}),
});
const opened = await response.json();
```

The native file dialog appears on the machine running AcqStore Server.

Cancelling the picker is not an HTTP failure. It returns HTTP 200 with:

```json
{
  "ok": false,
  "error": "cancelled"
}
```

### Known path visible to the server

```javascript
const response = await fetch(`${API}/open`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({path: '/absolute/path/visible/to/the/server.oir'}),
});
const opened = await response.json();
```

The path must be absolute and readable by the server process. A browser-local path is not automatically visible to a remote server.

For either workflow, check both the HTTP status and `opened.ok`:

```javascript
if (!response.ok || opened.ok === false) {
  throw new Error(`${opened.error ?? response.status}: ${opened.message ?? response.statusText}`);
}
```

## 4. Use the open response

A successful response contains the information needed for the first viewer:

```javascript
const sessionId = opened.sessionId;
const header = opened.header;
const plane = opened.plane;
const firstChannel = opened.channels[0];
```

The important fields are:

- `sessionId` — identifies the loaded acquisition
- `source` — file name, path, format, source dtype, and channel count
- `header` — AcqStore acquisition header JSON
- `plane.shape` — served two-dimensional shape as `[rows, columns]`
- `plane.axes` — axis names, sizes, steps, and units supplied by AcqStore
- `channels[].dataUrl` — relative URL for each source channel's binary plane
- `channels[].byteLength` — expected binary response size
- `reference` — optional reference-image metadata and channel URLs

Treat example metadata values as illustrative. Use the fields returned for the actual acquisition; do not assume particular axis names or units.

## 5. Fetch and decode one source plane

`dataUrl` is relative to the AcqStore Server origin. A standalone page opened from `file://` or another web server must prefix `SERVER`:

```javascript
const dataResponse = await fetch(`${SERVER}${firstChannel.dataUrl}`, {
  cache: 'no-store',
});

if (!dataResponse.ok) {
  throw new Error(`Binary request failed: HTTP ${dataResponse.status}`);
}

const buffer = await dataResponse.arrayBuffer();

if (buffer.byteLength !== firstChannel.byteLength) {
  throw new Error(
    `byteLength mismatch: expected ${firstChannel.byteLength}, got ${buffer.byteLength}`,
  );
}
```

The binary contract is row-major, little-endian Float32. Decode it portably with `DataView`:

```javascript
function decodeFloat32LittleEndian(buffer) {
  if (buffer.byteLength % 4 !== 0) {
    throw new Error('Float32 payload length must be divisible by four');
  }

  const view = new DataView(buffer);
  const values = new Float32Array(buffer.byteLength / 4);

  for (let index = 0; index < values.length; index += 1) {
    values[index] = view.getFloat32(index * 4, true);
  }

  return values;
}

const values = decodeFloat32LittleEndian(buffer);
const expectedSamples = plane.shape[0] * plane.shape[1];

if (values.length !== expectedSamples) {
  throw new Error(
    `sample-count mismatch: expected ${expectedSamples}, got ${values.length}`,
  );
}
```

At this point, `values` represents the original AcqStore plane in row-major `[rows, columns]` order.

## 6. Display the image

The server does **not** transpose image data. Transpose is an optional client-side display choice.

For example, the maintained demo transposes immediately before display because that orientation is useful for line-scan acquisitions:

```javascript
function transposePlane(values, shape) {
  const [rows, columns] = shape;
  const transposed = new Float32Array(values.length);

  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      transposed[column * rows + row] = values[row * columns + column];
    }
  }

  return {
    values: transposed,
    shape: [columns, rows],
  };
}
```

A client may instead display the original `[rows, columns]` plane directly. The choice depends on the application's visualization convention; it is not an API contract requirement.

Render either representation with Canvas, Plotly, or another graphics library.

## 7. Delete the session

Delete the server session when the client is finished:

```javascript
const deleteResponse = await fetch(
  `${API}/sessions/${encodeURIComponent(sessionId)}`,
  {method: 'DELETE'},
);
const deleted = await deleteResponse.json();

if (!deleteResponse.ok || deleted.ok === false) {
  throw new Error(`${deleted.error ?? deleteResponse.status}: ${deleted.message ?? deleteResponse.statusText}`);
}
```

Sessions also expire after the TTL reported by `/capabilities`. Clients should still delete sessions explicitly rather than waiting for expiration.

## 8. Finished

A working first client now performs this lifecycle:

```text
health
→ capabilities
→ pick-and-open or open
→ read header and plane metadata
→ fetch one channels[].dataUrl
→ validate and decode little-endian Float32
→ display original or client-transposed plane
→ delete session
```

Use the detailed reference only when needed:

- [API contract](reference/api.md)
- [Complete JavaScript client patterns](reference/javascript-client.md)
- [Stable errors](reference/errors.md)
- [Maintained demo behavior](reference/demo.md)
- [Reference index](reference/README.md)

The server's interactive OpenAPI documentation is also available at:

```text
http://127.0.0.1:8767/docs
```
