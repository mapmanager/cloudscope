# AcqStore Server — HTML integration (v0)

**Audience:** Claude (or a developer pasting this into Claude) updating
`neuronal_calcium_linescan_analyzer_vN.html` (or the in-repo fork under
`scripts/acqstore_server/clients/neuronal_calcium_linescan/`).

**Do not invent API fields.** Implement exactly against this contract.

**Also read:** [`llm_agent_guide_v0.md`](llm_agent_guide_v0.md) (server context),
[`reference_api_v0.md`](reference_api_v0.md) (reference planes).

Base URL (default): `http://127.0.0.1:8767`

**In-repo status:** the fork already implements pick-and-open load (ticket 049)
and reference overview (ticket 050). This handout remains the contract if you
extend or re-port the integration.

---

## Preconditions

1. User starts AcqStore Server: `uv run python -m acqstore_server` or
   `uv run python -m acqstore_server.desktop` (or packaged `.app`).
2. User opens the calcium HTML in a browser (any host/`file://`, or a static site).
3. Keep existing TIFF “Choose file” UI working. Add a **second** load path
   (already present in the in-repo fork).

**External HTML is supported.** Server enables CORS (`Access-Control-Allow-Origin: *`), including `file://` (`Origin: null`). The HTML must call absolute URLs, e.g. `http://127.0.0.1:8767/api/v1/pick-and-open`, then fetch plane bytes from the returned `url` fields. Our `/demo/` is only a same-origin test page — colleagues do **not** need to host their HTML on this server.

**Machine-readable contract:** live server exposes OpenAPI at `http://127.0.0.1:8767/openapi.json` (Swagger UI at `/docs`). Prefer this handout for workflow/display rules (transpose is client-side); use OpenAPI for exact request/response schemas.

---

## Endpoints

### `GET /api/v1/health`

Success JSON (fields may grow; always check `ok`):

```json
{
  "ok": true,
  "app": "acqstore_server",
  "version": "0.1.0",
  "bind": "127.0.0.1:8767",
  "docs": "/docs",
  "demo": "/demo/",
  "logFile": "/Users/…/Library/Logs/AcqStore Server/acqstore_server.log"
}
```

### `POST /api/v1/pick-and-open`  ← primary button target

Request body (all fields optional):

```json
{
  "calciumChannel": 0,
  "vesselChannel": 1,
  "extensions": [".oir", ".czi", ".tif", ".tiff", ".nd2"]
}
```

- Defaults: `calciumChannel=0`, `vesselChannel=1`.
- Set `"vesselChannel": null` to force single-channel even if the file has more channels.
- Server shows a **native OS file dialog**. Browser does not receive a filesystem path from `<input type=file>`.

Success: same shape as `/api/v1/open` (below).  
Cancel:

```json
{ "ok": false, "error": "cancelled", "message": "User cancelled file dialog" }
```

HTTP status for cancel: **200**.

### `POST /api/v1/open`

```json
{
  "path": "/absolute/path/to/file.oir",
  "calciumChannel": 0,
  "vesselChannel": 1
}
```

### `GET /api/v1/session/{sessionId}/channel/{role}`

- `role` is `calcium` or `vessels`
- Body: raw **little-endian float32**, length `height * width * 4`
- Layout: **row-major** `(y * width + x)` → reshape to `[height][width]`
- `Content-Type: application/octet-stream`

### `GET /api/v1/session/{sessionId}/reference/channel/{index}`

- Present when open JSON has non-null `reference`
- `index` is zero-based (`0` … `reference.numChannels - 1`)
- Body: raw **little-endian float32** plane for that reference channel
- Layout: **row-major** `(Y, X)` in reference-image pixel coordinates
- `Content-Type: application/octet-stream`
- See also [`reference_api_v0.md`](reference_api_v0.md)

**Removed (do not call):** `GET …/reference/plane`, top-level `reference.url`.

---

## Success JSON (exact)

```json
{
  "ok": true,
  "sessionId": "…",
  "source": {
    "path": "/abs/file.oir",
    "format": "oir",
    "numChannels": 2,
    "width": 256,
    "height": 20000,
    "dtype": "float32"
  },
  "calibration": {
    "msPerLine": 2.118,
    "umPerPixel": 0.33,
    "stepYSeconds": 0.002118,
    "stepXUm": 0.33,
    "unitsSource": "acqimage"
  },
  "channels": {
    "calcium": {
      "index": 0,
      "name": "CH1",
      "role": "calcium",
      "encoding": "raw-f32-le",
      "layout": "row-major",
      "height": 20000,
      "width": 256,
      "byteLength": 20480000,
      "url": "/api/v1/session/…/channel/calcium"
    },
    "vessels": {
      "index": 1,
      "name": "CH2",
      "role": "vessels",
      "encoding": "raw-f32-le",
      "layout": "row-major",
      "height": 20000,
      "width": 256,
      "byteLength": 20480000,
      "url": "/api/v1/session/…/channel/vessels"
    }
  },
  "reference": {
    "numChannels": 2,
    "encoding": "raw-f32-le",
    "layout": "row-major",
    "height": 512,
    "width": 512,
    "byteLength": 1048576,
    "channels": [
      {
        "index": 0,
        "encoding": "raw-f32-le",
        "layout": "row-major",
        "height": 512,
        "width": 512,
        "byteLength": 1048576,
        "url": "/api/v1/session/…/reference/channel/0",
        "dx": 0.5,
        "dy": 0.25,
        "xUnit": "um",
        "yUnit": "um"
      },
      {
        "index": 1,
        "encoding": "raw-f32-le",
        "layout": "row-major",
        "height": 512,
        "width": 512,
        "byteLength": 1048576,
        "url": "/api/v1/session/…/reference/channel/1",
        "dx": 0.5,
        "dy": 0.25,
        "xUnit": "um",
        "yUnit": "um"
      }
    ],
    "lineRoi": [10.0, 20.0, 400.0, 20.0],
    "scanPath": { "x": [10.0, 400.0], "y": [20.0, 20.0] },
    "dx": 0.5,
    "dy": 0.25,
    "xUnit": "um",
    "yUnit": "um"
  }
}
```

If single-channel linescan: **omit** `channels.vessels` (do not invent an empty plane).  
If no reference attachment: **`"reference": null`** (not an error).

Top-level `reference.height` / `width` / `byteLength` / spacing summarize channel 0 (all channels share H×W). Fetch planes only via `reference.channels[i].url`.

`lineRoi` is `[x0, y0, x1, y1]` in **reference pixel** coordinates, or `null`.  
`scanPath` is plot-ready `{x:[...], y:[...]}` in **reference pixel** coordinates, or `null`. Prefer `scanPath` for overlay when present; else draw `lineRoi` as a segment. Draw the same overlay on **every** reference channel panel.

**Note on `dx` / `dy`:** From AcqStore `ReferenceImagePlane`: `dx` is the physical step for **row/Y** indices; `dy` is the physical step for **column/X** indices.

**Display:** server does not transpose. Demo + in-repo fork use dim0→canvas X, dim1→canvas Y for kymograph and reference.

---

## Ordered client algorithm

1. Add button **Load from AcqStore Server**.
2. Config base URL default `http://127.0.0.1:8767` (optional health check).
3. On click: `POST ${base}/api/v1/pick-and-open` with JSON body (may be `{}`).
4. If `ok === false` and `error === "cancelled"` → return quietly.
5. If `ok === false` → show `message` to the user; stop. (`load_timeout` → HTTP 504.)
6. For `channels.calcium.url`: `GET` absolute URL `${base}${url}` if `url` is path-absolute.
7. `const f32 = new Float32Array(await response.arrayBuffer())`.
8. Build `raw` as array of length `height`, each row `f32.subarray(y*width, (y+1)*width)` **or** equivalent `[height][width]` structure expected by existing `setImage`.
9. If `channels.vessels` present, repeat for vessels.
10. Set `$('msPerLine').value = calibration.msPerLine` and `$('umPerPixel').value = calibration.umPerPixel` (and sync range inputs if present).
11. If vessels present:

```js
setImage(calciumRows, source.path, {
  dualMode: true,
  channels: {
    ocamp: calciumRows,
    fitc: vesselsRows,
    ocampName: channels.calcium.name,
    fitcName: channels.vessels.name
  }
});
```

12. Else: `setImage(calciumRows, source.path)`.
13. Call existing calibration refresh (`updateCalInfo` / `applyPixelDimensions` / `renderAll`) as the current HTML already does after load.
14. **Reference overview:** if `reference !== null`, for each `reference.channels[i]`, `GET` that channel `url`, decode float32 plane, draw overview panel(s); overlay `reference.scanPath` polyline or `reference.lineRoi` segment in the **same pixel coordinate system** as the reference plane. See [`reference_api_v0.md`](reference_api_v0.md). (Implemented in the in-repo fork as a collapsible card after Image Display.)
15. If `error === "load_timeout"` (HTTP 504) → show that open/decode exceeded the server soft timeout (default 120s; env `ACQSTORE_SERVER_OPEN_TIMEOUT_S`).

**Do not** replace TIFF choose-file. **Do not** invent new analysis APIs. **Do not** invent reference fields beyond this contract.

---

## Error codes

| `error` | Meaning |
|---------|---------|
| `cancelled` | User closed dialog |
| `path_not_found` | Missing path / session |
| `unsupported_format` | AcqImage rejected format |
| `channel_out_of_range` | Bad channel index |
| `calibration_unavailable` | No usable physical units |
| `load_timeout` | Open/decode exceeded soft timeout (HTTP 504) |
| `decode_failed` | IO / plane decode failure |

---

## Copy-paste skeleton (adapt to existing `$` / `setImage`)

```js
const ACQSTORE_BASE = 'http://127.0.0.1:8767';

async function fetchChannelRows(base, ch) {
  const r = await fetch(base + ch.url);
  if (!r.ok) throw new Error('channel fetch failed: ' + ch.url);
  const buf = await r.arrayBuffer();
  const f32 = new Float32Array(buf);
  if (f32.length !== ch.height * ch.width) {
    throw new Error('byte length mismatch for ' + (ch.role || 'plane'));
  }
  const rows = new Array(ch.height);
  for (let y = 0; y < ch.height; y++) {
    rows[y] = f32.subarray(y * ch.width, (y + 1) * ch.width);
  }
  return rows;
}

async function loadFromAcqStoreServer() {
  const metaResp = await fetch(ACQSTORE_BASE + '/api/v1/pick-and-open', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ calciumChannel: 0, vesselChannel: 1 }),
  });
  const meta = await metaResp.json();
  if (!meta.ok) {
    if (meta.error === 'cancelled') return;
    throw new Error(meta.message || meta.error);
  }
  const calcium = await fetchChannelRows(ACQSTORE_BASE, meta.channels.calcium);
  const vessels = meta.channels.vessels
    ? await fetchChannelRows(ACQSTORE_BASE, meta.channels.vessels)
    : null;

  $('msPerLine').value = meta.calibration.msPerLine;
  $('umPerPixel').value = meta.calibration.umPerPixel;
  if ($('msPerLineRange')) $('msPerLineRange').value = meta.calibration.msPerLine;
  if ($('umPerPixelRange')) $('umPerPixelRange').value = meta.calibration.umPerPixel;

  if (vessels) {
    setImage(calcium, meta.source.path, {
      dualMode: true,
      channels: {
        ocamp: calcium,
        fitc: vessels,
        ocampName: meta.channels.calcium.name,
        fitcName: meta.channels.vessels.name,
      },
    });
  } else {
    setImage(calcium, meta.source.path);
  }
  updateCalInfo();
  renderAll();

  // Reference: fetch meta.reference.channels[i].url — see reference_api_v0.md
  // and scripts/acqstore_server/clients/neuronal_calcium_linescan (ticket 050) for a working panel.
}
```

Live miniature of this integration (owned by AcqStore Server, not the calcium app):

`http://127.0.0.1:8767/demo/`

In-repo full analyzer fork:

`scripts/acqstore_server/clients/neuronal_calcium_linescan/` (e.g. `linescan_analyzer_v1_18_b.html`)
