# Sum intensity analysis

Sum intensity analysis measures **normalized line intensity** along a line scan kymograph ROI
and detects transient peaks from a **functional reporter (like GCaMP)**. The analysis computes
delta-F over F0 (df/f0), applies derivative-threshold onset detection by default, and refines
peak locations in a search window around each onset.

## Before you start

- Load a **line scan kymograph** (`.oir`, `.czi`, `.tif`, or `.ome.zarr`).
- Select or create a **rectangular ROI** covering the region to analyze.

See [Open data](index.md#open-data) and [Using the GUI](../gui.md) for loading files and ROIs.

## Run sum intensity analysis in the GUI

1. Select the file, channel, and ROI in the file list.
2. Open the left navigation toolbar and click **Sum Intensity** (functions icon).
3. Choose a **Detection preset** (**fast**, **medium**, or **slow**) or tune individual
   detection parameters.
4. Click **Run Sum Intensity Analysis**.
5. Inspect the plot: df/f0 trace, derivative, onset markers, and peak markers.
6. Use **Save** in the main toolbar to persist results.

![CloudScope sum intensity analysis view](../../assets/gui/sum-intensity-analysis-view.png){ .cs-screenshot .cs-screenshot-center width="980" loading=lazy }

Optional plot overlays (context menu on the sum-intensity plot):

- Show or hide the **derivative** trace on the secondary y-axis.
- Show or hide a **diameter** trace when diameter analysis has been run on the same file,
  channel, and ROI (default off).

## Saved files

For a source file named `my_file.tif`:

```text
my_file.tif.json
my_file.tif.sum_intensity.csv
```

The JSON sidecar stores detection parameters, summary values (for example peak count and F0
baseline), and event records. The CSV stores per-timepoint tabular traces and onset/peak
markers.

## See also

- [End-user recipes](index.md)
- [Sum Intensity Analysis (Data Scientist)](../../scientists/sum-intensity-analysis.md) — detection parameters, presets, and science detail
- [Sum Intensity Analysis Notebook](../../notebooks/sum-intensity-analysis.ipynb) — scripted workflow
