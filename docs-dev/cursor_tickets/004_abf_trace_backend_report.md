# 004 ABF trace backend report

## Files changed

- `pyproject.toml`
- `src/acqstore/acq_trace/__init__.py`
- `src/acqstore/acq_trace/acq_trace.py`
- `src/acqstore/acq_trace/epoch_data.py`
- `src/acqstore/acq_trace/file_loaders/__init__.py`
- `src/acqstore/acq_trace/file_loaders/abf_trace_loader.py`
- `src/acqstore/acq_trace/sweep_data.py`
- `src/acqstore/acq_trace/trace_header.py`
- `tests/acqstore/data/abf/2021_07_20_0002.abf`
- `tests/acqstore/data/abf/2021_07_20_0008.abf`
- `tests/acqstore/data/abf/2021_07_20_0013.abf`
- `tests/acqstore/data/abf/2021_07_20_0016.abf`
- `tests/acqstore/test_abf_trace_loader.py`
- `tests/acqstore/test_acq_trace.py`
- `scripts/acqstore/try_abfile.py`

## Summary of implementation

Added a backend-only ABF trace acquisition model in `src/acqstore/acq_trace/`.
The new code keeps electrophysiology files separate from `AcqImage` and does
not introduce image pixels, ROIs, contrast, image views, velocity analysis, or
diameter analysis concepts.

The implementation includes:

- `AcqTrace` as the public per-file trace acquisition object.
- `AbfTraceLoader` as the pyABF-backed loader.
- `TraceHeader` for ABF-level metadata.
- `SweepData` for one channel/sweep recording.
- `EpochInterval` and `EpochTable` for pyABF sweep epochs and per-sample labels.
- `AcqTrace.info()` / `AbfTraceLoader.info()` for script-friendly summaries.
- A Plotly-based `scripts/acqstore/try_abfile.py` script with a hard-coded path.

## Tests added or modified

Added focused unit tests for:

- ABF header metadata.
- Uploaded ABF sweep counts.
- Sweep data arrays and units.
- Command waveform access.
- Epoch interval extraction and per-sample labeling.
- Invalid channel/sweep indices.
- Missing files and directory paths.
- `AcqTrace` public API and metadata ownership.
- Trace dataclass validation.

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_abf_trace_loader.py tests/acqstore/test_acq_trace.py
```

## Test results

Passing:

```text
23 passed
```

## Any concerns or follow-ups

- This ticket intentionally does not modify `AcqImage`, `AcqImageList`,
  CloudScope GUI code, or analysis code.
- Future work should add a trace-table/peak-detection layer that can share logic
  with image-derived sum-intensity analysis without making ABF pretend to be an
  image acquisition.
- Future collection work can introduce a mixed acquisition list or a small
  acquisition protocol after the backend trace model is stable.
