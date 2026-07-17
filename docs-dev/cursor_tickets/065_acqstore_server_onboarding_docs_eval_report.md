# AcqStore Server v2 onboarding docs — client sufficiency evaluation

**Ticket:** 065  
**Date:** 2026-07-17  
**Type:** Documentation evaluation (not a server implementation ticket)  
**Artifacts:** `scripts/acqstore_server/demo_cursor_client.html`

## Method

1. Read **only** `docs-dev/acqstore_server/README.md`, then `docs-dev/acqstore_server/client-roadmap.md`.
2. Implement a standalone browser client from that information alone.
3. Open additional documentation **only if blocked**.
4. Do **not** inspect `src/acqstore_server`, the maintained `/demo/v2/` client, or OpenAPI unless required.

## Files changed

| File | Change |
|------|--------|
| `scripts/acqstore_server/demo_cursor_client.html` | Created/replaced: single-file pure JS client (fetch + Canvas) |
| `docs-dev/cursor_tickets/065_acqstore_server_onboarding_docs_eval_report.md` | This report |

No server code was modified. No files under `src/acqstore_server` were opened or changed.

## Summary of implementation

The client implements the roadmap lifecycle:

1. Health (`GET /api/v2/health`)
2. Capabilities (`GET /api/v2/capabilities`)
3. Open via pick-and-open or absolute path (`POST /api/v2/pick-and-open` / `POST /api/v2/open`)
4. Display `opened.source` metadata
5. Display `opened.header`
6. Fetch `channels[0].dataUrl`, validate `byteLength`, decode little-endian Float32
7. Render plane to Canvas (optional client-side transpose)
8. Delete session (`DELETE /api/v2/sessions/{sessionId}`)

## Live verification

Server: `uv run python -m acqstore_server` at `http://127.0.0.1:8767`  
Client served from: `http://127.0.0.1:8899/demo_cursor_client.html`  
Test acquisition (repo fixture, not documented in onboarding):  
`tests/acqstore/data/oir-samples/20251030_A106_0007.oir`

Browser log (abbreviated):

```text
Health OK
Capabilities received
Opened session …
Plane decoded and drawn to Canvas
Deleted session …
```

Observed plane: `shape=[30000, 22]`, `byteLength=2640000`, Canvas size matched shape. Cross-origin fetch from `:8899` → `:8767` succeeded (CORS worked without extra docs).

## Tests added or modified

None (documentation evaluation + standalone HTML artifact only).

## Exact test commands run

```bash
uv run python -m acqstore_server
curl -sS http://127.0.0.1:8767/api/v2/health
curl -sS http://127.0.0.1:8767/api/v2/capabilities
# open / download / delete via curl against a local .oir fixture
python3 -m http.server 8899 --directory scripts/acqstore_server
# browser MCP: exercise demo_cursor_client.html end-to-end
```

## Test results

- Health and capabilities: OK, match roadmap expectations
- Open + binary plane + delete: OK via curl and via the HTML client in the browser
- Canvas display: OK (min/max grayscale stretch of Float32 plane)

---

## Evaluation answers

### 1. Did the onboarding documentation alone allow you to build the client?

**Yes.** The two onboarding documents were sufficient to implement a working standalone browser client covering all eight required steps. No additional documentation files were opened.

### 2. Exactly where did you become blocked?

**Not blocked.** Soft gaps (below) were filled with ordinary JavaScript/Canvas knowledge, not by reading more AcqStore Server docs.

Closest friction points (not hard blockers):

| Gap | How it was handled |
|-----|--------------------|
| No Canvas Float32→grayscale recipe | Used standard min/max stretch + `putImageData` |
| Capabilities TTL field name not shown | Displayed full JSON; field observed at runtime as `sessionTtlSeconds` |
| No sample absolute path for repo developers | Used `pick-and-open` path in UI; for automated check, located a repo `.oir` fixture outside the docs |
| How to host the standalone HTML page | Used a trivial `python3 -m http.server` (not documented) |

### 3. Which additional files did you open?

**None** for documentation or implementation reference.

Files intentionally **not** opened during the build:

- `docs-dev/acqstore_server/reference/*`
- `http://127.0.0.1:8767/docs` / OpenAPI
- Maintained demo at `/demo/v2/`
- `src/acqstore_server/**`

(Runtime verification used live HTTP responses and a filesystem search for a local `.oir` fixture only.)

### 4. Why did you open each one?

N/A — no additional documentation files were opened.

### 5. Which information should have been added to `client-roadmap.md`?

Smallest high-value additions (none were required to unblock this client):

1. **Minimal Canvas display snippet** — 10–20 lines showing Float32 plane → grayscale `ImageData` (or a one-liner Plotly heatmap note). Roadmap currently stops at “render with Canvas or Plotly.”
2. **Example `/capabilities` JSON** — especially the TTL field name (`sessionTtlSeconds`) and that `binary.servedDtype` / `encoding` mirror the plane contract.
3. **Cross-origin note** — standalone pages may be served from another origin; CORS is enabled (observed working from `:8899`). Mention that `file://` may be restricted and a local static server is fine.
4. **Repo developer tip (optional)** — one absolute-path example under `tests/…` for `/open` when not using the packaged app / native picker.
5. **Header vs source** — one sentence clarifying that `source` is file/import summary and `header` is the full AcqStore acquisition header object (both were present and usable as opaque JSON).

### 6. Did you need to inspect implementation code?

**No.**

### 7. If yes, why?

N/A.

### 8. Estimate how long a new JavaScript developer would need to become productive

Assuming a mid-level browser JS developer (comfortable with `fetch`, `ArrayBuffer`, Canvas or Plotly):

| Milestone | Estimate |
|-----------|----------|
| First successful health → open → plane → delete | **45–90 minutes** |
| Polished first viewer (UI, error handling, transpose choice) | **2–4 hours** |
| Production-ready multi-channel / session management | longer; would then need `reference/` docs |

External developers using **AcqStore Server.app** + native pick-and-open should land near the low end. Source-checkout developers without a known absolute path may spend extra time locating a test file unless the roadmap adds a sample path.

### 9. Rate the onboarding documentation (1–10)

**8.5 / 10**

Strong: correct endpoint paths, request/response shape for open, cancel semantics, binary Float32LE contract, `dataUrl` origin prefixing, transpose-as-client-choice, session delete, clear “don’t start in reference/” guidance.

Deductions: display recipe omitted; capabilities TTL field name omitted; hosting/CORS and sample path tips missing.

### 10. Recommend the smallest set of documentation improvements required

Do these three in `client-roadmap.md` (no need to expand reference for first-client onboarding):

1. Add a short **Canvas grayscale render** example after the Float32 decode section.
2. Add a **sample capabilities response** (or name `sessionTtlSeconds` explicitly where TTL is mentioned).
3. Add a one-paragraph **how to run your HTML client** note: prefer `http://127.0.0.1:…` over `file://`; CORS to the server origin is supported.

Optional fourth: one **example absolute path** for CloudScope checkout testing.

---

## Concerns or follow-ups

- Treating “inspect implementation code” as a docs failure is the right bar; this evaluation did not need that.
- Prior ticket `064_v2_docs_client_sufficiency_report.md` exists from an earlier pass; this report (`065`) is an independent re-run under the mandatory two-file-first protocol.
- The HTML client is an evaluation artifact under `scripts/`, not a replacement for the maintained `/demo/v2/` reference client.
