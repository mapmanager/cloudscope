# Diameter analysis

Diameter analysis estimates **vessel diameter from line scan kymographs**.

## Before you start

- Load a **line scan kymograph**.
- Select or create an **ROI** covering the vessel region to analyze.

See [Open data](index.md#open-data) and [Using the GUI](../gui.md) for loading files and ROIs.

## Run diameter analysis in the GUI

1. Select the file, channel, and ROI in the file list.
2. Open the left navigation toolbar and click **Diameter** (straighten icon).
3. Review **Detection parameters** in the Diameter panel.
4. Run the analysis.
5. Inspect the summary, quality-control values, and tabular output.
6. Use **Save** in the main toolbar to persist results.

## Saved files

For a source file named `my_file.tif`:

```text
my_file.tif.json
my_file.tif.diameter.csv
```

The JSON sidecar stores detection parameters and summary values (for example mean diameter and
QC scores). The CSV stores tabular diameter results.

## See also

- [End-user recipes](index.md)
- [Diameter Analysis (Data Scientist)](../../scientists/diameter-analysis.md) — detection parameters and science detail
