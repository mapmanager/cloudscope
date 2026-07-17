# AcqStore Server API v2

API v2 is a generic, channel-indexed interface. It does not assign biological roles to channels.

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
