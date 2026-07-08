# 003 — Session reconnect restore

**Status:** implemented  
**Type:** implementation  
**Branch:** `feature/fix-disconnect-reconnect-bug`  
**Depends on:** `002_reconnect_plotly_refresh_report.md` (plot hydrate on reconnect)

---

## Summary

Hard reconnect (new NiceGUI client, widgets rebuilt) now captures a **session snapshot** on disconnect and restores UI chrome plus controller state through a single **`HomePageSessionReconnectRestore`** event. Selection and shared `primary_x_range` ride on the event; per-view chrome uses fail-fast `export_session_state` / `apply_session_state` blobs.

Replaces reconnect `FileSelectionChanged` republish (B1).

---

## Files changed

| File | Change |
|------|--------|
| `src/cloudscope/session_state.py` | **New** — snapshot types, `require_keys`, selection guard helpers |
| `src/cloudscope/events/session_reconnect.py` | **New** — `HomePageSessionReconnectRestore` event |
| `src/cloudscope/runtime.py` | `session_snapshot`, `reconnect_build_in_progress` |
| `src/cloudscope/controllers/home_page_controller.py` | `publish_session_reconnect_restore()` replaces `republish_selection_from_state()` |
| `src/cloudscope/views/base_view.py` | Reconnect handler, export/apply defaults, suppress hydrate during reconnect build |
| `src/cloudscope/views/view_manager.py` | `collect_session_state()` |
| `src/cloudscope/pages/home_page.py` | Disconnect capture, `build(reconnect=)`, chrome restore, publish restore |
| `src/cloudscope/views/file_list_tree_view.py` | Tree expansion export/apply |
| `src/cloudscope/views/acq_analysis_plot_view.py` | Plot display export/apply, reconnect x-range cache |
| `src/cloudscope/views/sum_intensity_plot_view.py` | Plot display export/apply, reconnect x-range cache |
| `src/cloudscope/views/primary_image_view.py` | Z/T/contrast/viewport/display export/apply |
| `src/nicewidgets/tree_widget/tree_widget.py` | `expanded_group_ids()` tracking (additive) |
| `src/nicewidgets/tree_widget/js_hooks.py` | Expand/collapse JS hooks |
| `tests/cloudscope/test_session_state.py` | **New** |
| `tests/cloudscope/test_controller.py` | Updated reconnect publish test |
| `tests/nicewidgets/test_tree_widget_expanded_groups.py` | **New** |
| `tests/cloudscope/test_home_page_build.py` | `build(reconnect=)` fake |

---

## Architecture

### Disconnect

1. `HomePageSessionSnapshot(chrome, views)` captured from `panel_open_state` + `ViewManager.collect_session_state()`
2. Stored on `CloudScopeRuntime.session_snapshot`
3. `on_hide()` on all views

### Reconnect

1. `HomePage.build(reconnect=True)` — chrome from snapshot; views skip build-end / `on_show` data hydrates
2. `publish_session_reconnect_restore(snapshot)` — one `HomePageSessionReconnectRestore` (after lazy load)
3. `BaseView._on_session_reconnect_restore` — selection + x-range + `apply_session_state` + one `on_session_reconnect_restore()`

### Fail-fast blobs

- `schema_version: 1` required
- Apply uses `data["key"]` (no silent `.get()` defaults)
- `display_options` via `dataclasses.asdict` / `Dataclass(**dict)`

### Dual viewport note

- Kymograph / synced 1D x-range: `event.primary_x_range`
- 2D µm image pan/zoom: `primary_image` blob `viewport_xy` applied after raster load

---

## Tests added or modified

- `tests/cloudscope/test_session_state.py`
- `tests/cloudscope/test_controller.py` — `test_publish_session_reconnect_restore_publishes_current_state`
- `tests/nicewidgets/test_tree_widget_expanded_groups.py`
- `tests/cloudscope/test_home_page_build.py`

## Test commands

```bash
uv run pytest tests/cloudscope/test_session_state.py tests/cloudscope/test_controller.py tests/nicewidgets/test_tree_widget_expanded_groups.py
uv run pytest
```

## Test results

- Focused: 12 passed
- Full suite: **1781 passed**, 17 skipped

## Concerns / follow-ups

- Manual sleep/reconnect verification for file-list open state, tree expansion, x-range, primary viewport
- Left toolbar open/tab not yet in chrome snapshot (page composer or `LeftToolbarView` export)
- Normal file-change path still publishes separate `PrimaryXRangeChanged` (reconnect-only unification)
