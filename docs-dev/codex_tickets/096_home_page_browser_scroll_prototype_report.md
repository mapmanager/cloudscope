# 096 Home page browser scroll prototype (Direction B)

## Files changed

- `src/cloudscope/pages/home_page.py`
- `tests/cloudscope/test_home_page_main_scroll_layout.py`
- `docs-dev/codex_tickets/096_home_page_browser_scroll_prototype_report.md`

## Summary of implementation

Minimal Direction B prototype:

1. Re-enabled browser/page scroll (`body { overflow-y: auto }`, removed `overflow: hidden`).
2. Outer left splitter uses `min-h-[calc(100vh-4rem)] overflow-visible` instead of fixed viewport clip.
3. Left toolbar wrapped in `sticky top-10` container.
4. Main workspace remains a viewport-sized splitter island (`height: calc(100vh - 4rem)`).
5. Added `h-24` bottom cushion in document flow after the workspace column.

## Tests added or modified

- Updated `tests/cloudscope/test_home_page_main_scroll_layout.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_home_page_main_scroll_layout.py tests/cloudscope/test_home_page_build.py -q
```

## Test results

```
4 passed in 1.56s
```

## Browser validation (8784, 1400×900)

- `html` scrollHeight 1048 vs clientHeight 900 → **browser tab can scroll** (~148px).
- `body { overflow-y: auto }`; no `overflow: hidden` on document.
- `.sticky` left toolbar wrapper present.
- `.cloudscope-home-page-bottom-cushion` present.
- No `.cloudscope-home-main-scroll` internal page scroll owner.

- Splitter island is still fixed height; dragging splitters redistributes inside the island.
- Removed bottom `h-24` cushion and nested `SUM_INTENSITY_EXPAND` splitter (2026-06-30 follow-up).
- Document scroll may be minimal without cushion; browser tab scroll still enabled via Direction B CSS.
- Native pywebview behavior may differ; revert-friendly experiment.
- Plotly/table sizing may need follow-up if panes collapse.
