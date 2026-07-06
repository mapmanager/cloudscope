# 105 — Right pool splitter drag freeze

## Files changed

- `src/cloudscope/views/splitter_manager.py`
- `src/cloudscope/pages/home_page.py`
- `tests/cloudscope/test_splitter_manager.py`

## Summary

Added generic `SplitterManager.set_splitter_drag_enabled()` that pins a splitter's
Quasar `limits` to the current value when drag is disabled, and restores the
preset limits when re-enabled (avoids dimmed `disable` styling).

Wired for the **right velocity-pool splitter only**:

1. `set_right_pool_open(False)` — collapse then freeze drag.
2. `set_right_pool_open(True)` — unfreeze then restore open width.
3. After `register(RIGHT_POOL, …)` on home page — freeze when startup is closed.
4. `update:model-value` on the right pool splitter — re-freeze after user drag
   collapses the panel.

Left toolbar splitter is unchanged.

**Recommendation followed:** pool view/NicePool tabs already skip MVC subscriptions
while closed (lazy build + `BaseView` show/hide). No controller gating added;
backend pool controllers still keep `AcqImageList` pools in sync while the panel
is collapsed.

## Tests added or modified

- Extended `test_splitter_manager_right_pool_open_closed` to assert limit pin/restore.
- Added `test_splitter_manager_set_splitter_drag_enabled_pins_limits`.
- Added `test_splitter_manager_right_pool_startup_closed_freezes_drag`.
- `FakeSplitter` now tracks `limits` for drag-freeze assertions.

## Test commands run

```bash
uv run pytest tests/cloudscope/test_splitter_manager.py -q
```

## Test results

All tests in `tests/cloudscope/test_splitter_manager.py` passed.

## Concerns or follow-ups

- Browser verification of drag feel on native/web was not run in this pass; unit
  tests cover manager behavior only.
- If backend pool rebuild cost while closed becomes a concern, gate
  `VelocityPoolController` / `SumIntensityPoolController` separately.
