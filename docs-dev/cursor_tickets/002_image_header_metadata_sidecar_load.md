# 002 — Image header calibration sidecar load

## Files changed

- `src/acqstore/acq_image/acq_image.py`
- `src/acqstore/acq_image/metadata.py`
- `tests/acqstore/test_acq_image_sidecar.py`
- `tests/acqstore/test_metadata.py`

## Summary of implementation

Hydrate **editable** image-header calibration from the AcqImage JSON sidecar on
load. Structural header fields (shape, dims, dtype, channel count, etc.) remain
authoritative from the file loader on every open.

Changes:

1. **`ImageHeaderMetadata`** — added `editable_field_names`,
   `editable_patch_from_sidecar`, and `apply_sidecar_calibration`. The sidecar
   patch is filtered to schema-editable keys only
   (`physical_unit_x/y`, `physical_label_x/y`). Application reuses
   `update_values` validation and `replace_header`, then clears the dirty flag.

2. **`AcqImage._apply_loaded_sidecar_payload`** — calls
   `_apply_image_header_metadata_from_sidecar` after experiment metadata. Invalid
   calibration values log a warning and are skipped (policy B); the rest of the
   sidecar still loads. Non-dict `image_header_metadata` still fails the whole
   sidecar (structural JSON error).

3. Removed Phase 1 “save only, do not hydrate” comments on the sidecar path.

Native `.cs.ome.zarr` embedded sidecars use the same `_apply_loaded_sidecar_payload`
path — no extra work.

## Tests added or modified

**`tests/acqstore/test_acq_image_sidecar.py`**

- Replaced `test_load_ignores_image_header_values_in_json_phase1` with:
  - `test_load_round_trip_restores_image_header_calibration`
  - `test_load_applies_partial_image_header_calibration_patch`
  - `test_load_ignores_non_editable_image_header_sidecar_keys`
  - `test_load_tolerates_invalid_image_header_calibration`

**`tests/acqstore/test_metadata.py`**

- `test_image_header_metadata_sidecar_patch_filters_editable_keys_only`
- `test_image_header_metadata_apply_sidecar_calibration_updates_without_dirty`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_image_sidecar.py tests/acqstore/test_metadata.py -q
```

## Test results

```
34 passed in 0.07s
```

## Concerns or follow-ups

- Invalid calibration currently skips the **entire** calibration patch (same as
  `update_values` merge semantics), not individual bad keys. Acceptable for now
  given the four editable fields are applied as one logical unit.
- No `docs/` update per ticket scope.
