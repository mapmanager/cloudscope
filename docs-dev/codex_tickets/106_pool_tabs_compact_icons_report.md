# 106 — Pool view compact tabs with icons

## Files changed

- `src/cloudscope/views/velocity_pool_view.py`
- `tests/cloudscope/test_velocity_pool_view.py`
- `.cursor/rules/shared-module-discipline.mdc`

## Summary

Tightened the Velocity / Peaks horizontal tab strip in the right-panel pool view:

- Added tab icons inline: Velocity `speed`, Peaks `functions` (same Material names as
  left toolbar; not extracted to a shared module per user steering).
- Applied Quasar compact props on `ui.tabs`: `dense`, `align=left`, `inline-label`,
  `narrow-indicator`, `no-caps`.
- Removed tab-panel padding via Tailwind `p-0` and scoped CSS under
  `.velocity-pool-tab-panels`.
- Reduced tab min-height/padding via scoped CSS under `.velocity-pool-tabs`.

Added Cursor rule `shared-module-discipline.mdc` to balance KISS vs reflexive
shared-module extraction.

## Tests added or modified

- Added `test_velocity_pool_view_builds_compact_tabs_with_icons`.

## Test commands run

```bash
uv run pytest tests/cloudscope/test_velocity_pool_view.py -q
```

## Test results

All tests in `tests/cloudscope/test_velocity_pool_view.py` passed (16).

## Concerns or follow-ups

- Browser visual pass on right pool (light/dark, narrow width) recommended to
  confirm tab strip height meets expectations.
