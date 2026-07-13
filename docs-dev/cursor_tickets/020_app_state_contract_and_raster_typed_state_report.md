# 020 — App-state serialization contract + raster typed view state

## Summary

Continues the reconnect typed-state work (ticket 019) by adding a typed,
JSON-safe **app-level state contract** and extending the typed-state pilot to
the raster views.

- Added `HomePageRestorableState` — the serializable app-level subset of
  `HomePageState` (`selection`, `primary_x_range`, `file_ids`). Non-serializable
  runtime fields (`acq_image_list`, `visible_file_ids_provider`) are excluded by
  construction.
- `HomePageState.to_restorable_state()` builds it (deep-copying the selection).
- `HomePageChromeState` and `HomePageSessionSnapshot` gained `to_dict`/`from_dict`
  with schema-version and key validation. `HomePageSessionSnapshot` now carries
  `app_state`, captured at disconnect in `home_page.py`.
- `DebugView._collect_state()` now renders `snapshot.to_dict()` and stays thin
  (removed the inline snapshot-flattening logic and the unused `dataclasses`
  import).
- `PlotlyRasterViewerDisplayOptions` (nicewidgets) gained `to_dict`/`from_dict`.
  `layout_margins_profile` is intentionally excluded (a fixed construction-time
  layout concern, not user-mutable display state); `from_dict` ignores unknown
  keys and fills defaults.
- `PrimaryImageView` now uses `PrimaryImageViewState` + `RasterViewport` instead
  of a loose `asdict` blob, preserving the existing blob shape (`viewport_xy`,
  `manual_contrast_range`, etc.).
- `ReferenceImageView` gained `ReferenceImageViewState` (display options only)
  plus `export_session_state` / `apply_session_state` / `_apply_raster_display_options`.
- Removed `del visible` from `SumIntensityPlotView._on_series_visibility_changed`
  and documented why the argument is unused (widget owns visibility state).

**Restore behavior is unchanged.** `app_state` is captured for
diagnostics/serialization and future shareable-state work; reconnect restore
still reads live controller state. Moving restore to true build time and
`HomePageChromeState` field cleanup remain deferred (see roadmap).

## Files changed

Source:

- `src/cloudscope/session_state.py` — add `HomePageRestorableState`;
  `to_dict`/`from_dict` on `HomePageChromeState` and `HomePageSessionSnapshot`;
  `HomePageSessionSnapshot.app_state`.
- `src/cloudscope/controllers/home_page_controller.py` — add
  `HomePageState.to_restorable_state()`; import `HomePageRestorableState`.
- `src/cloudscope/pages/home_page.py` — capture `app_state` in
  `_on_client_disconnect`.
- `src/cloudscope/views/debug_view.py` — use `snapshot.to_dict()`; drop unused
  `dataclasses` import.
- `src/nicewidgets/raster_viewer/frontend/plotly_display_options.py` — add
  `to_dict`/`from_dict` (excluding `layout_margins_profile`).
- `src/cloudscope/views/primary_image_view.py` — add `RasterViewport` and
  `PrimaryImageViewState`; convert `export_session_state`/`apply_session_state`.
- `src/cloudscope/views/reference_image_view.py` — add `ReferenceImageViewState`
  and export/apply/display-option apply.
- `src/cloudscope/views/sum_intensity_plot_view.py` — remove `del visible`.

Docs:

- `docs-dev/cloudscope/dev-roadmap-reconnect.md` — add "Implemented so far".

Tests:

- `tests/cloudscope/test_session_state.py` — `HomePageRestorableState`,
  `HomePageChromeState`, `HomePageSessionSnapshot` round trips + bad schema.
- `tests/cloudscope/test_controller.py` — `to_restorable_state` excludes runtime
  fields.
- `tests/cloudscope/test_debug_view.py` — updated snapshot read-out shape.
- `tests/cloudscope/test_primary_image_view.py` — `PrimaryImageViewState` round
  trips (with and without viewport/manual contrast).
- `tests/cloudscope/test_reference_image_view.py` — `ReferenceImageViewState`
  round trip.
- `tests/nicewidgets/test_plotly_raster_viewer.py` — raster display-options
  serialization round trip + unknown-key tolerance.

## Tests run

```bash
uv run pytest tests/cloudscope/test_session_state.py tests/cloudscope/test_controller.py tests/cloudscope/test_debug_view.py tests/cloudscope/test_primary_image_view.py tests/cloudscope/test_reference_image_view.py tests/cloudscope/test_sum_intensity_plot_view.py tests/cloudscope/test_acq_analysis_plot_view.py tests/nicewidgets/test_plotly_raster_viewer.py -q
uv run pytest -q
```

## Test results

- Focused run: 145 passed.
- Full suite: 1883 passed, 45 skipped (pre-existing missing-fixture skips), 17
  warnings (pre-existing).

## Concerns / follow-ups

- `app_state` is captured but not yet used to drive restore. Wiring it into the
  restore path (or true build-time restore) is deferred.
- `HomePageChromeState` still exposes `analysis_plot_open`, `reference_image_open`,
  `velocity_pool_open`. Field cleanup and new page-chrome fields
  (`left_toolbar_open`, splitters, pool tab) remain a separate, agreed follow-up.
- Two pre-existing Ruff long-line warnings in `home_page.py` (L778/L781) are
  unrelated to this ticket and were left untouched.
- Raster typed-state changes were verified via unit tests only; live
  disconnect/reconnect verification in the app was not performed in this ticket.
