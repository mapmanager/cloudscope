# 006 AcqTrace peak detection report

## Files changed

- `scripts/acqstore/try_abfile.py`
- `src/acqstore/acq_trace/acq_trace.py`
- `src/acqstore/acq_trace/analysis/__init__.py`
- `src/acqstore/acq_trace/analysis/trace_peak_detection.py`
- `src/acqstore/acq_trace/analysis/trace_peak_params.py`
- `src/acqstore/acq_trace/analysis/trace_peak_result.py`
- `src/acqstore/acq_trace/readme-acq-trace.md`
- `src/acqstore/common_analysis/__init__.py`
- `src/acqstore/common_analysis/peak_detection_core.py`
- `tests/acqstore/test_acq_trace_peak_detection.py`

## Summary of implementation

Added backend-only trace peak detection for `AcqTrace` without changing CloudScope GUI, `AcqImageList`, image analysis classes, or the existing image `SumIntensityAnalysis` implementation.

The implementation adds a modality-neutral 1D peak detection core in `src/acqstore/common_analysis/peak_detection_core.py`. This shared core accepts only `time_sec`, `values`, and `PeakDetectionCoreParams`, and returns per-sample and per-peak DataFrames. It intentionally does not know about ABF files, sweeps, channels, epochs, ROIs, CSV files, or GUI state.

The trace-specific wrapper in `src/acqstore/acq_trace/analysis/trace_peak_detection.py` runs the shared core on one selected sweep or all sweeps for a channel. The default `sweep_index=None` analyzes all sweeps. Result tables include trace context such as channel, sweep, epoch, units, and global peak IDs across the analysis run.

`AcqTrace` now exposes a convenience method:

```python
trace.run_peak_detection(channel_index=0, sweep_index=None, params=params)
```

The development script now runs peak detection and overlays detected peaks on the first Plotly row while preserving the three-row layout: recorded values, DAC command, and epoch labels.

Added `src/acqstore/acq_trace/readme-acq-trace.md` to document current backend state, terminology, peak-detection design, sidecar JSON behavior, deferred `AcqAnalysisSet` work, and future CloudScope integration notes.

## Tests added or modified

Added `tests/acqstore/test_acq_trace_peak_detection.py`, covering:

- synthetic positive peak detection in the shared core
- synthetic negative peak detection in the shared core
- prominence and distance filters
- invalid trace array validation
- trace parameter conversion to core parameters
- one-sweep ABF peak detection
- all-sweeps ABF peak detection with `sweep_index=None`
- `AcqTrace.run_peak_detection(...)` delegation

## Exact test commands run

```bash
uv run pytest tests/acqstore/test_acq_trace_peak_detection.py
uv run pytest tests/acqstore/test_abf_trace_loader.py tests/acqstore/test_acq_trace.py tests/acqstore/test_acq_trace_peak_detection.py tests/acqstore/test_public_imports.py
```

## Test results

```text
tests/acqstore/test_acq_trace_peak_detection.py: 8 passed
combined focused suite: 45 passed
```

## Concerns or follow-ups

- Existing image `SumIntensityAnalysis` is not yet refactored to use `common_analysis.peak_detection_core.py`. This was intentionally deferred to avoid touching image analysis in this backend-only ABF pass.
- Trace peak results are not yet persisted through a trace-specific analysis set. A future pass should design `TraceAnalysisKey`, `TraceAnalysisSet`, and result CSV persistence without forcing sweep or epoch identifiers into image `roi_id` semantics.
- The shared core currently uses SciPy `find_peaks` with simple peak/time/width/prominence features. If feature parity with image sum-intensity analysis is required, future work should extend the shared core carefully and then migrate image sum-intensity to use it.
- The development script uses placeholder peak parameters. Users should adjust polarity, prominence, and minimum distance for their ABF data.
