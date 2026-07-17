# AcqStore Server API v2

API v2 is a generic, channel-indexed HTTP interface over AcqStore.

## Open a server-accessible path

```http
POST /api/v2/open
Content-Type: application/json
```

```json
{
  "path": "/absolute/path/to/acquisition.tif",
  "channelIndices": [2, 0]
}
```

Omit `channelIndices` to return all source channels. Requested order is preserved.

## Native file picker

```http
POST /api/v2/pick-and-open
Content-Type: application/json
```

```json
{
  "channelIndices": [0, 1],
  "extensions": [".oir", ".czi", ".tif"]
}
```

## Binary channel data

Each response channel includes a `dataUrl` such as:

```text
/api/v2/sessions/{sessionId}/channels/{channelIndex}/data
```

Reference-image channels use:

```text
/api/v2/sessions/{sessionId}/reference/channels/{channelIndex}/data
```

The binary representation is:

- `float32`
- little-endian
- row-major
- uncompressed `application/octet-stream`
- `Cache-Control: no-store`

Plane shape and axis calibration are reported separately in the JSON response.

## Coordinate semantics

The server reports arrays and reference coordinates in AcqStore convention. It does not apply Plotly-specific transposes or coordinate swaps.

## Capabilities

```http
GET /api/v2/capabilities
```

Returns the runtime AcqStore import extensions and the transport/session configuration:

```json
{
  "ok": true,
  "apiVersion": "v2",
  "supportedImportExtensions": ["czi", "nd2", "oir", "ome.zarr", "tif"],
  "allowedImportExtensions": ["czi", "nd2", "oir", "ome.zarr", "tif"],
  "binary": {
    "servedDtype": "float32",
    "encoding": "raw-f32-le",
    "layout": "row-major",
    "mediaType": "application/octet-stream"
  },
  "sessionTtlSeconds": 600.0
}
```

The exact extension arrays are runtime data. Clients should not hard-code the example list.

## Session metadata

```http
GET /api/v2/sessions/{sessionId}
```

Returns live-session channel indices, reference-channel indices, total binary bytes, and remaining TTL.

## Delete a session

```http
DELETE /api/v2/sessions/{sessionId}
```

Clients handling large acquisitions should delete sessions when their buffers are no longer needed. Expired or already-deleted sessions return `session_not_found`.

## API index

```http
GET /api/v2
```

The API index is the stable discovery entry point for clients. It returns links rather than requiring callers to know every route in advance.

## Binary response contract

Source and reference channel URLs return:

```text
Content-Type: application/octet-stream
Cache-Control: no-store
```

The payload is a row-major little-endian float32 array. Clients must:

1. verify the downloaded byte count equals `byteLength`;
2. decode with little-endian float32;
3. verify the sample count equals the product of `plane.shape`;
4. reshape using `plane.shape`.

The OpenAPI document describes these responses as binary `application/octet-stream` payloads.

## Errors

API v2 uses a stable `{ok, error, message}` envelope. Request-validation failures also include machine-readable `details`. See [API v2 errors](errors.md).


## AcqStore header

Successful `POST /api/v2/open` and `POST /api/v2/pick-and-open` responses include a
`header` object sourced from AcqStore's public `ImageHeader.as_json_dict()` API. It
contains the native acquisition shape, dimensions, dimension sizes, source dtype,
channel count, physical calibration, acquisition date/time, and display file size.
The server preserves AcqStore's normalized values and only applies camelCase JSON
aliases.

## JavaScript integration

For the complete client workflow and copyable implementation, see the [JavaScript client guide](javascript-client.md).
