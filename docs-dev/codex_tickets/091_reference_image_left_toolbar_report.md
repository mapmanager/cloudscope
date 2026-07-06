# 091 Reference Image left toolbar tab

## Files changed

- `src/cloudscope/views/view_ids.py`
- `src/cloudscope/views/left_toolbar_view.py`
- `src/cloudscope/pages/home_page.py`
- `tests/cloudscope/test_left_toolbar_view.py`

## Summary of implementation

Added a **Reference Image** tab (icon `image`) to the left toolbar, placed after Sum Intensity and before Config. The tab hosts a second `ReferenceImageView` instance via a thin `LeftPanelReferenceImageView` subclass that uses `ViewId.LEFT_TOOLBAR_REFERENCE_IMAGE` so it can register alongside the existing main-panel reference image view.

`LeftToolbarView` now accepts `dark_mode`, `dark_mode_provider`, and `raster_display_cache` and passes them to the left-panel reference image child. `home_page.py` supplies the same theme/cache args used by the main SmartExpansion reference image. The existing SmartExpansion reference image panel was not modified.

## Tests added or modified

- `tests/cloudscope/test_left_toolbar_view.py` — assert `LeftPanelReferenceImageView` child and updated `panel_view_ids`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_left_toolbar_view.py
```

## Test results

1 passed in 1.53s (`tests/cloudscope/test_left_toolbar_view.py`).

## Concerns or follow-ups

- Two reference image views can be visible at once (left toolbar tab + main SmartExpansion). This is intentional for the UX experiment.
- If the left-tab reference image feels cramped, consider a taller plot height for the left-panel instance only (would require a small subclass override of `build()`).
