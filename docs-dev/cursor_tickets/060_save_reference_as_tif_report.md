# 060 — Save reference image as TIFF

## Files changed

- `src/acqstore/acq_image/acq_image.py`
- `src/cloudscope/events/files.py`
- `src/cloudscope/controllers/load_save_controller.py`
- `src/cloudscope/views/reference_image_view.py`
- `tests/acqstore/test_tiff_export.py`
- `tests/cloudscope/test_load_save_controller.py`
- `tests/cloudscope/test_reference_image_view.py`
- `docs-dev/cursor_tickets/060_save_reference_as_tif_report.md`

## Summary of implementation

Added the public backend API:

```python
AcqImage.save_reference_as_tif(
    path,
    *,
    imagej_metadata=True,
    overwrite=False,
)
```

The API exports the complete reference array, including every channel. It
builds an `AcqPixels` snapshot from `ReferenceImage` dimensions, coordinate
scales, and coordinate units, then delegates to the existing
`save_pixels_as_tif` implementation. ImageJ X/Y resolution is therefore
written from the reference image's spatial calibration. Scan paths and line
ROIs are metadata only and are not rendered into exported pixels.

The API raises `ValueError("Acquisition has no reference image: ...")` when no
reference exists and preserves the standard TIFF overwrite contract.

CloudScope now provides **Save Reference As Tif** below the Reference Image
viewer. The button is enabled only after a real reference image loads and
publishes `SaveReferenceAsTifIntent`; `LoadSaveController` owns native save
dialog and browser-download orchestration. Suggested output names use
`<source-stem>-reference.tif`.

## Tests added or modified

- Backend export writes the complete multichannel reference array.
- ImageJ unit and X/Y resolution match reference calibration.
- Scan paths are not burned into pixels.
- Missing-reference and overwrite behavior.
- Suggested reference TIFF filename.
- Native, browser-download, and cancellation controller paths.
- Reference viewer intent publication and enabled/disabled button state.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_tiff_export.py \
  tests/acqstore/ome_zarr/test_tiff_export_imagej_metadata.py -q
```

```bash
uv run pytest tests/cloudscope/test_load_save_controller.py -q
```

```bash
uv run pytest tests/cloudscope/test_reference_image_view.py \
  tests/cloudscope/test_left_toolbar_view.py -q
```

```bash
uv run pytest tests/acqstore/test_tiff_export.py \
  tests/acqstore/ome_zarr/test_tiff_export_imagej_metadata.py \
  tests/cloudscope/test_load_save_controller.py \
  tests/cloudscope/test_reference_image_view.py \
  tests/cloudscope/test_left_toolbar_view.py -q
```

## Test results

- Backend TIFF tests: **9 passed**
- Load/save controller tests: **40 passed**
- Reference view and left-toolbar tests: **23 passed**
- Combined focused suite: **72 passed**
- `git diff --check`: passed

## Concerns or follow-ups

- Live CloudScope browser verification was explicitly deferred by the user.
- The existing unrelated Ruff warning for the pre-existing unused
  `LoadWarning` import in `load_save_controller.py` remains unchanged.
- `packaging/acqstore_server/` was already untracked and was not modified.
