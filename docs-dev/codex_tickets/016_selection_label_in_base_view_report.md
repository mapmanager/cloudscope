# Ticket 016 — Shared selection-label helper on `BaseView`

## Summary

`VelocityAnalysisView` and `DiameterAnalysisView` each owned an identical
`_selection_label` field, identical creation code, and an identical
`_refresh_selection_label` method that rendered the primary selection as a
single-line `file=…, channel=…, roi=…` string.

This ticket extracts that behavior into two opt-in helpers on `BaseView` and
switches the two analysis views to use them. The label is also reformatted to
three lines per ticket request:

1. File name (basename of `file_id`).
2. Channel value (or `—` when unset).
3. ROI value (or `—` when unset).

`No file selected` is still rendered as a single line when no file is selected.

A pre-implementation sweep of `src/cloudscope/views/` confirmed that only
`velocity_analysis_view.py` and `diameter_analysis_view.py` use the
`_selection_label` + `file=…, channel=…, roi=…` pattern. Other `No file
selected` strings in the codebase are unrelated (status messages, the
`acq_analysis_plot_view` empty-message helper, a metadata-view inline label,
controller error strings, and notifications).

## Files changed

- `src/cloudscope/views/base_view.py`
  - Added `from pathlib import Path`.
  - Added `build_selection_label() -> ui.label` — creates a single
    `ui.label("No file selected")` with classes
    `text-sm opacity-70 shrink-0 whitespace-pre-line` and stores it on
    `self._selection_label`.
  - Added `refresh_selection_label() -> None` — renders the three-line
    summary using `Path(file_id).name` for the file line and `—` placeholders
    for missing channel / ROI. No-op when the label has not been built.
- `src/cloudscope/views/velocity_analysis_view.py`
  - Removed the `self._selection_label: ui.label | None = None` attribute
    declaration in `__init__`.
  - Replaced the inline `ui.label("No file selected")…` creation in
    `_build_content` with `self.build_selection_label()`.
  - Replaced the call to `self._refresh_selection_label()` in
    `_refresh_selection_dependent_ui` with `self.refresh_selection_label()`.
  - Deleted the now-redundant `_refresh_selection_label` method.
- `src/cloudscope/views/diameter_analysis_view.py`
  - Same four edits as `velocity_analysis_view.py`.
- `tests/cloudscope/test_velocity_analysis_view.py`
  - Renamed the section comment to reference the new public method.
  - Updated both selection-label tests to call `refresh_selection_label` and
    to assert the new three-line format (`["file: sample.oir", "channel: 2",
    "roi: 5"]`).
- `tests/cloudscope/test_diameter_analysis_view.py`
  - Same updates as the velocity test file.
- `tests/cloudscope/test_base_view.py`
  - Added a shared `_FakeLabel` stand-in.
  - Added five new tests covering: no-op without `build_selection_label`,
    "No file selected" placeholder line, three-line full-selection rendering
    with basename extraction, em-dash placeholders when both channel and ROI
    are missing, and em-dash on only the unset line when one of channel / ROI
    is set.

## Implementation notes

- Choice of single label + Tailwind `whitespace-pre-line` rather than a
  three-label column. This keeps element count minimal, matches the existing
  one-element layout slot, and renders `\n` separators as visible line breaks
  without per-line styling state.
- `file_id` is the absolute file path per `AcqImage.file_id`, so the file line
  is derived directly via `Path(file_id).name` without needing an `AcqImage`
  lookup.
- The helpers are opt-in: `BaseView` does not call them from its lifecycle,
  so views that do not need a selection label are unaffected. The
  `_selection_label` attribute is assigned only when `build_selection_label`
  is called; `refresh_selection_label` uses `getattr(self, "_selection_label",
  None)` so it is safe to invoke unconditionally.

## Tests added or modified

Added tests:

- `tests/cloudscope/test_base_view.py::test_refresh_selection_label_no_op_when_label_not_built`
- `tests/cloudscope/test_base_view.py::test_refresh_selection_label_displays_no_file_when_unset`
- `tests/cloudscope/test_base_view.py::test_refresh_selection_label_renders_three_lines_with_basename`
- `tests/cloudscope/test_base_view.py::test_refresh_selection_label_uses_em_dash_for_missing_channel_and_roi`
- `tests/cloudscope/test_base_view.py::test_refresh_selection_label_uses_em_dash_only_for_missing_field`

Modified tests (renamed callee + new three-line assertions):

- `tests/cloudscope/test_velocity_analysis_view.py::test_refresh_selection_label_displays_no_file_when_unset`
- `tests/cloudscope/test_velocity_analysis_view.py::test_refresh_selection_label_includes_selection_components`
- `tests/cloudscope/test_diameter_analysis_view.py::test_refresh_selection_label_no_file_set`
- `tests/cloudscope/test_diameter_analysis_view.py::test_refresh_selection_label_includes_selection_components`

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_base_view.py \
              tests/cloudscope/test_velocity_analysis_view.py \
              tests/cloudscope/test_diameter_analysis_view.py -q
uv run pytest -q
```

## Test results

Targeted run (the three files this ticket touches):

```
39 passed, 1 warning in 0.93s
```

Full suite:

```
2 failed, 737 passed, 3 warnings in 2.70s
```

The two failures are in `tests/cloudscope/test_acq_analysis_plot_view.py`:

- `test_refresh_plot_clears_chart_and_sets_status_when_no_plot_data`
- `test_refresh_plot_sets_line_data_for_available_plot`

These failures are confirmed pre-existing — `git stash` of the ticket changes
followed by the same full-suite run still produces the same two failures.
They originate from a commented-out `self._status_label.text = …` line in
`src/cloudscope/views/acq_analysis_plot_view.py` (around line 294) and are
unrelated to the `BaseView` / analysis-view changes in this ticket.

The pre-existing `PytestCollectionWarning` for `TestEvent` in
`tests/cloudscope/test_base_view.py` is also unchanged by this ticket.

## Concerns or follow-ups

- The two pre-existing `test_acq_analysis_plot_view.py` failures should be
  triaged in a separate ticket; either re-enable the commented status-label
  assignment in `acq_analysis_plot_view.py` or update the tests to match the
  intended behavior.
- The new helpers are deliberately opt-in. If a future view wants a selection
  label, it just calls `build_selection_label()` from inside its container and
  `refresh_selection_label()` from its selection-refresh path.
- If per-line styling becomes needed later (e.g. emphasize the file name),
  the single label can be replaced with a small `ui.column` of three labels
  without changing the public API.
