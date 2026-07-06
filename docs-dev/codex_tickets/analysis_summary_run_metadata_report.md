# Analysis summary run metadata and formatted display

## Files changed

- `src/acqstore/acq_image/analysis/model.py`
- `src/acqstore/acq_image/analysis/velocity_analysis/radon_velocity_analysis.py`
- `src/acqstore/acq_image/analysis/diameter_analysis/diameter_analysis.py`
- `src/acqstore/acq_image/analysis/heart_rate_analysis/heart_rate_analysis.py`
- `src/acqstore/acq_image/analysis/event_analysis/event_analysis.py`
- `src/cloudscope/views/analysis_summary_display.py`
- `src/cloudscope/views/velocity_analysis_view.py`
- `src/cloudscope/views/diameter_analysis_view.py`
- `tests/acqstore/test_analysis_summary_metadata.py`
- `tests/cloudscope/test_analysis_summary_display.py`
- `tests/acqstore/test_analysis_pool.py`

## Summary of implementation

- Added `BaseAnalysis.finalize_summary()` to prepend `analysis_date` (YYMMDD), `analysis_time` (HH:MM:SS.mmm), and optional `analysis_version` before remaining summary keys.
- All four analysis types call `finalize_summary` from `run()`: radon velocity, diameter, heart rate, event.
- Added `analysis_version` ClassVar and prepended metadata keys to `summary_columns` for pool tables (`velocity_*`, `hr_*`, `event_*` columns).
- Diameter gained a full `summary_columns` tuple matching core metrics.
- Velocity and diameter left-panel views show a collapsed **Summary** expansion with one `key: value` per line (no outer Results heading).

## Tests added or modified

- Added: `tests/acqstore/test_analysis_summary_metadata.py`
- Added: `tests/cloudscope/test_analysis_summary_display.py`
- Modified: `tests/acqstore/test_analysis_pool.py`

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_analysis_summary_metadata.py tests/cloudscope/test_analysis_summary_display.py tests/acqstore/test_analysis_pool.py tests/acqstore/test_radon_velocity_analysis.py tests/acqstore/test_diameter_analysis.py
uv run pytest
```

## Test results

- Focused: 33 passed
- Full suite: 1285 passed

## Concerns or follow-ups

- Old sidecar JSON without metadata is unchanged until the user re-runs analysis (no backfill).
- Event `_sync_summary()` after load/edit does not stamp metadata; only `run()` does.
- Heart rate / event left-panel views do not yet show formatted summary expansions.
