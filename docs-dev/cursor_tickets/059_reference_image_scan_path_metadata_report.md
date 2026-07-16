# 059 — Reference image scan-path metadata

## Files changed

- `src/acqstore/acq_image/metadata.py`
- `tests/acqstore/test_metadata.py`
- `tests/acqstore/test_acq_image_sidecar.py`
- `tests/acqstore/test_oir_file_loader.py`
- `docs-dev/cursor_tickets/059_reference_image_scan_path_metadata_report.md`

## Summary of implementation

Extended `reference_image_metadata` with scan-path fields derived from
`ReferenceImage` public API:

| Field | Visible in GUI | Notes |
|-------|----------------|-------|
| `has_scan_path` | yes | `has_scan_path()` |
| `scan_path_num_points` | yes | `N` from `get_scan_path_plot()` |
| `line_roi` | yes | `(x0, y0, x1, y1)` string or empty |
| `scan_path_x_pixels` | no | JSON list in sidecar |
| `scan_path_y_pixels` | no | JSON list in sidecar |

OIR line-scan files expose 2-point paths from `line_roi`; CZI can expose
longer polylines. Coordinate lists are stored as JSON arrays in the sidecar but
hidden in the Image Header reference card (summary fields only).

`REFERENCE_IMAGE_METADATA_SCHEMA` bumped to **version 2**. AcqImage sidecar
version remains **2**.

## Tests added or modified

- `test_reference_image_metadata_includes_scan_path_lists`
- Updated no-scan-path defaults on existing metadata test
- Sidecar OIR save asserts list-typed `scan_path_x_pixels`
- `test_oir_kymograph_reference_metadata_scan_path_matches_snapshot`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_metadata.py \
  tests/acqstore/test_acq_image_sidecar.py \
  tests/acqstore/test_oir_file_loader.py \
  tests/cloudscope/test_image_header_metadata_view.py -q
```

## Test results

- **69 passed**

## Concerns or follow-ups

- Deferred: expose reference metadata (summary only) on `acqstore_server` open
  JSON when returning to that branch.
- GUI card auto-shows new visible scan-path summary fields; no CloudScope code
  change required.
