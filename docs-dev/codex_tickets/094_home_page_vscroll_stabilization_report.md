# 094 Home page vertical scroll stabilization (Pass 1)

## Files changed

- `src/cloudscope/pages/home_page.py`
- `tests/cloudscope/test_home_page_main_scroll_layout.py`
- `docs-dev/codex_tickets/094_home_page_vscroll_stabilization_report.md`

## Summary of implementation

Pass 1 from `tmp/fix-web-vscroll.md`: keep the fixed splitter / internal-scroll
architecture and make the main scroll owner more reliable.

1. Added `HOME_MAIN_BOTTOM_SPACER_CLASSES = 'h-48 shrink-0'`.
2. Appended a bottom spacer div inside `_main_scroll_shell_classes()` but outside
   the workspace frame so the internal scroll container has real tail content.
3. Marked the scroll owner with `cloudscope-home-main-scroll` for browser devtools.

No change to document-level `overflow: hidden`, left toolbar pinning, or
reference-image / SmartExpansion commented-out blocks (Phase 3 cleanup deferred).

## Tests added or modified

- Added `tests/cloudscope/test_home_page_main_scroll_layout.py` (layout constants).

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_home_page_main_scroll_layout.py tests/cloudscope/test_home_page_build.py tests/cloudscope/test_home_page_right_pool_panel.py
```

## Test results

```
5 passed in 1.57s
```

(`test_home_page_main_scroll_layout.py`, `test_home_page_build.py`,
`test_home_page_right_pool_panel.py`)

## Browser validation

Validated at 1400×900 with `CLOUDSCOPE_NATIVE=0` on port 8781:

- `.cloudscope-home-main-scroll` is the scroll owner; `body` overflow remains hidden.
- Bottom spacer present: `h-48 shrink-0` (192px).
- Main scroll `maxScroll` increased from 120px to 312px (workspace 956px + spacer 192px − shell 836px).
- At `scrollTop=160`, workspace bottom clears footer by 19px (previously stuck 16–21px under footer at old max).
- Left toolbar and page load unchanged.

## Concerns or follow-ups

- Phase 2 (browser-native document scroll + sticky left toolbar) remains optional.
- Phase 3 dead code cleanup (`reference_image` panel state, commented blocks) deferred.
- `HOME_WORKSPACE_CLOSED_HEIGHT_CSS` magic `+ 120px` could be replaced with measured
  header/footer constants in a future layout pass.
