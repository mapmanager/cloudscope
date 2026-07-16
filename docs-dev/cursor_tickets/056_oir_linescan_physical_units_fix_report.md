# 056 — OIR line-scan physical units + reference spatial scales

## Files changed

- `pyproject.toml` — bump `oirfile` to `>=2026.7.10,<2026.8`
- `uv.lock`
- `src/acqstore/acq_image/file_loaders/oir_file_loader.py`
- `tests/acqstore/test_oir_file_loader.py`
- `docs-dev/cursor_tickets/056_oir_linescan_physical_units_fix_report.md`

## Summary of implementation

### Primary image (line-scan kymograph)

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

### Reference image (overview / linescan context)

Olympus TXT `[Reference Image]` carries pixel shape and total field size in µm
(e.g. 512×512 px, 169.706×169.706 µm → ~0.331 µm/px). TIF exports have no
reference pixels, but the TXT sidecar still documents reference calibration.

`oirfile.reference.coord_scales` are coordinate-array deltas
(`pixel_length / n_pixels`), not µm/px — wrong by ~512× for axis scaling.

New helpers in `oir_file_loader.py`:

- `_oir_reference_spatial_coord_scales()` — override `Y`/`X` with parent
  `OirFile._pixel_length_x` / `_pixel_length_y` (µm/px).
- `_reference_snapshot_from_oir_reference()` — passes pixel lengths when
  building `ReferenceImage`.
- `OirFileLoader.reference_image` — supplies parent pixel lengths from open
  `OirFile`.

Reference `plane.dx` / `plane.dy` now match primary spatial X and Olympus TXT
reference µm/px (`169.706 / 512`).

Also bumped `oirfile` to **2026.7.10** on branch `debug/oir-units-and-reference`
(reference 2-channel `(C,Y,X)` loading; scale fix is loader-side).

## Tests added or modified

- Updated fake-scene line-scan expectations (seriesInterval + pixel_length_x).
- Updated multi-channel equal-`coord_scales` case to expect distinct Y/X steps.
- Updated kymograph fixture to Olympus TXT SoT (~0.001142 s, ~0.274 µm/px).
- `test_oir_reference_spatial_coord_scales_override` — unit test for override.
- `test_oir_kymograph_reference_plane_matches_primary_spatial_x` — ref dx/dy ≈ primary X.
- `test_oir_debug_0010_reference_matches_primary_x_and_txt_um_per_pixel` — vs TXT 169.706/512.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_oir_file_loader.py -q
```

Manual verification on `tmp/oir-debug` (no JSON sidecars):

```bash
uv run python - <<'PY'
# primary + reference for all oir-debug OIRs; ref dx/dy == primary X == TXT um/px
PY
```

## Test results

- `tests/acqstore/test_oir_file_loader.py`: **17 passed**
- `tmp/oir-debug` paired checks (primary Y/X vs TIF+TXT):
  - `20260709_A131_0010` OIR vs TIF: Y/X match
  - `20260709_A131_0011` OIR vs TIF: Y/X match
  - `20260709_A131_0012` OIR vs TIF: Y/X match
  - `20251014_A98_0002` (1ch, no TIF pair): Y≈0.001134 s, X≈0.291 µm/px
- `tmp/oir-debug` reference scales (post-fix):
  - All four OIRs: ref `(512, 512)`, `dx == dy == primary X`
  - `0010`: `dx ≈ 0.331456` vs TXT `169.706/512 ≈ 0.331457`

## Concerns or follow-ups

- Merge `debug/oir-units-and-reference` → `main`, then `main` →
  `feature/acqstore_server` so server `calibration.dim_*` picks up fixed values.
- Add `scripts/acqstore/debug_oir_loader.py` for repeatable `tmp/oir-debug`
  matrix (deferred).
- Validate 2-channel reference `(C,Y,X)` display after oirfile 7.10 on real app.
- Sidecar JSON (`file.oir.json`) can override header calibration in CloudScope;
  use sidecar-free paths when validating loader output.
- **Next:** persist reference calibration in AcqImage sidecar — see
  `057_reference_image_metadata_handoff.md`.
