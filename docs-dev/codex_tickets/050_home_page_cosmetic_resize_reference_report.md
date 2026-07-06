# 050 Home Page Cosmetic Resize Reference Report

## Files changed

- `src/cloudscope/views/acq_analysis_plot_view.py`
- `src/cloudscope/views/reference_image_view.py`
- `docs-dev/codex_tickets/050_home_page_cosmetic_resize_reference_report.md`

## Summary of implementation

- Updated the analysis echart container from a fixed `h-80` height to a full-height flex layout so NiceGUI's echart `ResizeObserver` can resize the chart as the Home page splitter changes.
- Removed the internal reference image title label from `ReferenceImageView`; the outer Home page `SmartExpansion` remains responsible for displaying `Reference image`.
- Removed the internal reference image status label and stopped consuming the reference-image status message in the UI.
- Kept `_load_reference_plane_payload`'s return shape unchanged because existing tests cover its messages.

## Tests added or modified

- No tests added or modified. Existing tests cover the touched helper contract, and this change is layout/UI wiring only.

## Exact test commands run

```bash
uv run pytest
```

## Test results

- `1069 passed, 15 warnings in 3.82s`

## Concerns or follow-ups

- The echart resize behavior depends on the existing NiceGUI echart `ResizeObserver`; no custom resize hook was added.
- The reference image viewer still uses fixed `h-80` plot height as planned, since only the redundant internal text was in scope.
