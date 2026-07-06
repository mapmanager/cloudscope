# Reference image SmartExpansion default closed report

## Files changed

- `src/cloudscope/pages/home_page.py`

## Summary of implementation

Reference image `SmartExpansion` now starts collapsed on first app launch
(`initially_open=False`), matching velocity pool.

`panel_open_state['reference_image']` defaults to `False` so splitter layout
matches the collapsed expansion on first paint.

`_reset_home_expansions()` (Reset view layout) opens file list, analysis plot,
and velocity pool as before, but **closes** reference image instead of opening
it.

## Tests added or modified

None (layout-only home page default change).

## Exact test commands run

Not run (no automated coverage for home page expansion defaults).

## Test results

N/A

## Concerns or follow-ups

Manual check: cold start and Reset view layout both leave Reference image
collapsed; user can still expand it from the header during a session.
