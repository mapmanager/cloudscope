# AcqStore Server v2 onboarding docs — client sufficiency evaluation (v2 re-run)

**Ticket:** 066  
**Date:** 2026-07-17  
**Type:** Documentation evaluation  
**Artifact:** `scripts/acqstore_server/demo_cursor_client_v2.html`

## Method (rules followed)

1. Read **only** `docs-dev/acqstore_server/README.md`, then `docs-dev/acqstore_server/client-roadmap.md`.
2. Implement a new standalone client from that information alone.
3. **Do not** open or read any prior client HTML (including `demo_cursor_client.html`).
4. Open additional docs **only if blocked**.
5. Do **not** inspect `src/acqstore_server`, maintained `/demo/v2/`, or OpenAPI unless required.

## Prior client code — explicit confirmation

| Question | Answer |
|----------|--------|
| Was `scripts/acqstore_server/demo_cursor_client.html` opened or read? | **No** |
| Was the maintained demo (`/demo/v2/` or static demo sources) opened or read? | **No** |
| Was any prior client HTML copied, pasted, or diffed into this file? | **No** |
| Was `demo_cursor_client_v2.html` written from scratch using the onboarding docs + ordinary Canvas/JS knowledge? | **Yes** |

Code taken from the **onboarding roadmap itself** (not from a prior client file): `decodeFloat32LittleEndian`, `transposePlane`, endpoint URLs, and open/delete error-check patterns as published in `client-roadmap.md`.

## Files changed

| File | Change |
|------|--------|
| `scripts/acqstore_server/demo_cursor_client_v2.html` | New standalone HTML client |
| `docs-dev/cursor_tickets/066_acqstore_server_onboarding_docs_eval_v2_report.md` | This report |

No server code modified. No files under `src/acqstore_server` opened.

## Summary of implementation

Lifecycle from the roadmap:

1. Health — `GET /api/v2/health`
2. Capabilities — `GET /api/v2/capabilities`
3. Open — `POST /pick-and-open` or `POST /open`
4. Display `opened.source`
5. Display `opened.header`
6. Fetch `channels[0].dataUrl`, validate `byteLength`, decode little-endian Float32
7. Optional client-side transpose; Canvas grayscale display
8. Delete — `DELETE /api/v2/sessions/{sessionId}`

## Live verification

- Server already listening at `http://127.0.0.1:8767`
- Client served at `http://127.0.0.1:8901/demo_cursor_client_v2.html`
- Fixture used for `/open` (not listed in onboarding docs; found via filesystem search):  
  `tests/acqstore/data/oir-samples/20251030_A106_0007.oir`

Browser status lines observed:

```text
health ok
capabilities ok
opened …
plane drawn
deleted …
```

Plane: `shape=[30000, 22]`, `byteLength=2640000`, canvas matched shape.

## Tests added or modified

None (docs evaluation + HTML artifact only).

## Exact test commands run

```bash
curl -sS http://127.0.0.1:8767/api/v2/health
# POST /open, GET plane bytes, DELETE session (curl)
python3 -m http.server 8901 --directory scripts/acqstore_server
# browser MCP exercise of demo_cursor_client_v2.html
```

## Test results

API curl path and browser UI path both completed health → open → plane → delete successfully.

---

## Evaluation answers

### 1. Did the onboarding documentation alone allow you to build the client?

**Yes.**

### 2. Exactly where did you become blocked?

**Not blocked.** Soft gaps filled without extra AcqStore docs:

- Canvas Float32 → grayscale recipe (general JS knowledge)
- Capabilities TTL field name (show whole JSON; not required for first plane viewer)
- Sample absolute path for repo testing (filesystem fixture search; UI also supports pick-and-open)

### 3. Which additional files did you open?

**None** for documentation or client reference.

### 4. Why did you open each one?

N/A.

### 5. Which information should have been added to `client-roadmap.md`?

1. Short Canvas (or Plotly) Float32 display snippet  
2. Example `/capabilities` JSON naming `sessionTtlSeconds`  
3. Note on serving the HTML over `http://` and CORS to the server origin  
4. Optional sample absolute path for CloudScope checkout testing  

### 6. Did you need to inspect implementation code?

**No.**

### 7. If yes, why?

N/A.

### 8. Estimate how long a new JavaScript developer would need to become productive

- First working viewer: **about 45–90 minutes**  
- Polished first UI: **about 2–4 hours**

### 9. Rate the onboarding documentation (1–10)

**8.5 / 10**

### 10. Recommend the smallest set of documentation improvements required

1. Canvas grayscale render example after Float32 decode  
2. Sample capabilities response (or explicit TTL field name)  
3. One paragraph on hosting the standalone page (`http://` vs `file://`, CORS)

---

## Concerns or follow-ups

- This re-run intentionally avoided reading `demo_cursor_client.html` so the sufficiency claim is not contaminated by prior client code.
- Evaluation artifact only; not a replacement for the maintained `/demo/v2/` client.
