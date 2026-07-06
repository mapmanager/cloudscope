# Native single-window Phase 0 diagnostic logging

## Files changed

- `src/cloudscope/app.py`
- `src/cloudscope/pages/home_page.py`
- `docs-dev/codex_tickets/native_single_window_phase0_diag_report.md`

## Summary of implementation

Phase 0 adds temporary `[native-diag]` log lines to the single-window
`ui.run(native=True)` path. No behavior changes. Logs cover:

- `configure_native_window()` and `main()` startup (`window_args`, `confirm_close`)
- Native geometry handler registration (`moved` / `resized`)
- Native `loaded` / `closed` observer events (log-only)
- Splitter `_capture()` writes to in-memory `AppConfig`
- Shutdown persist handler registration and `app_config.save()` payload

Option C (`desktop_launcher.py`) is unchanged.

## Tests added or modified

None (diagnostic logging only).

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_home_page_right_pool_panel.py -q
```

## Test results

Pending maintainer run after local desktop session.

## Manual test protocol

1. Optional: truncate or note timestamp of `~/Library/Application Support/cloudscope/logs/cloudscope.log`.
2. Run `uv run python src/cloudscope/app.py`.
3. Wait for home page load.
4. Move and resize the main window.
5. Drag the file-list splitter.
6. Quit with red close button; relaunch and repeat move/resize/splitter; quit with Cmd+Q.
7. Collect logs:

   ```bash
   grep '\[native-diag\]' "$HOME/Library/Application Support/cloudscope/logs/cloudscope.log"
   ```

8. Compare `window_rect` and `home_file_list_splitter_pct` in `app_config.json` before/after.

## Concerns or follow-ups

- Remove or downgrade `[native-diag]` logs in Phase 1 after root cause is confirmed.
- Phase 1 will fix geometry registration / quit confirmation based on log evidence.
