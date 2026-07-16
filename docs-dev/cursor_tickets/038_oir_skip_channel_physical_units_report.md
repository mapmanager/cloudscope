# 038 — OIR skip channel physical units (`C` / `S`)

## Problem

Loading true multi-channel OIR files (dims include `C`) failed during header read:

```text
TypeError: unsupported operand type(s) for -: 'numpy.str_' and 'numpy.str_'
```

`oirfile` stores channel **names** in `coords['C']` and omits `C` from
`coord_scales`. `_physical_units_for_oir_header` fell back to
`_step_from_coord`, which subtracted the first two channel-name strings.

Older fixtures often listed two channel metadata entries but only one plane in
the pixel map, so `C` was squeezed out of `dims` and the bug was latent.

## Files changed

- `src/acqstore/acq_image/file_loaders/oir_file_loader.py`
- `tests/acqstore/test_oir_file_loader.py`
- `docs-dev/cursor_tickets/038_oir_skip_channel_physical_units_report.md`

## Summary of implementation

- `_physical_units_for_oir_header`: for dims `C` and `S`, append `None` step and
  empty label `""`; do not call `_step_from_coord`.
- `_step_from_coord`: return `None` when the coordinate array dtype is not
  numeric (defense in depth).
- Left unused legacy helper `_physical_units_for_header` unchanged (out of scope).
- After `ImageHeader.with_coerced_physical_calibration()`, channel axis becomes
  step `1.0` / label `"Pixels"` (existing coercion policy). Y/X analysis spacing
  is unchanged.

## Tests added or modified

- `test_step_from_coord_returns_none_for_string_channel_names`
- `test_physical_units_for_oir_header_skips_channel_dim_c`
- `test_physical_units_for_oir_header_skips_sample_dim_s`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_oir_file_loader.py -v
```

Manual:

```bash
uv run python -c "
from acqstore.acq_image.acq_image import AcqImage
AcqImage('tmp/Example OCaMP-FITC Data/20260709_A131_0021.oir', load_images=True, load_analysis_csv=False)
AcqImage('tests/acqstore/data/oir-samples/20251030_A106_0002.oir', load_images=False, load_analysis_csv=False)
"
```

## Test results

- `tests/acqstore/test_oir_file_loader.py`: **14 passed**
- Manual new 2-channel OIR: load OK; dims `('C','Y','X')`; coerced units
  `(1.0, Y_step, X_step)`; labels `('Pixels', 'seconds', 'micrometer')`
- Manual old kymograph fixture: load OK; dims `('Y','X')` unchanged

## Concerns or follow-ups

- **Ticket B:** bump `oirfile` from 2026.4.25 to latest; lockfile; retest OIRs.
- Audit CZI / ND2 loaders for similar categorical-axis step subtraction (CZI
  already special-cases `C` with `nan`).
- Do not commit large sample OIRs under `tmp/` unless a dedicated fixture ticket
  adds a small multi-`C` file.
- After merge to `main`, merge `main` into `feature/acqstore_server`.
