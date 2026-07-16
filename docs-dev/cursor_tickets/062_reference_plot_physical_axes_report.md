# 062 Reference Plot Physical Axes

## Files changed

- `clients/neuronal_calcium_linescan/neuronal_calcium_linescan_analyzer_v1_18_b.html`
- `docs-dev/cursor_tickets/062_reference_plot_physical_axes_report.md`

## Summary of implementation

- Read each reference channel's `dx`, `dy`, `xUnit`, and `yUnit` fields from
  the AcqStore Server response.
- Converted reference heatmap coordinates from pixel indices to physical
  coordinates and labeled both Plotly axes with the server-provided units.
- Converted scan-path and line-ROI overlays to the same physical coordinate
  system and updated their hover labels.
- Added X/Y per-pixel scaling and units to the reference overview summary.
- Kept the change confined to the `_b.html` Plotly reference implementation;
  no Plotly callback behavior was changed.

## Tests added or modified

- None. This standalone HTML client has no automated test harness for the
  reference Plotly view.

## Exact test commands run

```bash
uv run python -m http.server 8768 --bind 127.0.0.1
git diff --check -- "clients/neuronal_calcium_linescan/neuronal_calcium_linescan_analyzer_v1_18_b.html"
```

## Test results

- Browser verification passed with a synthetic two-channel AcqStore response.
- Confirmed two plots rendered.
- Confirmed X coordinates used `dx`, Y coordinates used `dy`, and the line ROI
  used the same physical coordinate system.
- Confirmed both axis titles and hover labels displayed `micrometer`.
- Confirmed the summary displayed
  `X 0.5 micrometer/px · Y 2 micrometer/px`.
- IDE lint check reported no errors.
- `git diff --check` passed.

## Concerns or follow-ups

- None. Unit strings are displayed exactly as returned by AcqStore Server;
  this client does not rewrite `micrometer` to `µm`.
