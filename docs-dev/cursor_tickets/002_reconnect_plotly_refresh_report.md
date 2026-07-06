# 002 — Reconnect Plotly refresh (implementation)

**Status:** complete (rev 2 — bootstrap race + NiceGUI sync)  
**Type:** implementation ticket (follow-on to `001_disconnect_reconnect_handoff.md`)  
**Branch:** `feature/fix-disconnect-reconnect-bug`  
**Worktree:** `/Users/cudmore/Sites/cloudscope-fix-disconnect`

---

## Files changed

| File | Change |
|---|---|
| `src/cloudscope/controllers/home_page_controller.py` | `republish_selection_from_state()` for reconnect |
| `src/cloudscope/pages/home_page.py` | Republish after reconnect build (`was_initialized`) |
| `src/cloudscope/views/acq_analysis_plot_view.py` | Primary-image-style async refresh + generation token |
| `src/cloudscope/views/sum_intensity_plot_view.py` | Same |
| `src/nicewidgets/plotly_plot/widget.py` | `_push_series_data()` also calls `_plot_element.update()` |
| `tests/cloudscope/test_controller.py` | Republish test |
| `tests/cloudscope/test_acq_analysis_plot_view.py` | Scheduler, bootstrap, stale-generation tests |
| `tests/cloudscope/test_sum_intensity_plot_view.py` | Same |
| `tests/nicewidgets/test_plotly_plot_widget.py` | Fake plotly element `update()` stub |

---

## Summary of implementation

### Root cause (bootstrap + reconnect)

1. **Stale build-time refreshes:** On first run, `build()` schedules empty plot refreshes before async load completes. After load publishes `FileSelectionChanged`, a refresh with data runs — but **earlier scheduled empty refreshes could still run afterward** and clear the chart (`set_series([])` + placeholder). File switch → back worked because no stale build tasks remained.

2. **`asyncio.sleep(0)` was not equivalent to PrimaryImageView timing:** Primary image uses `await run.io_bound(...)` (real async gap + work off UI thread) before pushing display updates. Plot views only yielded once.

3. **Plotly JS-only push:** `PlotlyPlotWidget.set_series()` updated the local figure dict and pushed via custom JS; if JS ran before the Plotly element was ready, the browser could stay empty despite correct Python-side state. Added NiceGUI `update()` after series push so the figure syncs through the element API.

### Fixes

**Plot views (PrimaryImageView pattern + generation token):**

```text
_refresh_plot_from_current_selection()
  → increment _plot_refresh_generation
  → _schedule_coro(_refresh_plot_async(generation))
  → await run.io_bound(lambda: None)
  → drop if generation stale
  → _refresh_plot()
```

**PlotlyPlotWidget:** `_push_series_data()` calls `_plot_element.update()` after JS push.

**B1 reconnect republish:** unchanged.

---

## Tests added or modified

- Republish, scheduler, bootstrap `FileSelectionChanged`, stale-generation drop (both plot views)
- `test_stale_plot_refresh_generation_is_dropped` — first scheduled refresh dropped after second schedule

---

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_acq_analysis_plot_view.py tests/cloudscope/test_sum_intensity_plot_view.py tests/nicewidgets/test_plotly_plot_widget.py -q

uv run pytest -q
```

---

## Test results

| Command | Result |
|---|---|
| Plot + widget tests (113) | **113 passed** |
| Full suite | **1776 passed**, 17 skipped |

---

## Manual acceptance (pending)

1. `./scripts/run app` — first run with `config_last_path`: 1D plots populate without file switch.
2. Reconnect — plots populate without file switch.
3. File switch → back still works.

---

## Concerns or follow-ups

- Manual native verification still required after rev 2.
- B3 (initial figure bake) not needed if rev 2 passes manual testing.
