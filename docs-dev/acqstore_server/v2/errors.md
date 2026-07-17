# API v2 errors

API v2 uses one JSON error envelope for service failures, missing sessions, and request-validation failures.

```json
{
  "ok": false,
  "error": "request_validation_failed",
  "message": "Request validation failed",
  "details": [
    {
      "location": ["body", "channelIndices"],
      "message": "channelIndices must not contain duplicate indices",
      "type": "value_error"
    }
  ]
}
```

## Fields

- `ok` is always `false`.
- `error` is a stable machine-readable code.
- `message` is a concise human-readable summary.
- `details` is present for request-validation failures and identifies each invalid body, path, or query value.

Clients should branch on `error`, not on the wording of `message` or individual validation messages.

## Request validation

Malformed JSON, missing required fields, unknown fields, invalid channel indices, and invalid path parameters return:

```text
HTTP 422
error = request_validation_failed
```

This normalization is scoped to `/api/v2`. The frozen v1 API retains its existing FastAPI validation response.

## Common service codes

| Code | Typical status | Meaning |
|---|---:|---|
| `path_not_found` | 404 | The requested acquisition path does not exist. |
| `unsupported_format` | 415 | AcqStore cannot open the path format. |
| `invalid_channel_indices` | 422 | Channel selection is invalid for the acquisition. |
| `channel_out_of_range` | 422 | A requested channel index is unavailable. |
| `calibration_unavailable` | 422 | Required plane calibration is unavailable. |
| `load_timeout` | 504 | Open/decode exceeded the configured timeout. |
| `decode_failed` | 500 | AcqStore failed while decoding the acquisition. |
| `session_not_found` | 404 | The session expired, was deleted, or never existed. |
| `channel_not_found` | 404 | The source channel is not stored in the session. |
| `reference_channel_not_found` | 404 | The reference channel is not stored in the session. |
| `cancelled` | 200 | The user cancelled the native picker. |
