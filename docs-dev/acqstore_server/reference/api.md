# AcqStore Server API v2 contract

This document is the written HTTP contract for thin clients. The machine-readable contract is available from a running server at:

```text
http://127.0.0.1:8767/openapi.json
```

Interactive Swagger documentation is available at:

```text
http://127.0.0.1:8767/docs
```

For a complete JavaScript implementation, see [JavaScript client guide](javascript-client.md).

## Base URLs

```javascript
const SERVER = 'http://127.0.0.1:8767';
const API = `${SERVER}/api/v2`;
```

The server binds to localhost by default. A thin client always requires a running AcqStore Server instance, either the packaged desktop app or a source-based Python process.

## Client lifecycle

A complete client normally follows this sequence:

```text
GET  /api/v2/health
GET  /api/v2/capabilities
POST /api/v2/pick-and-open       or POST /api/v2/open
GET  returned channel dataUrl values
GET  /api/v2/sessions/{sessionId}
DELETE /api/v2/sessions/{sessionId}
```

## Discovery

### `GET /api/v2`

Returns links to the maintained v2 resources.

### `GET /api/v2/health`

Example response:

```json
{
  "ok": true,
  "apiVersion": "v2"
}
```

Use this as the lightest check that the local server and v2 router are available.

### `GET /api/v2/capabilities`

Example response shape:

```json
{
  "ok": true,
  "apiVersion": "v2",
  "supportedImportExtensions": [".tif", ".oir"],
  "allowedImportExtensions": [".tif", ".oir"],
  "binary": {
    "servedDtype": "float32",
    "encoding": "raw-f32-le",
    "layout": "row-major",
    "mediaType": "application/octet-stream"
  },
  "sessionTtlSeconds": 300.0
}
```

The extension lists are runtime values sourced from AcqStore. Clients should not hard-code them.

## Open an acquisition

### `POST /api/v2/pick-and-open`

Use the native file picker on the machine running AcqStore Server.

Minimal request:

```json
{}
```

Optional channel and extension selection:

```json
{
  "channelIndices": [0, 1],
  "extensions": [".oir", ".czi", ".tif"]
}
```

Cancelling the dialog is not an HTTP failure. It returns HTTP 200 with:

```json
{
  "ok": false,
  "error": "cancelled",
  "message": "User cancelled file dialog"
}
```

### `POST /api/v2/open`

Use an absolute path visible to the server process:

```json
{
  "path": "/absolute/path/to/acquisition.oir",
  "channelIndices": [0, 1]
}
```

Omit `channelIndices` to load all channels. Requested channel order is preserved.

## Successful open response

Both open endpoints return the same contract:

```json
{
  "ok": true,
  "apiVersion": "v2",
  "sessionId": "example-session-id",
  "source": {
    "path": "/absolute/path/to/acquisition.oir",
    "name": "acquisition.oir",
    "format": "oir",
    "sourceDtype": "uint16",
    "numChannels": 2
  },
  "header": {
    "shape": [2, 30000, 24],
    "dims": ["C", "Y", "X"],
    "sizes": {"C": 2, "Y": 30000, "X": 24},
    "dtype": "uint16",
    "numChannels": 2,
    "physicalUnits": [1.0, 0.000535, 0.011414],
    "physicalUnitsLabels": ["Channels", "seconds", "micrometer"],
    "date": "",
    "time": "",
    "fileSize": ""
  },
  "plane": {
    "shape": [30000, 24],
    "axes": [
      {"arrayDimension": 0, "name": "Y", "size": 30000, "step": 0.000535, "unit": "seconds"},
      {"arrayDimension": 1, "name": "X", "size": 24, "step": 0.011414, "unit": "micrometer"}
    ],
    "servedDtype": "float32",
    "encoding": "raw-f32-le",
    "layout": "row-major",
    "mediaType": "application/octet-stream"
  },
  "channels": [
    {
      "index": 0,
      "name": "Channel 0",
      "byteLength": 2880000,
      "dataUrl": "/api/v2/sessions/example-session-id/channels/0/data"
    }
  ],
  "reference": null
}
```

Field values above are illustrative. Clients must use the values returned by the running server.

`header` is normalized AcqStore acquisition metadata. `plane` describes the two-dimensional arrays served for the selected source channels.

## Binary source planes

### `GET /api/v2/sessions/{sessionId}/channels/{channelIndex}/data`

The response body is raw binary:

```text
Content-Type: application/octet-stream
Cache-Control: no-store
```

Decode it as little-endian float32. Validate:

```text
response byte count == channel.byteLength
float32 sample count == plane.shape[0] * plane.shape[1]
```

The payload is row-major and has not been transposed by the server.

## Reference image

When present, `reference` contains its own `plane`, `channels`, optional `lineRoi`, and optional `scanPath`.

Reference binary URL:

```text
GET /api/v2/sessions/{sessionId}/reference/channels/{channelIndex}/data
```

Decode and validate it using `reference.plane` and the selected reference channel's `byteLength`.

## Session lifecycle

### `GET /api/v2/sessions/{sessionId}`

Example response:

```json
{
  "ok": true,
  "sessionId": "example-session-id",
  "ttlSecondsRemaining": 294.2,
  "channelIndices": [0, 1],
  "referenceChannelIndices": [0],
  "totalBytes": 5764096
}
```

### `DELETE /api/v2/sessions/{sessionId}`

Example response:

```json
{
  "ok": true,
  "sessionId": "example-session-id",
  "deleted": true
}
```

Clients should explicitly delete sessions when finished.

## Stable errors

All v2 JSON errors use:

```json
{
  "ok": false,
  "error": "stable_machine_code",
  "message": "Human-readable summary",
  "details": null
}
```

Request-validation errors include `details`. Clients should branch on `error`, not on `message` text.

Common codes include:

```text
cancelled
path_not_found
unsupported_format
invalid_channel_indices
channel_out_of_range
channel_not_found
reference_channel_not_found
session_not_found
load_timeout
decode_failed
```

## Maintained reference client

The maintained v2 client is:

```text
src/acqstore_server/static/demo/v2/index.html
```

When the server is running:

```text
http://127.0.0.1:8767/demo/v2/
```
