# 047 — Demo load bottleneck measurement + client fork docs

## Files changed

- `docs-dev/acqstore_server/README.md` — vendored HTML client path + edit rules
- `clients/neuronal_calcium_linescan/README.md` — fork provenance + edit rules
- `src/acqstore_server/static/demo/index.html` — stage timing (`perfPre` + console)
- `docs-dev/cursor_tickets/047_demo_load_bottleneck_measurement_report.md`

## Measurement method

1. Instrument demo: `open.http`, `fetch.*.arrayBuffer`, `draw.kymo.*`, `ALL_STAGES_TOTAL`.
2. Run server on `:8787`, open `/demo/?perf=1`.
3. CDP load via `POST /api/v1/open` of
   `tmp/Example OCaMP-FITC Data/20260709_A131_0006.oir` (2-ch + ref).

## Results (this machine, Chromium CDP)

| Stage | Time | Notes |
|-------|------|--------|
| `open.http` (disk decode + session) | **98 ms** | Server-side |
| `fetch.calcium.TOTAL` (20.5 MB) | **40 ms** | ~515 MB/s localhost |
| `draw.kymo.TOTAL` calcium | **21 ms** | sampleStep=7, preview 1429×512 |
| `fetch.vessels.TOTAL` (20.5 MB) | **22 ms** | ~927 MB/s |
| `draw.kymo.TOTAL` vessels | **18 ms** | same pyramid |
| refs (2×1 MB + draw) | **~18 ms** | combined |
| **ALL_STAGES_TOTAL** | **220 ms** | end-to-end after path known |

## Verdict

**Transfer is not the architecture bottleneck.** Localhost float32 plane GET is tens of ms for ~20 MB. Server open is ~100 ms. Client draw with sampleStep is ~20 ms/plane.

A multi-second or ~10 s demo experience is **not** explained by HTTP transfer on this path. Likely causes of a slow subjective run:

1. Older demo draw path (full-resolution pixel loop) before sampleStep.
2. Native/webview timing different from Chromium CDP (re-measure there with `perfPre`).
3. Counting wall time that includes OS file dialog, or frozen UI without reading stage labels.

**Architecture remains viable** for server → browser float32 planes on localhost. Proceeding to the 5k HTML loader is reasonable; keep `/demo/` timing panel when validating native mode.

## Tests

Manual CDP timing as above (no pytest).
