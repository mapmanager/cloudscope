# 038 — Analysis results copy-to-clipboard, event view background, Ruff cleanup

## Summary

Three changes to the analysis side panels:

1. **Ruff cleanup (F841).** Removed dead/unused `table = analysis.result.table`
   assignments (and the associated commented-out "Rows: …" labels) in the
   results-controls of both the velocity and diameter views.

2. **Copy results to clipboard.** Added a `content_copy` icon button to the
   Run/Batch button row in both `VelocityAnalysisView` and
   `DiameterAnalysisView`. Clicking it copies the current selection's analysis
   result table to the clipboard as tab-delimited text (TSV) so it pastes
   cleanly into a spreadsheet. The copied table uses
   `BaseAnalysis.table_with_bookkeeping()` so `channel` and `roi_id` columns are
   included. The button is disabled until a result table exists for the current
   channel/ROI.

   - Reuses existing infrastructure only: `copy_to_clipboard()` from
     `nicewidgets/utils/clipboard.py`, which already handles native
     (`pyperclip`) and web (`navigator.clipboard`) clipboards. TSV is produced
     with the standard `DataFrame.to_csv(sep="\t", index=False)`.
   - Boundaries respected: button + handler are view orchestration (cloudscope);
     the clipboard helper stays in nicewidgets; the DataFrame comes from the
     acqstore analysis model. No cross-boundary moves.

3. **Event view background color.** Added a slate background
   (`bg-slate-50 dark:bg-slate-800 rounded-md p-2`) to `EventAnalysisView`'s root
   element. No `BaseView` refactor was needed — `BaseView` has no background API,
   but the view owns its root element, so a utility class on the root is the
   simplest approach.

## Files changed

- `src/cloudscope/views/velocity_analysis_view.py` — removed unused `table`
  line; import `copy_to_clipboard`; `_copy_button` attribute; copy button in the
  Run/Batch row; `_selected_analysis()` helper; `_on_copy_results_clicked()`
  handler; copy-button enable logic in `_refresh_run_button`.
- `src/cloudscope/views/diameter_analysis_view.py` — same set of changes as the
  velocity view (diameter analysis kind).
- `src/cloudscope/views/event_analysis_view.py` — slate background utility
  classes on the view root.

## Tests added or modified

- `tests/cloudscope/test_velocity_analysis_view.py` — added
  `test_on_copy_results_copies_tsv`, `test_on_copy_results_noop_when_no_table`,
  and `test_refresh_run_button_disables_copy_without_results`.
- `tests/cloudscope/test_diameter_analysis_view.py` — added the same three copy
  tests for the diameter view.

## Test commands run

```bash
uv run ruff check src/cloudscope/views/velocity_analysis_view.py src/cloudscope/views/diameter_analysis_view.py src/cloudscope/views/event_analysis_view.py
uv run pytest tests/cloudscope/test_velocity_analysis_view.py tests/cloudscope/test_diameter_analysis_view.py tests/cloudscope/test_event_analysis_view.py -q
```

## Test results

- Ruff: clean for the velocity and diameter views (the pre-existing `B009`
  `getattr` warning in `event_analysis_view.py:433` is unrelated and left
  untouched).
- pytest: 63 passed.

## Concerns / follow-ups

- The copy uses `table_with_bookkeeping()`, which raises if the analysis table
  ever contains reserved `channel`/`roi_id` columns; the handler catches any
  exception and shows a negative notification rather than crashing the UI.
- Pre-existing Ruff `B009` in `event_analysis_view.py` (`getattr(analysis,
  'get_events')()`) remains; out of scope for this change.
