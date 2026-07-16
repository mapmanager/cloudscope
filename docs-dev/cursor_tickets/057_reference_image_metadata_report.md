# 057 — Reference image metadata in AcqImage

## Files changed

- `src/acqstore/acq_image/metadata.py` — `REFERENCE_IMAGE_METADATA_SCHEMA`,
  `ReferenceImageMetadata`, label normalization helper
- `src/acqstore/acq_image/acq_image.py` — optional sidecar key, section wiring,
  lazy build, `is_dirty` avoids force-decoding reference
- `tests/acqstore/test_metadata.py`
- `tests/acqstore/test_acq_image_sidecar.py`
- `tests/acqstore/test_oir_file_loader.py`
- `tests/acqstore/test_file_loader_factory.py`
- `docs-dev/cursor_tickets/057_reference_image_metadata_handoff.md` (plan)
- `docs-dev/cursor_tickets/057_reference_image_metadata_report.md` (this file)

## Summary of implementation

When a file has a reference/overview image, `AcqImage` now exposes a third
metadata section `reference_image_metadata` and persists it as an optional
sidecar key (sidecar version stays **2**).

Subset fields (all **read-only** in v1):

- `shape`, `dims`, `sizes`, `dtype`, `num_channels`
- `physical_unit_y`, `physical_unit_x`, `physical_label_y`, `physical_label_x`

Labels normalize `micrometer` / `µm` → `um`. Values are built from the loader
`ReferenceImage` snapshot (OIR scales already corrected in ticket 056).

Lifecycle notes:

- Section is included in `get_metadata_sections()` only when
  `has_reference_image` is true.
- Sidecar write includes the key only when a reference exists.
- Sidecar load accepts the optional key; v1 does not override file-derived
  calibration.
- `is_dirty` does **not** decode reference pixels (preserves the “schema row
  does not reopen OIR” contract).

## Tests added or modified

- Unit: `ReferenceImageMetadata` values + reject edits
- Sidecar: OIR save includes key; round-trip; unknown-key warning regression
- OIR: metadata matches plane scales; debug 0010 matches primary X / TXT
- Factory: TIF still two sections; OIR exposes three

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_metadata.py \
  tests/acqstore/test_acq_image_sidecar.py \
  tests/acqstore/test_oir_file_loader.py \
  tests/acqstore/test_file_loader_factory.py -q
```

## Test results

- **72 passed**

## Concerns or follow-ups

- CloudScope GUI metadata widget for reference section (out of scope v1).
- Editable reference calibration / sidecar override (deferred).
- `acqstore_server` open JSON exposure (deferred).
- CZI-specific metadata fixture test not added (no dedicated CZI-with-reference
  assertion beyond existing reference-image loader coverage).
