# 021 — Page-level layout chrome restore (left toolbar + right pool)

## Summary

Restores user-visible **page layout** across client disconnect/reconnect (and
desktop sleep/wake): the left toolbar's open state + active tab, and the right
analysis-pool panel's open state + selected tab.

- **Cleaned `HomePageChromeState`** to represent real home-page shell chrome:
  - Kept `file_list_open` and `analysis_plot_open` (both verified live —
    `analysis_plot_open` drives `acq_analysis_plot` show/hide and
    `_sync_analysis_reference_layout`).
  - Removed dead fields: `reference_image_open` (reference image was moved off
    the home page to the left toolbar) and `velocity_pool_open` (the embedded
    pool is gated off by `SHOW_EMBEDDED_VELOCITY_POOL = False`).
  - Added `left_toolbar_active_view_id: str | None` (the left toolbar is open
    exactly when this is not `None`, so a separate `left_toolbar_open` bool was
    intentionally not added) and `right_pool_open: bool`.
  - Replaced `from_panel_open(...)` with `HomePageChromeState.capture(...)`.
- **No `splitter_values` in chrome.** Splitter drag positions are already
  persisted by `SplitterManager` into `AppConfig` (in memory across reconnect,
  to disk on shutdown). Only the left-toolbar/right-pool open toggles — which
  `SplitterManager.value_for()` deliberately forces closed at startup — needed
  to be captured, and those are the two new booleans above.
- **`LeftToolbarView(initial_active_view_id=...)`** applies the restored tab at
  build time via `_apply_active_view(...)`; unknown/foreign ids collapse safely
  (`_resolve_initial_active_view_id`).
- **`VelocityPoolViewState(active_tab=...)`** restores the right pool's
  Velocity/Peaks tab using the standard `export/apply_session_state` path
  (tab is selection-independent, so no selection guard).
- `home_page.py` seeds/reads chrome accordingly, applies the left-tab and
  right-pool open state during build, and captures the new chrome at disconnect.

Restore is applied at **build time** from `runtime.session_snapshot.chrome`;
true build-time delivery of per-view blobs remains deferred (unchanged).

## Files changed

Source:

- `src/cloudscope/session_state.py` — rework `HomePageChromeState` fields,
  `defaults()`, new `capture()`, updated `to_dict`/`from_dict`.
- `src/cloudscope/views/left_toolbar_view.py` — add `initial_active_view_id`
  param, `_resolve_initial_active_view_id()`, apply on build.
- `src/cloudscope/views/velocity_pool_view.py` — add `VelocityPoolViewState`
  and `export_session_state` / `apply_session_state`.
- `src/cloudscope/pages/home_page.py` — import `ViewId`; drop `reference_image`
  panel key and simplify `_sync_analysis_reference_layout`; compute + pass
  `initial_left_toolbar_tab`; restore `right_pool_open` at build; capture new
  chrome in `_on_client_disconnect`.

Docs:

- `docs-dev/cloudscope/dev-roadmap-reconnect.md` — add ticket 021 to
  "Implemented so far".

Tests:

- `tests/cloudscope/test_session_state.py` — chrome round trip updated to new
  fields; added `capture` + collapsed-left-toolbar test.
- `tests/cloudscope/test_left_toolbar_view.py` — valid/unknown initial active
  tab resolution.
- `tests/cloudscope/test_velocity_pool_view.py` — `VelocityPoolViewState`
  round trip, unknown-tab fallback, and export/apply active-tab behavior.

## Tests run

```bash
uv run pytest tests/cloudscope/test_session_state.py tests/cloudscope/test_debug_view.py tests/cloudscope/test_left_toolbar_view.py tests/cloudscope/test_velocity_pool_view.py tests/cloudscope/test_controller.py tests/cloudscope/test_splitter_manager.py -q
uv run pytest -q
```

## Test results

- Focused run: 72 passed.
- Full suite: 1889 passed, 45 skipped (pre-existing missing-fixture skips), 17
  warnings (pre-existing).

## Concerns / follow-ups

- Chrome restore was verified by unit tests only. Live disconnect/reconnect
  verification in the running app (left toolbar tab + right pool tab visibly
  restored) is not part of this ticket and should be confirmed manually.
- Restoring `left_toolbar_active_view_id == EXPERIMENT_METADATA` while blinded
  mode is active would activate that tab on build; `_on_tab_clicked` guards
  user clicks but `_apply_active_view` does not. Left as-is (out of scope);
  the button is still disabled by `_refresh_button_state`.
- Two pre-existing Ruff long-line warnings in `home_page.py` (unrelated) remain.
- The embedded velocity pool (`SHOW_EMBEDDED_VELOCITY_POOL = False`) retains a
  local `panel_open_state['velocity_pool']` default; it is no longer part of the
  serialized chrome contract.
