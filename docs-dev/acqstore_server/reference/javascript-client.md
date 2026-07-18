# JavaScript client guide

This is the primary integration guide for JavaScript clients using **AcqStore Server API v2**.

AcqStore Server must already be running. A client may connect to either:

- the packaged macOS application supplied by the AcqStore Server developers; or
- a server started from the CloudScope source tree by a Python developer.

The default local address is:

```text
http://127.0.0.1:8767
```

The server uses AcqStore and `AcqImage` to open the acquisition. The JavaScript client receives metadata as JSON and image planes as raw float32 binary data.

## First checks

Verify the server and discover its runtime contract:

```javascript
const SERVER = 'http://127.0.0.1:8767';
const API = `${SERVER}/api/v2`;

const health = await requestJson(`${API}/health`);
const capabilities = await requestJson(`${API}/capabilities`);

console.log(health.apiVersion);                    // "v2"
console.log(capabilities.allowedImportExtensions); // runtime AcqStore formats
console.log(capabilities.binary.encoding);         // "raw-f32-le"
```

Do not hard-code the supported extension list. It is derived from the AcqStore installation used by the running server.

## Two ways to open an acquisition

### Native file picker

For a local browser client, this is normally the simplest workflow:

```javascript
const opened = await requestJson(`${API}/pick-and-open`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({}),
});
```

The file dialog is displayed by the machine running AcqStore Server. Cancelling the dialog returns HTTP 200 with `ok: false` and `error: "cancelled"`; `requestJson()` below treats that as an error.

An optional request can restrict channels or the native picker extensions:

```javascript
{
  channelIndices: [0, 1],
  extensions: ['.oir', '.czi', '.tif']
}
```

### Server-visible path

Use this only when the client already knows an absolute path visible to the server process:

```javascript
const opened = await requestJson(`${API}/open`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    path: '/absolute/path/to/acquisition.oir',
    channelIndices: [0, 1],
  }),
});
```

Omit `channelIndices` to request all channels. Requested channel order is preserved.

## Successful open response

A successful open creates a temporary in-memory session and returns:

- `sessionId`: session used by all binary URLs;
- `source`: source name, format, dtype, and channel count;
- `header`: normalized AcqStore acquisition header;
- `plane`: shape, axes, calibration, and binary encoding for source channels;
- `channels`: source-channel resources;
- `reference`: optional reference-image plane, channels, and scan-path metadata.

The server returns two-dimensional channel planes. Each channel resource contains a `dataUrl` and exact `byteLength`.

## Complete reusable JavaScript client

The following code covers health, capabilities, native picking, path opening, float32 decoding, optional display transpose, session inspection, and cleanup.

```javascript
const SERVER = 'http://127.0.0.1:8767';
const API = `${SERVER}/api/v2`;

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  const contentType = response.headers.get('content-type') || '';

  if (!contentType.includes('application/json')) {
    throw new Error(`Expected JSON from ${url}; received ${contentType || 'unknown content type'}`);
  }

  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    const error = new Error(`${payload.error || response.status}: ${payload.message || response.statusText}`);
    error.code = payload.error || `http_${response.status}`;
    error.status = response.status;
    error.details = payload.details || null;
    throw error;
  }
  return payload;
}

async function getHealth() {
  return requestJson(`${API}/health`);
}

async function getCapabilities() {
  return requestJson(`${API}/capabilities`);
}

async function pickAndOpen({channelIndices, extensions} = {}) {
  const body = {};
  if (channelIndices !== undefined) body.channelIndices = channelIndices;
  if (extensions !== undefined) body.extensions = extensions;

  return requestJson(`${API}/pick-and-open`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
}

async function openPath(path, {channelIndices} = {}) {
  const body = {path};
  if (channelIndices !== undefined) body.channelIndices = channelIndices;

  return requestJson(`${API}/open`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  });
}

function decodeFloat32LittleEndian(buffer) {
  if (buffer.byteLength % 4 !== 0) {
    throw new Error(`Float32 payload byte length must be divisible by 4; got ${buffer.byteLength}`);
  }

  const values = new Float32Array(buffer.byteLength / 4);
  const view = new DataView(buffer);
  for (let index = 0; index < values.length; index += 1) {
    values[index] = view.getFloat32(index * 4, true);
  }
  return values;
}

async function fetchPlane(resource, plane) {
  const response = await fetch(`${SERVER}${resource.dataUrl}`, {cache: 'no-store'});
  if (!response.ok) {
    let message = `Binary fetch failed with HTTP ${response.status}`;
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      const payload = await response.json();
      message = `${payload.error || response.status}: ${payload.message || message}`;
    }
    throw new Error(message);
  }

  const buffer = await response.arrayBuffer();
  if (buffer.byteLength !== resource.byteLength) {
    throw new Error(`byteLength mismatch: expected ${resource.byteLength}, got ${buffer.byteLength}`);
  }

  const values = decodeFloat32LittleEndian(buffer);
  const expectedSamples = plane.shape[0] * plane.shape[1];
  if (values.length !== expectedSamples) {
    throw new Error(`sample count mismatch: expected ${expectedSamples}, got ${values.length}`);
  }

  return {
    values,
    shape: [...plane.shape],
    axes: plane.axes,
  };
}

function transposePlane(values, shape) {
  const rows = shape[0];
  const columns = shape[1];
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

async function getSession(sessionId) {
  return requestJson(`${API}/sessions/${encodeURIComponent(sessionId)}`);
}

async function deleteSession(sessionId) {
  return requestJson(`${API}/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  });
}

async function example() {
  await getHealth();
  const capabilities = await getCapabilities();
  console.log('AcqStore formats:', capabilities.allowedImportExtensions);

  let opened = null;
  try {
    opened = await pickAndOpen();

    console.log('source:', opened.source);
    console.log('AcqStore header:', opened.header);
    console.log('source plane:', opened.plane);

    const sourceChannel = opened.channels[0];
    const sourcePlane = await fetchPlane(sourceChannel, opened.plane);

    // This transpose is a client display decision. The server returns the
    // original row-major AcqStore plane and never transposes it.
    const displayPlane = transposePlane(sourcePlane.values, sourcePlane.shape);
    console.log('display shape:', displayPlane.shape);

    if (opened.reference && opened.reference.channels.length > 0) {
      const referenceResource = opened.reference.channels[0];
      const referencePlane = await fetchPlane(referenceResource, opened.reference.plane);
      const referenceDisplay = transposePlane(referencePlane.values, referencePlane.shape);
      console.log('reference display shape:', referenceDisplay.shape);
      console.log('scan path:', opened.reference.scanPath);
      console.log('line ROI:', opened.reference.lineRoi);
    }

    console.log('session:', await getSession(opened.sessionId));
  } finally {
    if (opened?.sessionId) {
      await deleteSession(opened.sessionId);
    }
  }
}
```

## Binary contract

For every source or reference channel:

1. fetch `dataUrl` with `cache: 'no-store'`;
2. verify the response byte count equals `byteLength`;
3. decode little-endian float32 values;
4. verify sample count equals `plane.shape[0] * plane.shape[1]`;
5. reshape using `plane.shape` in row-major order;
6. apply any transpose only in the client immediately before display.

The server does not transpose image data.

## URL handling

The maintained demo is served by AcqStore Server, so its `dataUrl` values can be fetched directly as relative URLs. An external HTML page may be opened from another origin or from `file://`; prepend `http://127.0.0.1:8767` to relative `dataUrl` values as shown above.

The local server enables CORS for thin clients. It binds to localhost and is not intended to be exposed as a public network service.

## Session lifetime

Binary data is held in memory for a limited time. Read `sessionTtlSeconds` from `/capabilities` rather than assuming a fixed value.

Clients should explicitly delete sessions when finished, especially for large acquisitions. A missing, expired, or already-deleted session returns:

```json
{
  "ok": false,
  "error": "session_not_found",
  "message": "Session not found: ..."
}
```

## Error handling

All v2 JSON errors use:

```json
{
  "ok": false,
  "error": "stable_machine_code",
  "message": "Human-readable summary",
  "details": null
}
```

Validation failures include `details`. Branch on `error`, not the text of `message`.

See [API v2 errors](errors.md) for the stable codes.

## Reference implementation

The maintained working client is:

```text
src/acqstore_server/static/demo/v2/index.html
```

When the server is running:

```text
http://127.0.0.1:8767/demo/v2/
```

Use the demo to verify the server and compare behavior while developing another client.
