# 088 Unified CloudScope log file

## Files changed

- `src/cloudscope/utils/logging.py` — `attach_file_handler_to_loggers()`, shared handler lifecycle
- `src/cloudscope/app.py` — sibling packages use `file=False`; attach to `cloudscope.log`
- `tests/cloudscope/test_logging.py` — attachment integration tests
- `docs-dev/codex_tickets/088_unified_cloudscope_log_report.md` — this report

## Summary

Unified file logging for the CloudScope application entry point:

1. `setup_logging(level='DEBUG')` — creates `cloudscope.log` as before.
2. `setup_nicewidgets_logging(level='DEBUG', file=False)` and `setup_acqstore_logging(level='DEBUG', file=False)` — console handlers only; no separate package log files.
3. `attach_file_handler_to_loggers('acqstore', 'nicewidgets')` — shares the CloudScope `RotatingFileHandler` with package-root loggers.

All `get_logger(__name__)` calls under `acqstore.*` and `nicewidgets.*` continue to propagate to their package roots and now also write to `cloudscope.log`. Console output is unchanged (each package still has its own stderr handler).

`CLOUDSCOPE_DISABLE_FILE_LOG=1` disables CloudScope file creation; attachment is then a no-op.

Standalone acqstore/nicewidgets scripts are unchanged (default `file=True`).

## Tests added or modified

- `tests/cloudscope/test_logging.py`

## Test commands run

```bash
uv run pytest tests/cloudscope/test_logging.py -q
```

## Test results

8 passed (0.03s)

## Concerns or follow-ups

- DRY refactor of the three `logging.py` modules deferred.
- Documentation-only deprecation of `acqstore.log` / `nicewidgets.log` for CloudScope runs not added in this ticket.
