# 079 Sum intensity GUI integration docs report

## Files changed

- `src/acqstore/acq_image/analysis/sum_intensity_analysis/README.md`
- `docs-dev/acqstore/analysis/sum_intensity_architecture.md`

## Summary of implementation

Added concrete documentation for future CloudScope sum-intensity GUI work. The docs now include pseudo-code for a `SumIntensityParametersView`, pseudo-code for a `SumIntensityPlotView`, explicit detection-parameter names and units, manual F0 workflow guidance, and a NiceGUI CPU-bound execution note.

## Tests added or modified

None. Documentation-only update.

## Exact test commands run

Not run; documentation-only update.

## Test results

Not applicable.

## Concerns or follow-ups

- The pseudo-code intentionally leaves exact CloudScope controller/event/helper names to the GUI implementation ticket.
- The plotting pseudo-code assumes the planned `PlotlyPlotWidget.plot_scatter()` method exists.
