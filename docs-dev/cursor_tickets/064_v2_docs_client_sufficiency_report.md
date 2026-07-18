# Ticket 064 — AcqStore Server v2 documentation sufficiency (Cursor demo client)

## Goal

Determine whether the AcqStore Server v2 documentation is sufficient for a new
developer to build a browser client, by building one from the documented
onboarding path and recording gaps.

## Files changed

- `scripts/acqstore_server/demo_cursor_client.html` (new)
- `docs-dev/cursor_tickets/064_v2_docs_client_sufficiency_report.md` (this report)

No server code under `src/acqstore_server/` was modified.

## Summary of implementation

Created a self-contained HTML + JavaScript client at
`scripts/acqstore_server/demo_cursor_client.html` that:

1. Calls `GET /api/v2/health`
2. Calls `GET /api/v2/capabilities`
3. Opens an acquisition via `POST /api/v2/pick-and-open` or `POST /api/v2/open`
4. Displays useful acquisition metadata (`source`, session id, channel list, plane shape)
5. Displays the AcqStore `header` JSON
6. Downloads channel 0 via the returned `dataUrl`, validates `byteLength` and sample count
7. Transposes the row-major float32 plane for display on a Canvas
8. Deletes the session via `DELETE /api/v2/sessions/{sessionId}`

The page hard-codes `http://127.0.0.1:8767` so it can be opened from `file://`
or another origin (CORS is enabled on the server).

## Live verification

Started AcqStore Server with `uv run python -m acqstore_server`, served the
client from `http://127.0.0.1:8899/`, and exercised the UI in the browser:

- Health badge: `server healthy · API v2`
- Capabilities JSON rendered
- Opened `/Users/cudmore/Sites/cloudscope/data/cond1/20251030_A106_0002.oir`
- Session created; header and metadata rendered
- Canvas painted with non-trivial pixel data (`grayMin=2`, `grayMax=224`, size `1000×32` after aspect-safe scaling of the transposed `24×30000` linescan)
- Session deleted; subsequent `GET` returned `session_not_found`

## Tests added or modified

None. This was a documentation evaluation plus a standalone demo HTML file, not
a pytest change.

## Exact test commands run

```bash
uv run python -m acqstore_server
curl -s http://127.0.0.1:8767/api/v2/health
curl -s http://127.0.0.1:8767/api/v2/capabilities
# Browser UI open/download/delete against data/cond1/20251030_A106_0002.oir
```

## Test results

Manual end-to-end client workflow succeeded against a live local server.

## Critique — documentation sufficiency

### 1. What documentation was sufficient?

Once past the entry docs, these were enough to build a working client:

- `docs-dev/acqstore_server/v2/api.md` — exact endpoints, JSON shapes, binary
  media type, byteLength/sample-count validation rules, session delete contract,
  stable error envelope
- `docs-dev/acqstore_server/v2/javascript-client.md` — complete reusable
  `fetch` helpers, little-endian float32 decode, transpose helper, CORS /
  absolute `dataUrl` note for external pages, session TTL guidance
- The maintained demo at `src/acqstore_server/static/demo/v2/index.html` —
  definitive Canvas rendering / transpose / open / delete behavior

Together, `api.md` + `javascript-client.md` + the demo are sufficient for an
independent developer who already knows how to start the server.

### 2. What documentation was confusing?

- **Entry hierarchy mismatch.** Root `README.md` says “Everything under
  `reference/` is lookup documentation”, but the tree has `v2/` (and `v1/`),
  not `reference/`. The roadmap also says “consult the documents under
  `reference/`”. A new developer following those links literally hits a dead
  end.
- **Roadmap is too thin to stand alone.** It lists endpoint names and says
  “transpose the plane” / “little-endian Float32” but omits base URL, request
  bodies, response fields, how to obtain the binary URL, validation rules, and
  CORS/`dataUrl` absolute-URL handling. A developer who obeys “Only after
  completing this workflow should you consult `reference/`” cannot finish the
  workflow from the roadmap alone.
- **Transpose ambiguity.** The roadmap says “Transpose the plane before
  displaying it” as if it were a required API rule. `javascript-client.md`
  correctly frames it as a *client display decision* because the server never
  transposes. The maintained demo always transposes; a reader can reasonably
  wonder whether skipping transpose is a contract violation.
- **How to start the server is underspecified in the roadmap.** “Run the
  packaged AcqStore Server.app or start the server from Python” gives no
  command, port, or link. Default `http://127.0.0.1:8767` appears only later
  in `api.md` / `javascript-client.md`.
- **Header vs plane calibration units.** Live `.oir` responses can show axis
  `unit` values of `"Y"` / `"X"` rather than `"seconds"` / `"micrometer"` as in
  the documented example. The examples are illustrative (stated), but a new
  client author may treat them as normative.

### 3. What assumptions were required?

- Default server bind is `http://127.0.0.1:8767` (not in the roadmap).
- JSON field names use camelCase aliases (`sessionId`, `dataUrl`,
  `byteLength`, `sourceDtype`, …) as shown in examples — confirmed by live
  responses and OpenAPI-style schemas.
- Relative `dataUrl` values must be prefixed with the server origin when the
  HTML page is not same-origin with the API (required for this standalone
  `scripts/` client; documented only in `javascript-client.md`).
- CORS is enabled for browser clients (documented in `javascript-client.md`).
- `Float32Array` over an `ArrayBuffer` is safe because the platform is
  little-endian (matching `raw-f32-le`); the JS guide’s `DataView` path is
  the more portable decode.
- Transpose is a display convention for this product’s linescan-heavy data,
  not a server-enforced transform.
- For headless verification, `POST /api/v2/open` with an absolute path is
  usable even when the native picker cannot be automated; the roadmap
  presents pick-and-open first without explaining that distinction.

### 4. Which reference documents were actually opened?

Per instructions, started with only:

1. `docs-dev/acqstore_server/README.md`
2. `docs-dev/acqstore_server/client-roadmap.md`

Then, because the roadmap was insufficient to implement steps 4–7, opened:

3. `docs-dev/acqstore_server/v2/api.md`
4. `docs-dev/acqstore_server/v2/javascript-client.md`
5. `src/acqstore_server/static/demo/v2/index.html` (maintained demo)
6. `src/acqstore_server/v2/routes.py` (to confirm binary headers / session
   delete behavior against the docs)

Not opened for this evaluation: `v2/README.md`, `architecture.md`,
`errors.md`, `demo.md`, `client-handoff.md`, OpenAPI UI, or tickets.

### 5. What information should have been in `client-roadmap.md` but was missing?

Minimum additions so the roadmap can be followed without immediately leaving it:

1. Default base URL: `http://127.0.0.1:8767` and `API = …/api/v2`
2. How to start the server from source (`uv run python -m acqstore_server`) and
   that the packaged app is equivalent
3. Exact open request bodies (`{}` for pick-and-open; `{path}` for open)
4. That a successful open returns `sessionId`, `source`, `header`, `plane`,
   `channels[].dataUrl` / `byteLength`
5. Binary fetch steps: `GET` absolute `SERVER + dataUrl`, `cache: 'no-store'`,
   validate `byteLength`, decode LE float32, reshape with `plane.shape`
6. Explicit note: server does **not** transpose; client may transpose for
   display (with a one-line why for linescans)
7. Correct pointer to follow-on docs: `v2/api.md` and `v2/javascript-client.md`
   (not a non-existent `reference/` folder)
8. Link to the maintained demo URL when the server is running:
   `http://127.0.0.1:8767/demo/v2/`
9. CORS + external-page `dataUrl` absolute-prefix rule
10. Cancelled picker returns HTTP 200 with `ok: false` / `error: "cancelled"`
11. Session TTL comes from capabilities; clients should DELETE when finished

### 6. Estimate — time to productivity for a new developer

| Path | Estimate |
|---|---|
| Follow roadmap only, refuse to open other docs | Blocked / incomplete client |
| Roadmap → `v2/javascript-client.md` + copy patterns | **2–4 hours** to a working single-plane viewer |
| Also study `api.md` + maintained demo for edge cases (cancel, errors, reference image, TTL) | **1 day** to a production-minded thin client |
| Without `javascript-client.md` (api.md + OpenAPI + demo only) | **1–2 days**, with more trial-and-error on binary decode / `dataUrl` origin |

Overall: documentation is **sufficient if the developer ignores the roadmap’s
“don’t look at reference yet” instruction and opens `v2/javascript-client.md`
immediately**. The declared onboarding path is not self-sufficient.

### 7. Recommended concrete documentation improvements

1. **Fix the hierarchy labels** in `README.md` and `client-roadmap.md`: replace
   `reference/` with `v2/` (and note `v1/` is archived).
2. **Expand `client-roadmap.md`** with the checklist in §5 above, including a
   minimal code sketch or a direct link: “Copy the complete client from
   `v2/javascript-client.md`.”
3. **Clarify transpose** in the roadmap: “Optional client-side display
   transpose; server returns original row-major AcqStore planes.”
4. **Add a one-command start** to the roadmap and point at the maintained demo
   as the oracle for expected UI behavior.
5. **Keep example JSON clearly marked as illustrative**, and prefer linking to
   `/openapi.json` / `/docs` for normative field lists.
6. Consider renaming/promoting `v2/javascript-client.md` as the true Step 0
   after the roadmap’s 8-step outline, since that is where a JS developer
   actually becomes productive.

## Concerns or follow-ups

- Background `uv run python -m acqstore_server` and a temporary
  `python3 -m http.server 8899` may still be running in the agent environment
  after this ticket; stop them locally if needed.
- Live `.oir` header/axis unit strings (`"Y"`/`"X"`) differ from the
  illustrative `"seconds"`/`"micrometer"` examples; worth confirming whether
  that is expected AcqStore header content or a packaging quirk for a later
  ticket (out of scope here; server was not modified).
