# 031 — Sum intensity plot Set F0 (manual baseline)

## Summary of implementation

CloudScope can now set sum-intensity `F0` visually from the sum-intensity plot:

1. Plot toolbar **Set F0** enters a modal analysis UI mode (`AnalysisUiMode.SET_F0`).
2. Analysis controller publishes `AppBusyChanged(is_busy=True)` (same pattern as event edit) and `AnalysisUiModeChanged`.
3. Plot swaps to `DETRENDED_NORM_SUM_INTENSITY` (the AcqStore trace used for F0), adds a draggable horizontal Plotly measurement line initialized from `F0_BASELINE`.
4. **Accept** publishes `UpdateAnalysisDetectionParamsIntent` with `baseline_method=manual` and `manual_f0_baseline=<line>`. Controller validates, publishes `AnalysisDetectionParamsChanged`, clears busy/mode. Left-panel analysis view updates draft controls. **No auto-run.**
5. **Cancel** clears mode/busy without param changes. Plot returns to normal df/f0 display.

Toolbar code is modular (`SumIntensityPlotToolbar`) so a future ticket can show/hide it independently.

## Files changed

- `src/cloudscope/events/analysis.py` — `AnalysisUiMode`, begin/cancel UI-mode intents, `AnalysisUiModeChanged`, `UpdateAnalysisDetectionParamsIntent`, `AnalysisDetectionParamsChanged`
- `src/cloudscope/controllers/analysis_controller.py` — subscribe/handle UI mode + detection-param update; reuse `AppBusyChanged`
- `src/cloudscope/views/sum_intensity_plot_toolbar.py` — modular plot toolbar (Set F0 / Accept / Cancel)
- `src/cloudscope/views/sum_intensity_plot_view.py` — Set F0 mode, series swap, measurement line
- `src/cloudscope/views/sum_intensity_analysis_view.py` — apply `AnalysisDetectionParamsChanged` to draft controls
- `tests/cloudscope/test_analysis_controller.py` — UI mode / param-update tests; `FakeTaskRunner.is_running`
- `tests/cloudscope/test_sum_intensity_plot_view.py` — Set F0 flow tests
- `tests/cloudscope/test_sum_intensity_analysis_view.py` — draft param apply test
- `docs-dev/cursor_tickets/031_sum_intensity_set_f0_report.md` — this report

## Tests added or modified

- Analysis controller: begin/cancel UI mode, busy rejection while task running, Accept clears Set F0 and publishes param state, invalid params warn
- Plot view: begin intent, enter mode (detrended + line), drag pending F0, Accept/Cancel intents, exit restores df/f0
- Analysis view: applies manual F0 draft controls and refreshes visibility

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_analysis_controller.py tests/cloudscope/test_sum_intensity_plot_view.py tests/cloudscope/test_sum_intensity_analysis_view.py
```

## Test results

```text
90 passed, 1 warning in 1.88s
```

(Pre-existing warning in `test_stale_plot_refresh_generation_is_dropped` about an un-awaited refresh coroutine; unrelated to Set F0.)

## Concerns or follow-ups

- `AnalysisUiModeChanged` was added so the plot enters/leaves Set F0 only after the controller accepts the mode (not optimistic UI). This mirrors ROI/event mode state signaling while still using `AppBusyChanged` for global disable.
- Left toolbar shell and some views already have `disable_when_busy=False`; Set F0 relies on the same busy semantics as event edit.
- Future ticket: second dedicated Set F0 plot + live df/f0 preview while dragging.
- Future ticket: toggle plot toolbar visibility via `SumIntensityPlotToolbar.set_visible`.
- User must still click **Run Sum Intensity Analysis** after Accept for scientific recompute.
