# Ticket 005 — LoadSaveView pure-helper tests

## Files changed

- `tests/cloudscope/test_load_save_view.py` — new file with 21 tests
- `docs/codex_tickets/005_load_save_view_helper_tests_report.md` (this report)

## Summary of implementation

`LoadSaveView` previously had no targeted helper tests; only the controller
side of the load/save flow had coverage. The pure module-level helpers
(`_recent_target_exists`, `_path_display`) and the easy view methods
(`_recent_item_matches_app_path`, `_resolve_initial_directory`, `_is_native_mode`,
`_update_button_states`) are testable headlessly by constructing the view
with `initially_visible=False`.

New tests cover:

- `_recent_target_exists`: FILE/FOLDER positive paths, missing paths, type
  mismatch (folder where file expected, file where folder expected), CSV
  treated as file.
- `_path_display`: shortens home-relative paths to `~/...`; returns paths
  outside the home unchanged.
- `_recent_item_matches_app_path`: true for matching `last_path`; false for
  different path; false when `last_path` is empty.
- `_resolve_initial_directory`: returns a directory `last_path` directly,
  returns parent when `last_path` is a file, falls back to home directory.
- `_is_native_mode`: returns a bool; returns False when `app.native` is None
  (using monkeypatch to simulate non-native runtime).
- `_update_button_states`: disables save-selected without a selection, disables
  when not dirty, enables when dirty, tolerates missing button references.

## Tests added or modified

21 tests in the new file `tests/cloudscope/test_load_save_view.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_load_save_view.py -q
uv run pytest tests/cloudscope/test_load_save_view.py --cov=cloudscope.views.load_save_view --cov-report=term-missing -q
```

## Test results

- 21 passed
- `load_save_view.py` coverage: **36% → 40%**
- The remaining gap is dominated by NiceGUI `build()` and click handlers
  (`_build_toolbar_contents`, `_build_recent_menu`, `_fill_recent_menu`,
  `_open_recent_menu`, `_rebuild_history_menu_impl`,
  `_on_load_clicked`/`_pick_load_path`, `_show_missing_recent_path_dialog`,
  `_notify_status`, `_run_ui`) which require a live NiceGUI client/slot.

## Concerns or follow-ups

- A future ticket could add a NiceGUI test-client smoke test that calls
  `build()` inside a `ui.column()` to push coverage on the build-time
  branches.
