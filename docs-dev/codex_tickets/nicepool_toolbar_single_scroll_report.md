# NicePool toolbar single vertical scroll

## Files changed

- `src/nicewidgets/nicepool/plot_pool_controller.py`
- `src/nicewidgets/nicepool/pool_control_panel.py`
- `src/nicewidgets/nicepool/nice_pool.py`

## Summary of implementation

DevTools on `/pool` confirmed two scroll owners on the left toolbar:

1. `PoolControlPanel` root column (`overflow-y-auto`) — intended scroll
2. Quasar `q-splitter__panel q-splitter__before` — redundant outer scroll

Fix:

- Scoped CSS under `.nicepool-root` sets splitter panels to `overflow: hidden`.
- `_control_panel_container` is the single scroll owner (`overflow-y-auto`).
- Removed `overflow-y-auto` from `PoolControlPanel.build()` content column.
- NicePool root uses bounded flex layout classes (`min-h-0 overflow-hidden`).

## Tests added or modified

- None (layout/CSS change; verified manually in browser).

## Exact test commands run

```bash
uv run pytest tests/nicewidgets/test_plot_pool_controller.py tests/nicewidgets/test_nicepool.py -q
```

Manual verification:

```bash
CLOUDSCOPE_NATIVE=0 CLOUDSCOPE_PORT=8765 CLOUDSCOPE_SHOW=0 uv run python src/cloudscope/app.py
# Open http://127.0.0.1:8765/pool — left toolbar should show one vertical scrollbar
```

## Test results

- Automated: **19 passed**
- Manual CDP on `http://127.0.0.1:8766/pool` after fix:
  - `q-splitter__panel q-splitter__before`: `overflow-y: hidden`
  - Single toolbar scroll owner: `_control_panel_container` (`overflow-y-auto`)

## Concerns or follow-ups

- ~~Unused duplicate toolbar: `src/nicewidgets/nicepool/control_panel.py`~~ — removed by user.
