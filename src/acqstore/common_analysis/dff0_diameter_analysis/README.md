# ΔF/F₀–Diameter Cross-Analysis

## Purpose

This package compares a continuous functional-reporter trace with a continuous
diameter trace from exactly one file, channel, and ROI. The reporter may encode
calcium, ATP, voltage, or another biological quantity. The implementation must
not assign a biological identity to the reporter.

The first development milestone establishes trustworthy loading, selection,
time alignment, diameter preprocessing, reporter-event access, and interactive
visual inspection. Reporter-triggered diameter response measurements will be
added after these foundations are inspected on real data.

## Inputs

Each source acquisition is represented by three colocated CloudScope sidecars:

- `<name>.diameter.csv`
- `<name>.sum_intensity.csv`
- `<name>.json`

A raw-data absolute path and pooled `_peaks.csv` file are not required. The JSON
contains the structured peak-event results for the file. Channel and ROI are
still mandatory because the sidecars may contain multiple selections.

## Current coordinate assumptions

Both upstream analyses produce one row per kymograph line scan. Internally,
analysis uses integer point indices:

- diameter `center_row`
- sum-intensity `time_index`
- peak-event `onset.index` and `peak.index`

The loader verifies that indices, timestamps, sample count, and uniform sampling
interval agree before returning a dataset. Seconds and milliseconds remain the
preferred units for user-facing controls and are converted to points.

## Reporter events

Reporter onset is not redetected here. It is supplied by the existing
sum-intensity peak detector, where onset is defined by the configured derivative
threshold, filtering, refractory period, and related upstream parameters.

The JSON event record remains structured and available through `raw_event`.
Core onset and peak fields are also exposed as typed attributes and a flat
DataFrame.

## Diameter preprocessing

Cross-analysis starts from raw `diameter_um`, not the upstream
`diameter_um_filt` column. A local, explicit filter creates
`diameter_um_analysis` while retaining `diameter_um_raw`.

Initial supported filters:

- `none`
- centered rolling median with an odd kernel measured in points

Missing raw diameter samples remain missing after filtering.

## Scientific interpretation

The analysis can measure temporal order and coupling between reporter and
diameter signals. Temporal precedence alone must not be described as formal
causality. Absolute ΔF/F₀ amplitude depends on upstream baseline, detrending,
and F0 choices. Diameter remains in physical units.

## Current outputs

- strict one-channel/one-ROI loading from three sidecars
- alignment and missing-value diagnostics
- locally filtered raw diameter
- selected reporter-event table from JSON
- linked Plotly reporter and diameter traces
- reporter onset markers projected onto both traces
- minimal standalone NiceGUI explorer that rebuilds the full Plotly figure

## Planned next analysis

For each reporter onset, define an index-based window and measure a potential
diameter response:

- pre-event diameter baseline
- diameter response onset
- reporter-to-diameter latency, including an allowed negative lead
- contraction or dilation amplitude
- response slope
- time to diameter extremum
- recovery time and unresolved recovery status

The exact response rules and defaults should be decided after interactive review
of raw and filtered diameter around events.
