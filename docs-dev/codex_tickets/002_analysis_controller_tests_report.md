# Ticket 002 — Expand AnalysisController tests

## Files changed

- `tests/cloudscope/test_analysis_controller.py` — expanded from 3 tests to 20
- `docs/codex_tickets/002_analysis_controller_tests_report.md` (this report)

## Summary of implementation

`AnalysisController` previously had only 3 tests covering selection-validation
and dependency-rejection paths. Lines 187-233 (worker construction), 254-261
(dependent-event rerun), 280-288 (completion publishing), and 325-331 (helper
validation) were uncovered.

A `FakeTaskRunner` was added that captures the `worker`, `on_completed`,
`on_failed`, `on_cancelled` callables from `start()` so each can be invoked
synchronously on the test thread. A `FakeTaskContext` lets the worker exercise
`report_progress`, `is_cancelled`, and `raise_if_cancelled` paths. A
`FakeAnalysisSet` returns real `RadonVelocityAnalysis`, `DiameterAnalysis`,
and `EventAnalysis` instances from `create()` so the worker's `isinstance`
branches execute genuinely.

New tests cover:

- `_on_cancel_task`: non-analysis cancel kinds are ignored; warning published
  when nothing is running.
- `_validate_intent`: missing channel and ROI raise; no `AcqImageList` raises.
- Happy-path dispatch: TaskRunner.start called with `TaskKind.ANALYSIS`, the
  expected label, and four callables.
- `_run_analysis_worker`: EVENT-kind create-when-missing, EVENT-kind
  set_detection_params-when-existing, non-EVENT remove-then-create,
  AcqImage-no-longer-loaded raise, AcqImageList-disappears-between-validate-
  and-worker raise, dependent EventAnalysis rerun after Radon, no rerun when
  no event analysis exists, cancellation aborts before run_analysis.
- Callbacks: completion publishes `AnalysisCompleted(success=True)` + INFO
  status; failure publishes `AnalysisCompleted(success=False)` + WARNING
  status; cancellation publishes a cancel-message AnalysisCompleted.
- `_copy_selection`: returns a structurally equal but distinct instance.

## Tests added or modified

20 tests in `tests/cloudscope/test_analysis_controller.py`.

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_analysis_controller.py -q
uv run pytest tests/cloudscope/test_analysis_controller.py --cov=cloudscope.controllers.analysis_controller --cov-report=term-missing -q
```

## Test results

- 20 passed
- `analysis_controller.py` coverage: **51% → 92%** (122 statements, 10 missed)
- Remaining missed lines are early-return guards in `_raise_if_exclusive_conflict`
  reached only when the user invokes EVENT-kind (which intentionally skips
  exclusion checks), plus the dependent-event TypeError defensive branch.

## Concerns or follow-ups

- Lines 135 (NotImplementedError), 151/154 (defensive early returns),
  166 (matching-existing-analysis early return), 209 (TypeError defensive
  branch when the analysis_set returns a non-EventAnalysis instance for
  the EVENT key), 224 (`DiameterAnalysis.set_execution_options`),
  259 (defensive TypeError on dependent rerun), 326/328/330 (raise paths
  in `_required_selection_values` that are guarded earlier by
  `_validate_intent`) remain uncovered. These are all defensive guards
  that cannot be reached through public APIs without bypassing earlier
  validation. Future work could either remove the redundant guards or
  add white-box tests that bypass `bind()`.
