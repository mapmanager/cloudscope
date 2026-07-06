# Ticket 069: Pool window geometry persistence

## Files changed

### Modified
- `src/cloudscope/app_config.py` — optional `pool_window_rect`, getter/setter, tolerant load
- `src/cloudscope/window_geometry.py` — parameterized `get_rect` / `set_rect` / optional `save`
- `src/cloudscope/desktop_launcher.py` — restore pool rect on open, attach tracker, pass `app_config`
- `tests/cloudscope/test_window_geometry.py`
- `tests/cloudscope/test_app_config.py`
- `tests/cloudscope/test_desktop_launcher.py`

### Created
- `docs-dev/codex_tickets/069_pool_window_geometry_report.md`

## Summary

Pool window geometry for Option C desktop now mirrors main window behavior:

- Optional `pool_window_rect` in `AppConfig` (`None` until user moves/resizes pool)
- `WindowGeometryTracker` on pool window updates config in memory on move/resize only
- `open_pool()` restores saved rect when set; otherwise uses main+offset defaults
- Pool close clears window ref only; app quit uses existing main `persist()` → `save()`

No schema version bump. No final geometry grab on pool close or quit.

## Tests added or modified

- `tests/cloudscope/test_app_config.py` — pool rect round-trip, missing key → `None`
- `tests/cloudscope/test_window_geometry.py` — parameterized tracker, unset pool rect
- `tests/cloudscope/test_desktop_launcher.py` — saved vs default pool placement

## Test commands run

```bash
uv run pytest tests/cloudscope/test_app_config.py tests/cloudscope/test_window_geometry.py tests/cloudscope/test_desktop_launcher.py
uv run pytest
```

## Test results

```
1166 passed, 2 skipped, 13 warnings
```

## Manual tests (operator)

- Open pool → move/resize → close pool → reopen → same geometry (same session)
- Quit app → relaunch → open pool → last geometry restored
- First pool open with no saved rect → main + offset default

## Concerns / follow-ups

- Main window still uses monitor + final `sync_from_window()` on main close; pool uses monitor only per plan
