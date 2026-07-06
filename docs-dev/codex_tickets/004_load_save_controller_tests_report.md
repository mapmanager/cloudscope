# Ticket 004 — Expand LoadSaveController tests

## Files changed

- `tests/cloudscope/test_load_save_controller.py` — appended 16 new tests
- `docs/codex_tickets/004_load_save_controller_tests_report.md` (this report)

## Summary of implementation

`LoadSaveController` previously had reasonable coverage for the load+recents
flow, but the save-selected error paths, save-all empty/error paths,
`_ImmediateTaskContext`, cancel-task variants (no-runner / wrong-kind /
no-matching-task), `_on_clear_recent_paths`, three branches of
`_recent_nominal_target_missing`, and the synchronous fallback in
`_start_task` were uncovered.

New tests added:

- `_ImmediateTaskContext`: progress with unknown fraction publishes `current=0`,
  with known fraction publishes scaled `current`; `is_cancelled` returns False
  and `raise_if_cancelled` is a no-op.
- Cancel task: ANALYSIS kind is ignored; without a runner attached the
  controller warns; runner returning False yields a warning.
- Save-selected: warn when the selected file_id no longer resolves, INFO when
  not dirty, INFO completion + actual save, ERROR when `save()` raises.
- Save-all: warn when no list loaded, INFO completion of a happy path, ERROR
  when iter raises.
- `_on_clear_recent_paths`: clears config, publishes RecentPathsChanged + INFO.
- `_recent_nominal_target_missing`: unrelated warning path, warning without a
  path, unrelated message at same path.
- `_start_task` synchronous fallback: completed, failed (RuntimeError),
  cancelled (TaskCancelled) paths each publish the right TaskStatus and
  invoke the matching callback.
- `_load_path_worker`: `LoadCancelled` is re-raised as `TaskCancelled`;
  `(completed, total)` progress callback is converted into fractions
  (including the `total == 0` branch).

## Tests added or modified

16 new tests in `tests/cloudscope/test_load_save_controller.py`. Total file
count is now 30 tests (was 14).

## Exact test commands run

```bash
uv run pytest tests/cloudscope/test_load_save_controller.py -q
uv run pytest tests/cloudscope/test_load_save_controller.py --cov=cloudscope.controllers.load_save_controller --cov-report=term-missing -q
```

## Test results

- 30 passed
- `load_save_controller.py` coverage: **72% → 96%** (188 statements, 8 missed)
- Remaining missed lines (162-163, 208-209, 250-251, 567-575) are
  `except RuntimeError` paths inside `_on_load_path`, `_on_save_selected`,
  `_on_save_all`, and the TaskRunner-attached branch of `_start_task` (the
  latter is exercised by the existing
  `test_load_controller_cancels_matching_load_task` only at the cancel
  surface, not the runner.start() pass-through).

## Concerns or follow-ups

- The runner-attached `_start_task` branch is only covered indirectly. A small
  test using a FakeRunner that records start() args would close that gap.
- The three `except RuntimeError` branches in `_on_load_path` / `_on_save_*`
  fire only when `_start_task` raises (e.g. TaskRunner reports an active
  task). They require a fake runner whose `start` raises, which is left as a
  follow-up.
