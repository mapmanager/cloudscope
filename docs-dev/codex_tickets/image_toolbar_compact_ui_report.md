# Image toolbar compact UI

## Files changed

- `src/nicewidgets/image_toolbar_widget/image_toolbar_widget.py`
- `src/nicewidgets/contrast_widget/contrast_widget.py`
- `src/cloudscope/views/image_toolbar_view.py`
- `tests/nicewidgets/test_contrast_widget.py`

## Summary of implementation

Compacted the home-page image toolbar row without changing intent or behavior.

**ImageToolbarWidget**

- Replaced outlined selects with built-in labels by external `ui.label` + compact `ui.select` pairs (`standout dense`, `w-28`, no `bg-white`).
- Kept ROI action buttons on the same host row; OK/Cancel remain text buttons.

**ContrastWidget**

- Applied the same external-label + compact select pattern for Color LUT (`w-28`, `standout dense`).
- Kept the Auto button as text.
- Tightened internal spacing (`gap-1`), range cap (`max-w-48`), and min/max label width (`w-8`).

**ImageToolbarView**

- Reduced host row padding/gap (`gap-1 py-0 px-1`).

Font sizing continues to come from `setUpGuiDefaults(text_size)` at page build time (currently `AppConfig` default `text-sm`). Switching the app default to `text-xs` and verifying desktop/web entry points is deferred to a follow-up ticket.

## Tests added or modified

- Modified: `tests/nicewidgets/test_contrast_widget.py` (updated range/label width class assertions).

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_image_toolbar_widget.py tests/nicewidgets/test_image_toolbar_widget_handlers.py tests/nicewidgets/test_contrast_widget.py tests/cloudscope/test_image_toolbar_view.py -q
```

## Test results

66 passed in 2.04s

## Concerns or follow-ups

- **App-wide `text-xs` default:** Audit that home page, pool page, and desktop launcher paths all call `setUpGuiDefaults` with `text-xs` (or change `DEFAULT_TEXT_SIZE` in `AppConfig`) so widget styling does not rely on per-control `classes('text-sm')`.
- **Visual check:** Confirm compact selects and contrast range look correct in both light and dark mode (no hard-coded `bg-white`).
