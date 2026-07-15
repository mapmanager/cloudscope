# 034 — Edit F0 dual plot, live Set Manual/Auto, general plot context-menu hook

## Summary of implementation

Revised sum-intensity Edit F0 UX:

1. **Second Plotly plot** (`_f0_plot`) shows detrended mean line + Manual H-line + Auto F0 line. Visible only in Edit F0 mode, stacked above the primary df/f0 plot (below the toolbar).
2. **Primary plot** no longer swaps series or draws F0 overlays; it stays on normal df/f0 + peaks.
3. **Enter/exit**: primary-plot context menu **Edit F0** (toggle); idle toolbar Set F0 button removed. **Close** (ex-Cancel) or uncheck Edit F0 exits without writing params.
4. **Toolbar**: Manual F0 readout + **Set Manual F0** | Percentile + **Set Auto F0** | **Close**. Percentile edits preview Auto F0 on `_f0_plot` only.
5. **Live Set**: Set Manual / Set Auto publish `UpdateAnalysisDetectionParamsIntent(..., run_analysis=True)`. Controller merges the patch onto last-run detection params, publishes `AnalysisDetectionParamsChanged` (left panel sync), starts analysis, stays in Edit F0, and re-asserts app-busy after the task clears busy.
6. **AcqStore**: no schema change; keep `baseline_method` / `baseline_percentile` / `manual_f0_baseline` (no stored `auto_f0` detection param).
7. **nicewidgets**: general `on_build_context_menu` callback on `PlotlyPlotWidget` (same pattern as Table/Tree), not F0-specific.

## Files changed

- `src/cloudscope/events/analysis.py` — `UpdateAnalysisDetectionParamsIntent.run_analysis`
- `src/cloudscope/controllers/analysis_controller.py` — merge + run; keep Edit F0 mode; reassert busy
- `src/cloudscope/task_runner.py` — terminal callbacks after `AppBusyChanged(False)`
- `src/nicewidgets/plotly_plot/widget.py` — `on_build_context_menu` / setter
- `src/nicewidgets/plotly_plot/context_menu.py` — invoke custom builder before Copy
- `src/cloudscope/views/sum_intensity_plot_toolbar.py` — Edit F0 toolbar layout
- `src/cloudscope/views/sum_intensity_plot_view.py` — dual plot + Edit F0 menu + live Set
- `tests/cloudscope/test_sum_intensity_plot_view.py`
- `tests/cloudscope/test_analysis_controller.py`
- `tests/cloudscope/test_task_runner.py`
- `tests/nicewidgets/test_plotly_plot_widget.py`

## Tests added or modified

- Edit F0 enters on F0 plot only; primary untouched
- Set Manual / Set Auto publish `run_analysis=True`
- Close / mode exit hide F0 chrome
- Percentile preview updates Auto on F0 plot
- Controller keeps Edit F0 after param update; merge+run path
- TaskRunner on_completed after busy clear
- Plotly context-menu custom action hook

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_sum_intensity_plot_view.py \
  tests/cloudscope/test_analysis_controller.py \
  tests/cloudscope/test_task_runner.py \
  tests/nicewidgets/test_plotly_plot_widget.py -q
```

## Test results

```text
140 passed, 1 warning in 1.42s
```

(Pre-existing warning in `test_stale_plot_refresh_generation_is_dropped` about an un-awaited refresh coroutine.)

## Concerns or follow-ups

- Manual F0 whole-line drag UX (vs first-point drag) deferred to exercise on `_f0_plot` after this lands.
- Live verify in native app recommended: context-menu Edit F0, Set Manual/Auto refresh primary peaks and left-panel params, Close leaves mode.
- Web mode (`CLOUDSCOPE_NATIVE=0`) cannot load files; data-dependent GUI verify is UNVERIFIED in this ticket.
