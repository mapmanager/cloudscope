# Heart rate analysis

Heart rate analysis estimates a **heartbeat frequency** (reported in **bpm** and **Hz**) from a
**velocity time series** produced by Radon velocity analysis on a line scan kymograph ROI.

!!! info "No GUI yet"
    Heart rate analysis is **not available in the CloudScope GUI** today. GUI support is planned.
    Use the notebook workflows below until a GUI panel is released.

## Before you start

1. Complete [velocity analysis](../velocity-analysis.md) for the file, channel, and ROI you want
   to analyze.
2. Install documentation dependencies if you will run notebooks locally:
   `uv sync --group docs`.

## Run heart rate analysis (notebook)

1. Open the [Heart Rate Analysis notebook](../../../notebooks/heart-rate-analysis.ipynb).
2. Load the same acquisition used for velocity analysis.
3. Select the channel and ROI with existing Radon velocity results.
4. Review heart rate detection parameters.
5. Run heart rate analysis and inspect the diagnostic plots.

For many files with the same parameter set, use the
[Heart Rate Batch Analysis notebook](../../../notebooks/heart-rate-batch-analysis.ipynb).

## Saved files

Heart rate results are stored in the acquisition JSON file only. There is no dedicated
heart rate CSV file. See [Saved file formats](../../saved-files.md).

## See also

- [Analyses from velocity](index.md)
- [Notebook workflows (Data Scientist)](../../../scientists/notebooks.md)
- [Velocity analysis](../velocity-analysis.md)
