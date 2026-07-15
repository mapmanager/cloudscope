# 036 — AcqStore Server design (local open API for calcium HTML)

**Status:** Design / handoff (planning). No implementation in this ticket.  
**Date:** 2026-07-15  
**Working app name:** AcqStore Server (`acqstore_server`)  
**Audience:** CloudScope maintainers + calcium HTML authors (external, not in this repo)

---

## 1. Background

A colleague maintains a standalone browser tool:

`neuronal_calcium_linescan_analyzer_vN.html`

(~5k-line single-file HTML/JS, not versioned in this repo). It:

- Loads line-scan images via a browser **Choose file** control.
- Decodes TIFF (and some raster formats) **entirely in JavaScript**.
- Expects either one calcium raster or **two separate files** (calcium + vessels).
- Asks the user to type/apply `msPerLine` and `umPerPixel`.

Real lab data is often a **single multi-channel Olympus OIR** (or similar) where:

- Calcium and vessel planes are **channels in one file**.
- Shape and physical scaling are shared across channels.
- Decoding and calibration already exist in this monorepo via **`acqstore` / `AcqImage`** and file loaders (`oirfile`, `czifile`, etc.).

Browsers cannot implement a trustworthy OIR/CZI stack. A **local Python process** must open the file and return what the HTML already knows how to consume: 2D float rasters + calibration.

This design defines a **small separate desktop/local server app** (not CloudScope GUI) that exposes that capability.

---

## 2. Purpose

Ship (eventually) a double-clickable / CLI-runnable **AcqStore Server** that:

1. Runs a **localhost-only** HTTP API backed by `acqstore`.
2. Shows a **native OS file dialog** when the calcium HTML requests a load.
3. Opens the chosen file with **`AcqImage`** (format-agnostic; no OIR-only special case).
4. Returns **both channels (when present) + shared calibration** in a stable contract the HTML authors can implement against.

CloudScope remains a separate product. AcqStore Server does not import `cloudscope` or `nicewidgets`.

### 2.1 Parallel deliverable — precise HTML developer roadmap

As we design and implement the server API, we treat **today’s calcium HTML snapshot** only as a **template / reverse-engineering reference** for what the page already knows how to ingest (e.g. `setImage`, dual `channels.ocamp` / `channels.fitc`, `msPerLine`, `umPerPixel`). We do **not** edit or version that HTML here; their file will change independently.

**Required outcome of this workstream:** a precise, standalone integration note for external HTML developers that states:

| Item | Precision required |
|------|--------------------|
| Endpoints | Method, path, when to call each |
| Request bodies | Exact JSON fields, defaults, optionals |
| Success JSON | Exact keys, types, nullability (e.g. no `vessels` when `C==1`) |
| Binary channel body | dtype, endianness, layout, length formula |
| Error shapes | `ok:false`, `error` codes, HTTP status rules |
| Client steps | Ordered algorithm from button click → existing HTML ingest |
| UI suggestions | Button label, base URL config — non-prescriptive beyond what the API needs |
| Compatibility | How to keep the old TIFF “choose file” path alongside AcqStore Server |

**Living source of truth while we build:** §7 (API) + §10 (HTML change list) in this ticket, updated when the wire format changes.  
**Handout for the other team (later):** export/freeze those sections into a short doc (e.g. `docs-dev/acqstore_server/html_integration_v0.md` or a shareable markdown/PDF) so HTML authors are not asked to read the full design ticket.

Any API change that would force HTML updates must update §7/§10 (and eventually the handout) in the same change.

### 2.2 Handouts optimized for Claude-written HTML

The calcium HTML is authored almost entirely by **Claude** (Claude.ai Artifacts / chat iteration) on the other team’s side. Every roadmap or integration note we give them must be written so that Claude can implement against it with **little to no guessing**.

**Write for the LLM implementer, not for a human skimming prose.** Prefer:

| Do | Avoid |
|----|--------|
| Exact endpoints, methods, JSON keys, types, nullability | “Something like…” / vague summaries |
| Full example request + full example success + full example error JSON | Partial snippets missing required fields |
| Binary rules as formulas (`byteLength = height * width * 4`, LE float32, row-major) | “Send the pixel data somehow” |
| Ordered numbered client algorithm (button → fetch → decode → `setImage`) | Loose narrative |
| Explicit hook into **existing** HTML symbols (`setImage`, `msPerLine`, `umPerPixel`, `dualMode`, `channels.ocamp` / `fitc`) | Inventing new analysis APIs they must invent |
| “Do not change X / keep TIFF path” constraints | Open-ended refactors |
| One dual-channel and one single-channel worked example | Only the happy dual-channel path |
| Copy-pasteable JS skeleton in one fenced block | Scattered pseudo-code |

**Tone for handouts:** imperative, contract-first, minimal background. Put design rationale in *our* tickets; put only wire + steps in the external Claude prompt/doc.

Assume the other developers will paste our handout into Claude as the primary instruction alongside their current HTML file. If a detail is underspecified, Claude will invent it — so leave no gaps in the contract.

---

## 3. End-user workflow (v0)

Decided workflow (server does **not** auto-open a browser):

1. User opens whichever calcium HTML revision they have **in a normal browser** (`file://` or any local HTTP host they use).
2. User starts **AcqStore Server** (CLI during development; packed `.app` later).
3. Server prints / shows the bound URL and port (e.g. `http://127.0.0.1:8767`).
4. HTML exposes a new control, e.g. **“Load from AcqStore Server”** (name TBD by HTML authors).
5. That control calls the server; the **server** shows a native file picker; user selects `.oir` / `.czi` / etc.
6. Server decodes via `AcqImage` and returns payload; HTML calls its existing ingest path (`setImage` + set `msPerLine` / `umPerPixel`).

The HTML file itself is **not** vendored or patched in this repo. We only **specify the HTTP contract** and send required client changes back to the HTML developers.

---

## 4. Clarification: browser “Choose file” vs native dialog

### What the HTML does today

The control under **1. Load Image → Calcium channel → Choose file** uses a browser `<input type="file">`.

That does **not** give JavaScript a reliable absolute filesystem path such as `/Users/you/data/scan.oir`.

For security, the browser typically gives a **`File` object** (name + size + MIME + a readable **byte stream** / `ArrayBuffer`). The current HTML uses that stream (`file.arrayBuffer()` → in-page `parseTiff` / image decode). Path is unavailable or not trustworthy for server-side open.

### What we propose instead

Yes: the option described as **native open dialog in Python**.

Flow:

```text
HTML button "Load from AcqStore Server"
    → POST http://127.0.0.1:<port>/api/v1/pick-and-open
    → AcqStore Server shows OS file dialog (same machine)
    → user picks file
    → server opens with AcqImage
    → response: calibration + channel pixel bytes
    → HTML assembles Float32 rows and calls setImage(...)
```

This is **not** the browser file picker for OIR. The browser only triggers the server; the server owns the dialog and the path.

Optional later: `POST /api/v1/open` with an explicit `path` for scripted/dev use (no dialog).

---

## 5. Product decisions (locked for this design)

| # | Topic | Decision |
|---|--------|----------|
| 1 | Platforms | **macOS first**; Windows exe near-future follow-on |
| 2 | Name | **AcqStore Server** / package `acqstore_server` |
| 3 | HTML in repo | **No**. Contract only; HTML authors implement the button + client |
| 4 | Formats | **All formats `AcqImage` / loaders support**; extend `acqstore` if needed |
| 5 | File choose UX | **(A)** Native dialog on server via **`POST /api/v1/pick-and-open`** |
| 6 | Path policy | **Recommend:** localhost-only + allow any readable path chosen via dialog or explicit open; optional root allowlist later |
| 7 | Shell UX | **(C)** Server only — **no** auto-open browser/window for calcium HTML |
| 8 | Port visibility | Fixed default port + print to console; optional tiny status page at `GET /` |
| 9 | Transfer encoding | Metadata JSON + binary channel bodies (see §7) |
| 10 | Channel defaults | `calciumChannel=0`, `vesselChannel=1` when `C>=2`; overridable |
| 11 | Channel counts | `C==1` → single-channel; `C>2` → only requested indices |
| 12 | Payload shape | **Calcium-oriented roles** in v0 (`calcium` / `vessels`) plus neutral `source` metadata (see §7) |
| 13 | Repo home | **Monorepo:** `src/acqstore_server/` + `packaging/acqstore_server/` (fourth top-level package). Extract to external repo later if needed |
| 14 | Packaging scripts | `packaging/acqstore_server/` parallel to `packaging/macos/` |
| 15 | Dependencies | **`acqstore` + thin server shell** (FastAPI and/or NiceGUI OK). **No** `cloudscope` / `nicewidgets` |
| 16 | Bind address | **`127.0.0.1` only** for v0 (see §8) |
| 17 | Release train | **Decide later**; develop locally first |

---

## 6. Repository layout (proposed)

```text
src/
  acqstore/              # existing backend (dependency)
  nicewidgets/           # unchanged; not used by this app
  cloudscope/            # unchanged; not used by this app
  acqstore_server/       # NEW fourth package — runtime
    __init__.py          # empty
    __main__.py          # python -m acqstore_server
    app.py               # ASGI/FastAPI (or NiceGUI) app factory
    api/
      v1.py              # routes
    open_service.py      # AcqImage open + plane extract + calibration map
    dialogs.py           # native file picker
    schemas.py           # request/response TypedDicts / pydantic models
    session_store.py     # short-lived binary session for channel GETs
    static/              # optional tiny status page assets only

packaging/
  acqstore_server/       # NEW — nicegui-pack / PyInstaller scripts later
    build_app.sh
    _config.sh
    ...

docs-dev/cursor_tickets/
  036_acqstore_server_design.md   # this file (API source of truth for now)
```

**Critical decision recorded:** stay **inside the CloudScope monorepo** for v0 so the app shares `uv.lock` and in-tree `acqstore` without publishing a private wheel. A future split into a standalone git repo that depends on released `acqstore` remains open (§12).

---

## 7. HTTP API contract (source of truth for HTML authors)

Base URL (default): `http://127.0.0.1:8767`

All responses include CORS headers allowing browser pages loaded from `file://` or other local origins to call the API (required for the agreed workflow).

### 7.1 Health

`GET /api/v1/health`

```json
{
  "ok": true,
  "app": "acqstore_server",
  "version": "0.1.0",
  "bind": "127.0.0.1:8767"
}
```

### 7.2 Pick and open (primary HTML button target)

`POST /api/v1/pick-and-open`

Request body (optional overrides; all fields optional):

```json
{
  "calciumChannel": 0,
  "vesselChannel": 1,
  "extensions": [".oir", ".czi", ".tif", ".tiff", ".nd2"]
}
```

Behavior:

1. Show native file dialog on the server machine.
2. If user cancels → `200` with `{ "ok": false, "error": "cancelled" }` (or `409`; prefer `200` + `ok:false` so fetch clients stay simple).
3. If user selects a path → same success payload as `/api/v1/open`.

### 7.3 Open by path (dev / scripting)

`POST /api/v1/open`

```json
{
  "path": "/Users/you/data/20260709_A131_0015.oir",
  "calciumChannel": 0,
  "vesselChannel": 1
}
```

Notes:

- Prefer **JSON body** over path-in-URL (`/api/v1/open/<path>`), to avoid encoding / Windows path issues.
- `path` must be absolute and readable on the server host.

### 7.4 Success payload (metadata)

```json
{
  "ok": true,
  "sessionId": "8f3c2a…",
  "source": {
    "path": "/Users/you/data/20260709_A131_0015.oir",
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
      "url": "/api/v1/session/8f3c2a…/channel/calcium"
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
      "url": "/api/v1/session/8f3c2a…/channel/vessels"
    }
  }
}
```

Single-channel files omit `channels.vessels` (or set it `null`). HTML should set `dualMode: false` in that case.

### 7.5 Channel binary download

`GET /api/v1/session/{sessionId}/channel/{role}`

- `role` ∈ `calcium` | `vessels`
- Body: raw little-endian **float32**, length `height * width`
- Layout: **row-major**, index `(y * width + x)` — matches assembling `Float32Array` rows for the HTML `state.raw` shape `[height][width]`
- `Content-Type: application/octet-stream`
- Sessions expire after a short TTL (e.g. 10 minutes) or after both roles fetched

**Why not JSON arrays of pixels?** Too large/slow. Raw f32 is what the page effectively uses after TIFF decode.

**v0 alternative (optional implementation shortcut):** single `multipart/mixed` response on `pick-and-open` / `open` containing JSON part + binary parts. If implemented, document as `Content-Type: multipart/...` and keep the two-step URLs as the stable long-term contract.

### 7.6 Errors

```json
{ "ok": false, "error": "cancelled", "message": "User cancelled file dialog" }
{ "ok": false, "error": "path_not_found", "message": "..." }
{ "ok": false, "error": "unsupported_format", "message": "..." }
{ "ok": false, "error": "channel_out_of_range", "message": "..." }
{ "ok": false, "error": "decode_failed", "message": "..." }
```

HTTP status: `400` / `404` / `422` / `500` as appropriate; `cancelled` may be `200` with `ok:false`.

### 7.7 Calibration mapping (server)

Use `AcqImage.get_image_physical_units()` → `(step_y, step_x)`.

For line-scan kymographs (documented AcqImage contract):

- `step_y` ≈ seconds per line  
- `step_x` ≈ µm per pixel  

Map for HTML:

- `msPerLine = step_y * 1000`
- `umPerPixel = step_x`
- Also return raw `stepYSeconds` / `stepXUm` for transparency

If units are missing or non-finite, return `ok:false` with `error: "calibration_unavailable"` **or** return null calibration fields and let HTML keep manual defaults — **implementation ticket must pick fail-fast vs soft**. Recommendation: **fail-fast with clear message** when header claims line-scan but units missing; soft-null when format truly has no calibration.

### 7.8 Dual-channel from one file (HTML-facing intent)

Today’s HTML UX assumes two file picks. Reality for multi-channel OIR:

- **One** file open
- **Two** planes (indices 0/1 by default)
- **One** shared calibration and shape

Server owns the split; HTML authors should not require two AcqStore Server round-trips for a 2-channel OIR.

---

## 8. Security (question 16 explained)

**Bind `127.0.0.1` only** means the API accepts connections from the same machine, not from other computers on the LAN/internet.

Why:

- The API can open arbitrary local files and return pixel data.
- A `0.0.0.0` bind would let other machines trigger dialogs / read files if they can reach the port.

v0 rules:

- Listen on `127.0.0.1` only.
- No auth token required on localhost for v0 (simplicity); revisit if shared-machine risk matters.
- CORS: allow browser origins needed for local HTML (`null` for `file://` is awkward — server should reflect permissive localhost CORS for v0, documented as lab-tool tradeoff).

---

## 9. Server process UX (no auto-open HTML)

Aligned with decision (C):

- Starting the app starts the HTTP server only.
- User opens calcium HTML themselves.
- Console (and optional `GET /` status page) shows: app name, version, bind URL, health link, “waiting for pick-and-open…”.
- Native dialog appears only when HTML calls `pick-and-open`.

Native dialog implementation notes (implementation ticket):

- Prefer a small, reliable macOS path (e.g. `osascript` / `NSOpenPanel` via a proven helper, or `tkinter.filedialog` if acceptable in frozen app).
- Dialog must run on the main/UI-capable thread as required by the chosen toolkit.
- Packaging must retain whatever library that needs.

---

## 10. HTML author change list (seed for the precise roadmap)

Conceptual client changes keyed to **today’s HTML ingest surface** (`setImage`, dual-channel opts, calibration inputs). Names for new UI chrome are suggestions only.

1. Add button **Load from AcqStore Server** (or equivalent).
2. Configurable base URL defaulting to `http://127.0.0.1:8767` (or discover via `GET /api/v1/health`).
3. On click: `POST /api/v1/pick-and-open` with optional channel overrides.
4. On success: `GET` each channel `url` → `Float32Array` of length `height*width` → reshape to `[height][width]` rows (row-major).
5. Set `$('msPerLine')` / `$('umPerPixel')` (and matching ranges if present) from `calibration`.
6. Call existing `setImage(calcium, source.path, { dualMode, channels })` when vessels present; single-channel `setImage` otherwise.
7. Keep existing TIFF dual-file Choose file UI for backward compatibility.
8. Handle `{ ok: false, error: "cancelled" }` without treating it as a hard failure.

We do **not** patch their HTML in this monorepo. As implementation stabilizes, expand this section into the **standalone HTML integration handout** (§2.1) with copy-pasteable request/response examples and a worked dual-channel + single-channel example.

---

## 11. Scope

### In scope (design locked; implement in follow-on tickets)

- New package `src/acqstore_server/`
- `POST /api/v1/pick-and-open`, `POST /api/v1/open`, channel binary GET, health
- `AcqImage`-based open for all supported formats
- Localhost bind, CORS for local HTML clients
- Calibration mapping to HTML fields
- Dual-channel default indexing
- Dev CLI: `uv run python -m acqstore_server`
- Unit tests for open_service / calibration / API (fake AcqImage or fixtures)
- Design note = this file

### Explicitly out of scope for first implementation

- Vendoring or patching `neuronal_calcium_*.html` in git
- CloudScope GUI button / shared CloudScope process
- Windows pack (design-ready; implement later)
- Codesign / notarize / public release train
- Upload-bytes open path (browser File → multipart) — optional later
- Analysis logic (ROI, events, etc.) — stays in HTML
- Changing `acqstore` public API unless open reveals a real gap (then a focused acqstore ticket)

---

## 12. Open follow-ups

- Publish vs keep monorepo-only forever.
- Windows packaging clone of macOS scripts.
- Whether to add optional upload-bytes endpoint for remote HTML hosts.
- Channel naming heuristics beyond index defaults (Olympus dye names).
- Whether reference attachments on OIR should ever map to vessels instead of channel 1.
- Auth / token for localhost if shared lab machines require it.

---

## 13. Suggested implementation ticket sequence

1. **Scaffold** `src/acqstore_server/` + `python -m` entry + health on `127.0.0.1:8767`.
2. **`open_service`**: path → AcqImage → planes + calibration schema (tests first).
3. **Binary session** channel GETs.
4. **`pick-and-open`** native dialog wiring (macOS).
5. **CORS + external HTML smoke** against a local copy of the colleague HTML (manual).
6. **Packaging** `packaging/acqstore_server/` (later ticket).
7. **Handout** one-page “HTML integration notes” exported from §7–§10 for the colleague.

---

## 14. Relation to CloudScope desktop app

CloudScope already is a NiceGUI/local server with `acqstore` inside. Hosting this HTML inside CloudScope was considered and **rejected** as the distribution plan:

- Clear product boundary for the colleague tool.
- Avoid dual UX in one `.app`.
- AcqStore Server can still share packaging *technology* (`nicegui-pack` / PyInstaller patterns from `packaging/macos/`).

A CloudScope button that starts this server remains a possible later convenience; not part of v0.

---

## 15. Decision log (this conversation)

- Sidecar path-open API preferred over in-browser OIR decode.
- Separate mini app preferred over embedding in CloudScope.
- User workflow: HTML in browser + server process + HTML button → native dialog.
- Package name: `acqstore_server` / AcqStore Server.
- Monorepo fourth package (confirmed).
- Single call `pick-and-open` (confirmed).
- Full `AcqImage` surface, not OIR-only.
- No HTML vendoring; contract-driven collaboration with HTML authors.

---

## 16. Handoff checklist for implementers

- [ ] Read §7 as API source of truth; do not invent alternate response keys without updating this doc.
- [ ] Do not import `cloudscope` or `nicewidgets`.
- [ ] Do not add the colleague HTML into git without an explicit ticket.
- [ ] Prefer fail-fast on invalid paths / channel indices.
- [ ] Record test commands and results in the **implementation** ticket report when code lands.
- [ ] Keep `__init__.py` empty per monorepo policy.
