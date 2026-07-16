# 056 — OIR line-scan physical units fix (seriesInterval + pixel length)

## Files changed

- `pyproject.toml` — bump `oirfile` to `>=2026.7.10,<2026.8`
- `uv.lock`
- `src/acqstore/acq_image/file_loaders/oir_file_loader.py`
- `tests/acqstore/test_oir_file_loader.py`
- `docs-dev/cursor_tickets/056_oir_linescan_physical_units_fix_report.md`

## Summary of implementation

For TIMELAPSE-on-Y line-scan OIR kymographs, `_physical_units_for_oir_header`
now sets calibration from Olympus LSMIMAGE metadata instead of raw
`oirfile.coord_scales`:

- **Y (time):** minimum positive `seriesInterval` under 30 ms from LSMIMAGE XML,
  divided by 1000 → seconds per line. Matches Olympus TXT `secondsPerLine`.
- **X (space):** `oirfile._pixel_length_x` as µm/px. Matches Olympus TXT
  `umPerPixel`. (`coord_scales['X']` was `pixel_length / nX`.)

Non-line-scan OIRs (e.g. Z-stack) unchanged. C/S channel skip unchanged.
Falls back to `coord_scales` with a warning when series interval or pixel
length is missing.

Also bumped `oirfile` to **2026.7.10** on branch `debug/oir-units-and-reference`
(reference-image fixes; physical units still required loader change).

## Tests added or modified

- Updated fake-scene line-scan expectations (seriesInterval + pixel_length_x).
- Updated multi-channel equal-`coord_scales` case to expect distinct Y/X steps.
- Updated kymograph fixture to Olympus TXT SoT (~0.001142 s, ~0.274 µm/px).

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_oir_file_loader.py -q
```

Manual verification on `tmp/oir-debug` (no JSON sidecars):

```bash
uv run python - <<'PY'
# paired OIR vs TIF+TXT for 0010/0011/0012 — all matched within tolerance
PY
```

## Test results

- `tests/acqstore/test_oir_file_loader.py`: **14 passed**
- `tmp/oir-debug` paired checks:
  - `20260709_A131_0010` OIR vs TIF: Y/X match
  - `20260709_A131_0011` OIR vs TIF: Y/X match
  - `20260709_A131_0012` OIR vs TIF: Y/X match
  - `20251014_A98_0002` (1ch, no TIF pair): Y≈0.001134 s, X≈0.291 µm/px

## Concerns or follow-ups

- Merge `debug/oir-units-and-reference` → `main`, then `main` →
  `feature/acqstore_server` so server `calibration.dim_*` picks up fixed values.
- Add `scripts/acqstore/debug_oir_loader.py` for repeatable `tmp/oir-debug`
  matrix (deferred).
- Validate 2-channel reference `(C,Y,X)` display after oirfile 7.10 on real app.
- Sidecar JSON (`file.oir.json`) can override header calibration in CloudScope;
  use sidecar-free paths when validating loader output.
