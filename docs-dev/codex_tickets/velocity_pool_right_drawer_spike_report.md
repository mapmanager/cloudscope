# Velocity pool right drawer spike

## Files changed

- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/header_view.py`
- `tests/cloudscope/test_header_view.py`
- `tests/cloudscope/test_home_page_pool_drawer.py`

## Summary of implementation

- Added `SHOW_VELOCITY_POOL_RIGHT_DRAWER = False` (default off) parallel to the existing embedded-pool flag; left `SHOW_EMBEDDED_VELOCITY_POOL` and its splitter/SmartExpansion path unchanged.
- When the drawer flag is True, home page constructs a separate `VelocityPoolView`, builds it into a top-level `ui.right_drawer` (560px, bordered, closed by default), and syncs `show()` / `hide()` on drawer open/close.
- Extended `build_main_header` with optional `on_pool_drawer_toggle`; home passes a toggle callback only when the drawer flag is True.
- Dev header button **Pool Drawer** appears next to **Open Pool** when enabled, with tooltip `Toggle velocity pool in right drawer (dev)`.

## Tests added or modified

- Modified: `tests/cloudscope/test_header_view.py` (signature includes `on_pool_drawer_toggle`)
- Added: `tests/cloudscope/test_home_page_pool_drawer.py` (flag defaults, drawer width constant, header callback default)

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_home_page_pool_drawer.py tests/cloudscope/test_header_view.py
uv run pytest
```

## Test results

- Focused: 11 passed
- Full suite: 1273 passed

## Concerns or follow-ups

- Manual UX spike: set `SHOW_VELOCITY_POOL_RIGHT_DRAWER = True` and verify Plotly sizing when the drawer first opens.
- Plotly may need an explicit relayout hook on drawer open if plots render at zero width.
- When the spike succeeds, consider wiring **Open Pool** to the drawer and retiring Option C pool window.

---

# Right drawer empty-content fix

## Files changed

- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/views/velocity_pool_view.py`
- `tests/cloudscope/test_velocity_pool_view.py`

## Summary of implementation

- **Root cause:** server-side `drawer.toggle()` from the header did not fire `.on('update:model-value')`, so `VelocityPoolView` stayed at `root.visible=False` after build with `initially_visible=False`.
- **Fix:** after `toggle()`, explicitly sync visibility from `drawer.value`; use `pool_drawer.on_value_change(...)` for client-side close.
- Moved drawer helpers into the `SHOW_VELOCITY_POOL_RIGHT_DRAWER` guard so flag-off builds have no drawer scaffolding.
- Drawer column height: `h-[calc(100vh-4rem)]` (matches header offset, same idea as `pool_page`).
- `VelocityPoolView.on_show()` clears `_disposed` so refresh/events work after drawer open.
- Reset `SHOW_VELOCITY_POOL_RIGHT_DRAWER = False` as ship default.

## Tests added or modified

- Added: `test_on_show_clears_disposed` in `tests/cloudscope/test_velocity_pool_view.py`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_velocity_pool_view.py tests/cloudscope/test_home_page_pool_drawer.py
uv run pytest
```

## Test results

- Focused: 22 passed
- Full suite: 1274 passed
