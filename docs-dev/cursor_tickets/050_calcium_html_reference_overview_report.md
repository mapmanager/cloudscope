# 050 — Calcium HTML reference overview + multiline open logs

## Files changed

- `src/acqstore_server/open_service.py` — multiline indented open summary; reference
  size + reference physical units lines
- `tests/acqstore_server/test_open_service.py` — assert indented log lines
- `clients/neuronal_calcium_linescan/neuronal_calcium_linescan_analyzer_v1_18.html`
  - CSS/UI/JS: collapsible **Reference overview** card after Image Display
  - Fetch `reference.channels[*]`, draw transposed plane + scanPath/lineRoi
  - Clear on TIFF load / Reset
- `clients/neuronal_calcium_linescan/README.md`
- `docs-dev/cursor_tickets/050_calcium_html_reference_overview_report.md`

## Summary of implementation

### Server open logs

After a successful open:

```text
Opened NAME in N ms
  dims=…
  shape=… C=…
  calcium[i]=HxW vessels=…
  msPerLine=… umPerPixel=…
  units stepY=…s stepX=… um
  reference=none
  # or:
  reference=channels=N HxW
  reference units stepY=… {yUnit} stepX=… {xUnit}
```

Reference units use API fields: `dx` → stepY (row), `dy` → stepX (column).

### HTML reference card (050)

- Plain HTML/CSS `.card.collapsible` (already in the analyzer — not NiceGUI).
- Placed after Image Display, before Trace Display.
- Same display policy as `/demo/`: dim0→canvas X, dim1→canvas Y; overlay in
  reference pixel coords with the demo `toCanvas` mapping.
- TIFF load / Reset clears the panel.

## Tests added or modified

- `test_open_path_logs_header_summary` updated for multiline format.

## Exact test commands run

```bash
uv run pytest tests/acqstore_server/test_open_service.py tests/acqstore_server/test_logging_setup.py -q
```

## Test results

**12 passed** focused (`test_open_service` + `test_logging_setup`). Multilevel open log verified manually for TIFF.

## Concerns / follow-ups

- Manual: Load OIR via AcqStore and confirm reference card expands with path overlay.
- Optional: auto-scroll native status log to bottom (051 follow-up).
