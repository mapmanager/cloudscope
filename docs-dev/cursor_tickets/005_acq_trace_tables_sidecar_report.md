# 005 AcqTrace Tables and Sidecar Report

## Files changed

- `pyproject.toml`
- `uv.lock`
- `src/acqstore/acq_types.py`
- `src/acqstore/acq_trace/__init__.py`
- `src/acqstore/acq_trace/acq_trace.py`
- `src/acqstore/acq_trace/epoch_data.py`
- `src/acqstore/acq_trace/sweep_data.py`
- `src/acqstore/acq_trace/trace_header.py`
- `src/acqstore/acq_trace/file_loaders/__init__.py`
- `src/acqstore/acq_trace/file_loaders/abf_trace_loader.py`
- `scripts/acqstore/try_abfile.py`
- `tests/acqstore/data/abf/2021_07_20_0002.abf`
- `tests/acqstore/data/abf/2021_07_20_0008.abf`
- `tests/acqstore/data/abf/2021_07_20_0013.abf`
- `tests/acqstore/data/abf/2021_07_20_0016.abf`
- `tests/acqstore/test_abf_trace_loader.py`
- `tests/acqstore/test_acq_trace.py`
- `docs-dev/cursor_tickets/005_acq_trace_tables_sidecar_report.md`

## Summary of implementation

- Added `AcqModality` in `src/acqstore/acq_types.py` and set `AcqTrace.modality` to `AcqModality.TRACE`.
- Kept ABF trace support backend-only under `src/acqstore/` with no CloudScope GUI changes.
- Added per-sweep trace table support through `SweepData.as_dataframe()` and `AcqTrace.get_sweep_trace_table()`.
- Added wide channel trace table support through `AcqTrace.get_channel_trace_table()` with columns such as `time_sec`, `sweep_0`, `sweep_0_command`, and `sweep_0_epoch`.
- Added compact epoch interval table support through `EpochTable.to_dataframe()` and `AcqTrace.get_epoch_table()`.
- Added trace-specific JSON sidecar persistence with version, modality, accepted state, experiment metadata, and trace header metadata. Image-only fields such as ROIs, image contrast, image header metadata, and analysis are intentionally excluded.
- Updated `scripts/acqstore/try_abfile.py` to plot all sweeps using Plotly with three linked rows: recorded values, command waveform, and epoch labels.
- Deferred `TraceAnalysisSet` and peak-detection integration because the existing image `AcqAnalysisSet` is keyed by ROI-oriented `AnalysisKey` and should not be forced onto trace/sweep/epoch analysis.

## Tests added or modified

- Added ABF fixture files under `tests/acqstore/data/abf/`.
- Added/expanded `tests/acqstore/test_abf_trace_loader.py` for header, sweep, command, epoch, validation, and info behavior.
- Added/expanded `tests/acqstore/test_acq_trace.py` for `AcqTrace`, trace tables, epoch tables, sidecar persistence, modality, lazy lifecycle placeholders, and data model validation.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_abf_trace_loader.py tests/acqstore/test_acq_trace.py
uv run pytest tests/acqstore/test_public_imports.py
```

## Test results

```text
35 passed in 0.25s
2 passed in 0.03s
```

## Concerns or follow-ups

- `TraceAnalysisSet` is still intentionally deferred. The next analysis pass should define trace-native keys based on channel, sweep, and probably epoch membership for result rows rather than reusing image ROI IDs.
- `AcqTrace.load_lazy_data()` and `AcqTrace.unload_lazy_data()` are no-ops because `AcqTrace` does not cache sweeps yet. Add explicit cache lifecycle later if large ABF files make repeated pyABF sweep loading too expensive.
- Sidecar loading currently persists experiment metadata and accepted state; trace header metadata is recorded for inspection but not applied back onto the pyABF-derived runtime header.
