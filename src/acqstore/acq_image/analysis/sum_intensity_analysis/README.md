# Sum intensity analysis and peak detection

This package implements the first backend-only pass of CloudScope sum-intensity
analysis. It is intentionally independent of CloudScope GUI code.

## Axis convention

The ROI image is a 2D array with shape `(time, space)`:

- dim 0 / rows: line-scan time, with spacing `seconds_per_line`.
- dim 1 / columns: spatial samples, with spacing `um_per_pixel`.

The analysis receives this image from `AnalysisDataProvider.get_roi_image()` and
physical spacing from `AnalysisDataProvider.get_image_physical_units()`.

## Signal pipeline

1. Compute row sums over the spatial dimension.
2. Apply optional rolling row-sum averaging using `window_radius_points`.
3. Compute `norm_sum_intensity = sum_intensity / image.shape[1]`.
4. Optionally median-filter the normalized trace. The default kernel is 3
   points, intended to remove one-line acquisition pops while preserving
   biological events when line-scan sampling is much faster than event kinetics.
5. Try single-exponential detrending for photobleaching:
   `a * exp(-b * t) + c`.
6. If detrending fails, record an analysis-level error and continue with the
   filtered normalized trace.
7. Estimate a scalar `F0` baseline from the filtered/detrended trace. The first
   pass uses a configurable percentile baseline, defaulting to the 20th
   percentile.
8. Compute `df_f_signal = (signal - F0) / F0`. Detection uses this trace by
   default, but `detection_source` may select another continuous trace.
9. Compute `d_df_f_signal = np.gradient(df_f_signal, time_sec)`, preserving one
   derivative value per original time point and expressing the derivative in
   `1 / second`.
10. Detect onsets using derivative threshold by default. Derivative-threshold
    detection is applied to the derivative of the selected `detection_source`.
11. Enforce onset-to-onset refractory period.
12. Search forward from each accepted onset within `peak_search_window_ms` to
    refine the peak.
13. Measure requested fractional widths such as 0.1, 0.2, 0.5, 0.8, and 0.9.
    Falling-side width crossings must occur within `width_search_window_ms`;
    otherwise the crossing status records a normal measurement failure.

## Delta-F over F0 baseline

Delta-F over F0 is useful because raw mean-line intensity still depends on
absolute fluorescence brightness, microscope settings, and image dtype. The
critical choice is how to estimate `F0`. This first pass uses a scalar
percentile baseline:

```python
F0 = percentile(filtered_or_detrended_norm_sum_intensity, baseline_percentile)
df_f_signal = (filtered_or_detrended_norm_sum_intensity - F0) / F0
```

The default `baseline_percentile` is 20.0. This is not intended to be the final
scientific answer for all recordings; it is a simple starting point that is
easy to plot, inspect, and tune. The result table stores `f0_baseline` and
`df_f_signal`, and the summary stores the baseline method and percentile. If F0
is zero or too close to zero, the algorithm records a warning and uses
`baseline_min_value` to avoid division by zero.

## Vectorized row-sum performance

A direct implementation of `window_radius_points` could loop over every time row,
extract a 2D band, average rows, and then sum pixels. That repeats overlapping
work for adjacent rows and can be expensive for 30,000-50,000 line scans.

This implementation uses an equivalent 1D formulation:

```python
row_sum = image.sum(axis=1)
sum_intensity = rolling_mean(row_sum, radius=window_radius_points)
norm_sum_intensity = sum_intensity / image.shape[1]
```

The rolling mean uses a cumulative-sum implementation with clipped edge windows.
This keeps the first pass KISS, NumPy-vectorized, and single-process. Threading
or multiprocessing should only be added after a benchmark proves this step is a
bottleneck.

## Failure model

Expected scientific failures are stored as data rather than thrown as runtime
exceptions.

- Analysis-level failures, such as `curve_fit` not converging during detrending,
  are recorded in the summary `errors` list and the algorithm falls back to the
  previous valid signal.
- Event-local failures are recorded in event `warnings` or `status` fields.
- Level-crossing failures are recorded in each crossing's `status`, for example
  `right_not_found_within_width_search_window` when a peak does not decay below
  the requested fraction within the configured width-search window.

Invalid API inputs still raise clear exceptions.

## Result table columns

The analysis table has one row per time point and includes:

- `time_index`
- `time_sec`
- `sum_intensity`
- `norm_sum_intensity`
- `filtered_norm_sum_intensity`
- `detrended_norm_sum_intensity`
- `f0_baseline`
- `df_f_signal`
- `d_df_f_signal`
- `is_onset`
- `is_peak`
- `onset_index`
- `peak_id`

## Backend API primitives

The public backend API avoids raw DataFrame column names and raw JSON parsing.
Callers should use enums and accessors:

- `SumIntensityTraceKey` names continuous traces such as `DF_F_SIGNAL` and
  `D_DF_F_SIGNAL`.
- `SumIntensityEventPointKey` names sparse marker collections such as `ONSETS`
  and `PEAKS`.
- `PeakWidthLevel` names standard width levels: 10, 20, 50, 80, and 90 percent
  of peak amplitude.
- `SumIntensitySummaryKey` names scalar summary values such as `F0_BASELINE`,
  `DETECTION_SOURCE`, and `SECONDS_PER_LINE`.

Typical access pattern:

```python
df_f = analysis.get_trace(SumIntensityTraceKey.DF_F_SIGNAL)
deriv = analysis.get_trace(SumIntensityTraceKey.D_DF_F_SIGNAL)
onsets = analysis.get_event_points(SumIntensityEventPointKey.ONSETS)
peaks = analysis.get_event_points(SumIntensityEventPointKey.PEAKS)
width_50 = analysis.get_width_trace(PeakWidthLevel.WIDTH_50)
all_widths = analysis.get_width_trace()
f0 = analysis.get_summary_value(SumIntensitySummaryKey.F0_BASELINE)
```

`get_width_trace()` returns NaN-separated line segments so frontend widgets can
plot all event widths with one ordinary line trace and `connectgaps=False`.

## Summary contents

The analysis summary stores compact run-level metadata and scalar results. It
does not store full traces; those live in the result table. It includes:

- `status`
- `num_timepoints`
- `num_peaks`
- `num_space_pixels`
- `seconds_per_line`
- `f0_baseline`
- `baseline_method`
- `baseline_percentile`
- `detection_source`
- `peak_search_window_ms`
- `width_search_window_ms`
- `peak_amplitude_mean`
- `peak_amplitude_median`
- `warnings`
- `errors`
- `peak_events`

`peak_events` is a list of one record per detected event. Each event contains
onset measurements, refined peak measurements, interval measurements, width
level crossings, event-local warnings, and event status.

## References

This implementation is designed to be compatible with CloudScope analysis
patterns while taking conceptual cues from SanPy, IPFX, eFEL, and
`scipy.signal.find_peaks`. The first pass does not call `find_peaks`; it keeps
onset detection and feature extraction explicit so CloudScope can serialize and
inspect each event.
