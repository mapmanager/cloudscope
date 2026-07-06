# 095 Home page fixed-shell layout rework

## Files changed

- `src/cloudscope/pages/home_page.py`
- `src/cloudscope/app_config.py`
- `tests/cloudscope/test_home_page_main_scroll_layout.py`
- `docs-dev/codex_tickets/095_home_page_fixed_shell_layout_report.md`

## Summary of implementation

Direction A fixed app shell — no page-level vertical scroll:

1. Removed Pass 1 bottom spacer and `+120px` workspace height fudge.
2. Replaced scroll shell (`overflow-y-auto`) with `HOME_MAIN_SHELL_CLASSES`
   (`overflow-hidden`, fill parent).
3. Removed fixed-height workspace frame wrapper; splitters fill the shell directly.
4. Removed dead `analysis_reference` splitter pane (reference image lives in left
   toolbar now). Analysis/sum-intensity stack sits directly under `primary_splitter.after`.
5. Simplified `_sync_analysis_panel_layout()` (no reference-image state).
6. Set `HOME_RIGHT_POOL_CLOSED_SPLITTER_PCT` to `100.0` so the main workspace uses
   full width when the right pool panel is collapsed (header toggle still opens pool).

Browser tab scroll remains disabled (`html/body/#app overflow: hidden`) by design for
this pass. Only intentional internal scrolls remain (e.g. file-list AG Grid).

## Tests added or modified

- Updated `tests/cloudscope/test_home_page_main_scroll_layout.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_home_page_main_scroll_layout.py tests/cloudscope/test_home_page_build.py tests/cloudscope/test_splitter_manager.py tests/cloudscope/test_app_config_splitters.py
```

## Test results

```
25 passed in 1.53s
```

## Browser validation (8783, 1400×900)

- `.cloudscope-home-main-shell` present; `.cloudscope-home-main-scroll` gone.
- No page-level vertical scroll owner; only AG Grid file-list scroll remains.
- Main shell right edge ~1383px vs viewport 1400px (left toolbar only; no 2% pool slack).
- `body` overflow remains hidden (fixed app shell by design).

- Browser-native tab scroll (Direction B) not attempted.
- Persisted `home_analysis_reference_splitter_pct` config key is orphaned but harmless.
- Verify right-pool open/close and splitter drag still feel OK at 100% collapsed width.
