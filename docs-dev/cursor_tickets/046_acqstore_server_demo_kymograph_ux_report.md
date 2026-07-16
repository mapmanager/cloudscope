# 046 — AcqStore Server demo kymograph UX + status

## Files changed

- `src/acqstore_server/static/demo/index.html` — calcium-HTML sampleStep pyramid +
  offscreen `drawImage`; fetch/draw timing; layout/status UX
- `src/acqstore_server/status_ui.py` — single **Open log** (default app)
- `docs-dev/acqstore_server/README.md` — demo-must-track-API policy
- `docs-dev/cursor_tickets/046_acqstore_server_demo_kymograph_ux_report.md`

## Summary of implementation

Long line-scan OIRs (`Y≈10000`, `X≈512`) were drawn as ~`960×49` hairline strips inside a tall empty black wrap after transpose+contain fit. That looked like “only one empty channel” and hid reference panels below the fold.

Demo now:

1. **Calcium-HTML display pyramid:** `displaySampleStepForTime` + `kymographToImageData`
   (subsample along time) → `putImageData` on offscreen → `drawImage` to visible canvas
   (same strategy as `neuronal_calcium_linescan_analyzer_v1_18` `matrixToImageData` /
   `getDisplayImageCanvas`).
2. **Scroll-X layout** for extreme aspect ratios: fill height, horizontal scroll for time.
3. **Progressive status** with fetch vs draw timing (`fetched X MB in N ms — drawing…`).
4. **Vessels card** unhidden as soon as open meta says dual-channel.
5. **Open log** single button (default app), CloudScope-style; removed redundant reveal/folder.
6. Docs note: API edits must update `/demo/` in the same ticket.

## Tests added or modified

None (static demo). Manual browser verification against `/api/v1/open` with
`tmp/Example OCaMP-FITC Data/20260709_A131_0006.oir`.

## Exact test commands run

```bash
# Server already on :8787; browser CDP load via /api/v1/open
```

## Test results

Browser: open payload C=2 + reference×2; calcium/vessels canvases tall enough to read;
status progresses; both reference panels render with scan path.

## Concerns or follow-ups

- Restart / hard-refresh native app if an old demo HTML is cached in a frozen build.
- Plane fetch vs draw: localhost GET of ~20 MB float32 is ~20 ms; multi-second
  “Fetching vessels…” was mostly **client canvas draw** (~1.2M pixels). Demo now
  caps at 400k pixels and prints fetch/draw ms in the status line + console.
- Status UI: single **Open log** (default app), matching CloudScope App Info —
  removed redundant Reveal log / Open log folder.
