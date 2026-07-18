# Saved file formats

When you save work in CloudScope, files are written **next to the source image file** on disk.
The original image file is never modified.

For a source file named `my_file.tif`, CloudScope may create:

```text
my_file.tif
my_file.tif.json
my_file.tif.radon_velocity.csv
my_file.tif.diameter.csv
my_file.tif.sum_intensity.csv
```

Which files appear depends on what you have loaded, edited, and analyzed. CloudScope reloads
saved files automatically the next time you open the source image.

Do not delete the `.json` or `.csv` files if you want CloudScope to restore prior metadata,
ROIs, parameters, and results.

## JSON file (`my_file.tif.json`)

The JSON file stores CloudScope state for one acquisition file. It includes:

| Content | Description |
|---|---|
| Accepted / rejected state | Whether the file is marked accepted in the file list |
| Experimental metadata | User-editable experiment fields (species, condition, notes, and related fields) |
| Image header metadata | Header fields read from the file, including physical unit and axis label calibration |
| ROIs | Line and rectangular regions of interest |
| Analysis records | One entry per analysis (velocity, diameter, peak detection, velocity events, and others) with detection parameters and summary values |
| Image contrast | Per-channel display contrast settings (when present) |

Analyses that produce large tabular output store **summaries and parameters** in the JSON file.
Row-by-row tables are stored in CSV files when an analysis provides CSV export.

### Analyses stored primarily in JSON

Some analyses do not write a separate CSV file:

| Analysis | JSON contents |
|---|---|
| **Velocity events** | Event definitions, event parameters, and event summary statistics (managed in the Velocity panel) |
| **Heart rate** | Summary values derived from a velocity time series (notebook workflow today; no dedicated GUI panel) |

See [Velocity event analysis](recipes/analyses-from-velocity/velocity-event-analysis.md) for
the GUI workflow.

## CSV files (tabular analysis output)

When an analysis produces a results table, CloudScope saves a CSV file named
`<source-file>.<analysis-name>.csv`.

| Analysis | CSV filename | Typical contents |
|---|---|---|
| Velocity (Radon) | `my_file.tif.radon_velocity.csv` | Per-window velocity measurements and related columns |
| Diameter | `my_file.tif.diameter.csv` | Per-line or per-profile diameter measurements |
| Sum intensity (peak detect) | `my_file.tif.sum_intensity.csv` | Detected peak events and related trace columns |

CSV files are suitable for export to spreadsheets or downstream Python analysis.

## Save actions in the GUI

From the load/save controls:

- **Save Selected** — saves the currently selected file when it has unsaved changes (metadata,
  ROIs, contrast, or analysis edits). Disabled when nothing is selected or the selection has no
  pending changes.
- **Save All** — saves every loaded file that has unsaved changes.

Both actions write the JSON file and any analysis CSV files that need updating for the affected
acquisition files.

## Export TIFF

CloudScope can also **export** TIFF files. These are separate from the JSON/CSV sidecars written
by **Save Selected** / **Save All**. Exports create a new TIFF; they do not modify the source
acquisition file.

| Action | Where | What is written |
|---|---|---|
| **Save As Tif...** | File list context menu | Primary acquisition pixels for the selected file as a TIFF (native save dialog on desktop; browser download in the web app). |
| **Save Reference As Tif** | Reference Image panel | Full multichannel reference/overview image as a TIFF when a reference is present. Suggested name is `<source-stem>-reference.tif`. ImageJ X/Y resolution is written from the reference spatial calibration when available. Scan paths and line ROIs are not burned into the exported pixels. |

## See also

- [End User Guide](index.md) — getting started and basic workflow
- [Using the GUI](gui.md) — load/save controls and interface overview
- [End-user recipes](recipes/index.md) — analysis workflows
- [AcqImage Metadata](../scientists/acqimage-metadata.md) — metadata fields in more detail (Data Scientist Guide)
