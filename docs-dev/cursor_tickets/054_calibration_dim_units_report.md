# 054 — Additive calibration dim_* header fields

## Files changed

- `src/acqstore_server/schemas.py`
- `src/acqstore_server/open_service.py`
- `src/acqstore_server/static/demo/index.html`
- `tests/acqstore_server/test_open_service.py`
- `docs-dev/cursor_tickets/054_calibration_dim_units_report.md`

## Summary of implementation

Open/pick-and-open `calibration` remains backward-compatible for the calcium HTML
client (`msPerLine`, `umPerPixel`, `stepYSeconds`, `stepXUm`, `unitsSource`
unchanged). Additive header-faithful fields for the served 2-D plane:

- `dim_0_step` / `dim_1_step` — floats (rows/Y, columns/X; same values as
  `stepYSeconds` / `stepXUm`)
- `dim_0_units` / `dim_1_units` — physical unit labels from
  `AcqImage` header (`physical_units_labels` for Y/X)

Demo channel titles now use:

`Channel N · H×W · {dim_0_step} {dim_0_units} · {dim_1_step} {dim_1_units}`

No hardcoded `ms/line` / `µm/px`. No `acqstore` package edits.

## Tests added or modified

- `tests/acqstore_server/test_open_service.py` — assert new keys exist, steps
  match existing step fields, unit labels are non-empty strings.

## Exact test commands run

```bash
uv run pytest tests/acqstore_server/test_open_service.py tests/acqstore_server/test_api_v1.py -q
```

## Test results

20 passed, 1 warning (Starlette TestClient deprecation) in 1.76s.

## Concerns or follow-ups

- TIFF fixtures without file calibration still report labels like `Pixels`
  (header coercion). Real OIR/TXT files should surface `seconds` / `um` (or
  loader-specific labels) via these keys.
- Calcium HTML continues to ignore the new keys; no client change required.
