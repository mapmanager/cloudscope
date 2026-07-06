# OIR axis labels report

## Files changed

- `src/acqstore/acq_image/file_loaders/oir_file_loader.py`
- `tests/acqstore/test_oir_file_loader.py`
- `docs-dev/codex_tickets/oir_axis_labels_report.md`

## Summary of implementation

Added an OIR-private header path so CZI continues using the unchanged shared
`_image_header_from_scene` / `_physical_units_for_header` helpers.

New OIR helpers:

- `_enabled_axes_from_lsmimage_xml` — parse enabled axes from public
  `xml_metadata[METADATA.LSMIMAGE]`
- `_is_y_timelapse_line_scan_axis` — detect line-scan kymographs where
  TIMELAPSE `maxSize` matches `Y`
- `_physical_units_for_oir_header` — use `coord_scales` / `coord_units` from
  `oirfile`, with `Y` relabeled to `seconds` for TIMELAPSE line scans
- `_image_header_from_oir_scene` — OIR-only header builder

`OirFileLoader._read_oir_header` now calls `_image_header_from_oir_scene`.

CZI imports and runtime behavior are unchanged.

## Tests added or modified

- `tests/acqstore/test_oir_file_loader.py`
  - XML TIMELAPSE parsing
  - fake-scene unit labels (Z-stack vs kymograph)
  - integration tests on `20251030_A106_0002.oir` and `20251030_A106.oir`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_oir_file_loader.py
uv run pytest tests/acqstore/test_czi_file_loader.py
```

## Test results

```
uv run pytest tests/acqstore/test_oir_file_loader.py tests/acqstore/test_czi_file_loader.py -v
12 passed in 0.25s
```

## Concerns or follow-ups

- `oirfile.coord_units` still reports `Y` as `µm` for line scans; CloudScope
  overrides to `seconds` using LSMIMAGE TIMELAPSE metadata.
- Consider upstream `oirfile` issue: expose line-scan time axis via public
  `coord_units` instead of requiring XML inspection.
- `# TODO` left for possible future display-name normalization (`µm` → `um`,
  `s` → `seconds`) on non-line-scan axes.
