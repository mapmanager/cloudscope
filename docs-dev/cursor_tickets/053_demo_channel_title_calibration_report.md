# 053 — Demo channel title calibration text

## Files changed

- `src/acqstore_server/static/demo/index.html`
- `docs-dev/cursor_tickets/053_demo_channel_title_calibration_report.md`

## Summary of implementation

Primary channel `h2` titles now include API plane size and HTML calibration fields after each plane is drawn:

- Format: `Channel N · {height}×{width} · {msPerLine} ms/line · {umPerPixel} µm/px`
- Size uses API order (time×space = height×width).
- Units come from `meta.calibration.msPerLine` and `meta.calibration.umPerPixel`.
- Titles reset to `Channel 0` / `Channel 1` at the start of each load; vessels show `Channel N — pending…` until drawn.

No muted hint paragraphs were added — info lives in the `h2` titles per product decision.

## Tests added or modified

None (static demo HTML only).

## Exact test commands run

None.

## Test results

N/A — static markup/JS string update only.

## Concerns or follow-ups

- Titles can get long on narrow cards; if that becomes noisy, move the calibration fragment back under a muted `<p>`.
- Float formatting is raw JSON values (no fixed precision); adjust if display looks too verbose for real files.
