# AcqStore Server — Reference image API (v0)

**Audience:** HTML authors fetching the overview / reference attachment after
`POST /api/v1/open` or `POST /api/v1/pick-and-open`.

**Do not invent fields.** Prefer live OpenAPI at `/openapi.json` for exact
schemas; this page explains reference-specific behavior.

Related: [`html_integration_v0.md`](html_integration_v0.md) · [`llm_agent_guide_v0.md`](llm_agent_guide_v0.md).

Base URL (default): `http://127.0.0.1:8767`

**In-repo:** the calcium HTML fork already shows a collapsible **Reference overview**
card (ticket 050) between Image Display and Trace Display.

---

## When is reference present?

After a successful open, JSON field `reference` is either:

- `null` — file has no usable reference attachment (or extraction soft-failed)
- an object — one or more reference channel planes are in the session store

There is **no** standalone “get reference without open” endpoint in v0.

Sessions are short-lived (in-memory TTL ~600 s). Fetch plane bytes soon after open.

---

## Metadata (`reference` object)

| Field | Meaning |
|-------|---------|
| `numChannels` | Number of reference planes |
| `encoding` | Always `raw-f32-le` |
| `layout` | Always `row-major` |
| `height`, `width` | Shared H×W for every channel (API row = Y, col = X) |
| `byteLength` | Bytes for **one** plane (`height * width * 4`) |
| `channels[]` | Per-channel meta + fetch URL (required) |
| `lineRoi` | Optional `[x0,y0,x1,y1]` in reference pixel coords, or `null` |
| `scanPath` | Optional `{ x: number[], y: number[] }` plot-ready path, or `null` |
| `dx`, `dy`, `xUnit`, `yUnit` | Spacing summary from channel 0 |

Each `channels[i]`:

| Field | Meaning |
|-------|---------|
| `index` | Zero-based channel index |
| `url` | `GET /api/v1/session/{sessionId}/reference/channel/{index}` |
| `height`, `width`, `byteLength` | Same layout rules as primary planes |
| `dx`, `dy`, `xUnit`, `yUnit` | Per-channel spacing (usually identical across channels) |

**`dx` / `dy`:** `dx` = physical step for **row/Y**; `dy` = physical step for **column/X**.

**Removed:** `GET …/reference/plane`, top-level `reference.url`. Use `channels[i].url` only.

---

## Binary plane fetch

```http
GET /api/v1/session/{sessionId}/reference/channel/{index}
```

- Body: little-endian float32, length `height * width * 4`
- Reshape to `[height][width]` (Y, X)
- `Content-Type: application/octet-stream`
- Missing session/channel → JSON error, HTTP 404
- Negative `index` → HTTP 422

Display tip: `/demo/` and the HTML fork **transpose** for screen layout
(dim0→canvas X, dim1→canvas Y). Overlay mapping: canvas `(scanPath.y * scaleX, scanPath.x * scaleY)` after that transpose (see demo `drawReference`).

---

## Client recipe

1. Open file → read `meta.reference`.
2. If `null`, hide / collapse reference UI.
3. For each entry in `meta.reference.channels`, `fetch(BASE + ch.url)` and decode float32.
4. Overlay `scanPath` / `lineRoi` in **reference pixel coordinates** (not primary kymograph coords).

---

## Errors / limits

| Situation | Behavior |
|-----------|----------|
| No reference in file | `reference: null` (open still succeeds) |
| Soft extraction failure | Logged server-side; `reference: null` |
| Open/decode too slow | `error: load_timeout`, HTTP **504** (default 120s; env `ACQSTORE_SERVER_OPEN_TIMEOUT_S`) |
| Stale session | Plane GET → 404 |

---

## Not in v0

- Thumbnail / pyramid / JPEG preview endpoints
- Reference-only open without loading primary planes
- Guaranteed mid-decode cancellation after timeout (worker may finish in background)
