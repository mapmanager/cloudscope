# Velocity analysis

Velocity analysis estimates **blood flow velocity from line scan kymographs** using a
Radon-transform-based method.

## Before you start

- Load a **line scan kymograph** (`.oir`, `.czi`, `.tif`, or `.ome.zarr`).
- Select or create an **ROI** covering the region to analyze.

See [Open data](index.md#open-data) and [Using the GUI](../gui.md) for loading files and ROIs.

## Run velocity analysis in the GUI

1. Select the file, channel, and ROI in the file list.
2. Open the left navigation toolbar and click **Velocity** (speed icon).
3. Review **Detection parameters** in the Velocity panel.
4. Click **Run Radon Analysis**.
5. Inspect the results summary and plotted output.
6. Use the copy button or **Save** in the main toolbar to keep results.

![CloudScope velocity analysis panel](../../assets/gui/velocity-analysis-panel.png){ .cs-screenshot .cs-screenshot-center width="980" loading=lazy }

Optional: click **Batch analysis** to preview or run velocity analysis across multiple loaded
files with shared ROI settings.

## Saved files

For a source file named `my_file.tif`:

```text
my_file.tif.json
my_file.tif.radon_velocity.csv
```

The JSON sidecar stores detection parameters and summary values. The CSV stores per-window
tabular velocity results.

## Next steps

- [Velocity event analysis](analyses-from-velocity/velocity-event-analysis.md) — mark events on
  velocity results (same Velocity panel, scroll down)
- [Analyses from velocity](analyses-from-velocity/index.md) — heart rate and other derived workflows
- [Velocity Analysis (Data Scientist)](../../scientists/velocity-analysis.md) — detection parameters and science detail
