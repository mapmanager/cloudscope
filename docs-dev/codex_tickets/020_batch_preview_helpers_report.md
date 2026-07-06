# Ticket 020 — AcqStore batch preview helpers

## Summary

Added read-only AcqStore helpers for planning batch-analysis rows before a
batch starts. These helpers mirror the useful parts of the old kymflow preview
behavior while staying backend/UI-neutral and side-effect free.

CloudScope currently uses only rectangular ROIs for velocity and diameter
analysis, so the shared ROI intersection defaults to rectangular ROI ids only.

## Files changed

- `src/acqstore/acq_image/analysis/batch/preview.py`
  - Added `BatchPreviewOutcome`.
  - Added `BatchPreviewRow`.
  - Added `roi_intersection_across_acq_images(...)`.
  - Added `preview_batch_rows(...)`.
- `tests/acqstore/test_batch_preview.py`
  - New focused tests for ROI intersection and preview rows.
- `docs/codex_tickets/020_batch_preview_helpers_report.md` (this report).

## Implementation notes

- Preview helpers are read-only:
  - no ROI creation,
  - no analysis creation/removal,
  - no analysis execution.
- `roi_intersection_across_acq_images(..., rect_only=True)` returns sorted ROI
  ids that exist on every file and are rectangular.
- `preview_batch_rows(...)` reports:
  - `pending / "add new ROI per file"` for `ADD_NEW_ROI`.
  - `skipped_missing_roi` for missing or non-rectangular existing ROI ids.
  - `pending / "will run"` for existing ROI rows with no prior primary analysis.
  - `pending / "will replace existing <analysis>"` for same-analysis reruns.
  - `skipped_conflict / "conflict with <other-analysis>"` for opposite primary
    analysis conflicts.
- The module lives under `acqstore` because the preview rules depend on backend
  ROI and analysis-set semantics. It does not import from `cloudscope`.

## Tests added or modified

Added `tests/acqstore/test_batch_preview.py` with coverage for:

- Rect-only ROI intersection.
- Missing existing ROI preview skip.
- `ADD_NEW_ROI` preview without mutating ROI state.
- Same-analysis existing result reported as replacement.
- Opposing primary-kymograph analysis reported as conflict skip.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_batch_preview.py \
              tests/acqstore/test_radon_batch.py \
              tests/acqstore/test_diameter_batch.py -q
uv run pytest -q
```

## Test results

Targeted:

```text
15 passed in 0.88s
```

Full suite:

```text
751 passed, 3 warnings in 2.69s
```

The warnings are pre-existing:

- `PytestCollectionWarning` for `TestEvent`.
- Two `RuntimeWarning: All-NaN slice encountered` warnings from raster-service
  tests.

## Concerns or follow-ups

- Preview helpers deliberately do not decide whether a dialog should block the
  Run button. They provide row outcomes; the CloudScope dialog can choose how to
  present and summarize them.
- The preview row outcome type is separate from final `BatchFileOutcome` because
  preview can contain `pending`, which is not a runtime result.
