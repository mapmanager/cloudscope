# 049 — Calcium HTML AcqStore linescan loader

## Files changed

- `clients/neuronal_calcium_linescan/neuronal_calcium_linescan_analyzer_v1_18.html`
  - UI: base URL + **Load from AcqStore Server** (`ACQSTORE: begin/end 049 linescan-server-load-ui`)
  - JS: health → pick-and-open → float32 rows → calibration → `setImage`
    (`049 linescan-server-load-js`, wire `049 linescan-server-load-wire`)
- `clients/neuronal_calcium_linescan/README.md` — run steps for TIFF + AcqStore paths
- `docs-dev/cursor_tickets/049_calcium_html_acqstore_loader_report.md`

## Summary of implementation

Additive load path only (contract: `html_integration_v0.md`):

1. Optional health check against configurable base URL (default `http://127.0.0.1:8767`).
2. `POST /api/v1/pick-and-open` with `{ calciumChannel: 0, vesselChannel: 1 }`.
3. Quiet return on `cancelled`; surface other errors / `load_timeout` on `#loadInfo`.
4. Fetch calcium (+ vessels if present) as LE float32 row arrays.
5. Apply `calibration.msPerLine` / `umPerPixel` (and range sliders).
6. Call existing `setImage` single or dual path (same as TIFF dual load).

**Out of scope (ticket 050):** reference overview UI / `reference.channels[*]` panels.

TIFF file inputs and **Load channel(s)** are unchanged.

## Tests added or modified

None (HTML client; no pytest harness for this file).

## Exact test commands run

```bash
uv run python -m acqstore_server   # :8767
cd clients/neuronal_calcium_linescan && uv run python -m http.server 8768 --bind 127.0.0.1
```

Browser CDP on `http://127.0.0.1:8768/neuronal_calcium_linescan_analyzer_v1_18.html`:

- Confirmed `#acqstoreLoadBtn`, `loadFromAcqStoreServer`, `fetchAcqStoreChannelRows`.
- Health OK.
- Path-based `POST /api/v1/open` (dialog not automatable) + same fetch helpers →
  `dualMode=true`, `height=10000`, `width=512` for
  `tmp/Example OCaMP-FITC Data/20260709_A131_0006.oir`.

## Test results

Smoke path succeeded (UI present; planes load into `setImage`).  
Pick-and-open dialog itself requires a manual click (native OS dialog).

## Concerns / follow-ups

- **050:** reference overview panels (optional in contract).
- Calibration values come straight from the server; this ticket does not reinterpret units.
- User should manually click **Load from AcqStore Server** once with the desktop/API server running to confirm the native dialog path end-to-end.
