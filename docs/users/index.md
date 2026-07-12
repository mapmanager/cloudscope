# End User Guide

CloudScope lets you load raw image files, visualize image data, define and select ROIs, run supported analyses, and export results.

Current quantitative analysis workflows are designed for **line scan kymographs** and include:

- [*in vivo* blood flow velocity analysis](recipes/velocity-analysis.md)
- [vessel diameter analysis](recipes/diameter-analysis.md)
- [peak detection](recipes/sum-intensity-analysis.md) for functional fluorescence reporters (like GCaMP)

## Try CloudScope in a browser

The fastest way to try CloudScope is the public browser application:

[Open the CloudScope Web Application](https://cloudscope.mapmanager.net){target="_blank" rel="noopener"}

The browser app provides the same GUI and analysis workflows as the desktop app.

## Install the desktop app

CloudScope desktop is the same application on macOS and Windows. Download builds from the
[CloudScope Releases](https://github.com/mapmanager/cloudscope/releases){target="_blank" rel="noopener"}
page and follow the platform-specific steps in [Install the desktop app](install.md).

Use official releases when you need stable, repeatable analysis results. Released desktop builds,
checksum files, and matching source code are archived so you can return to the same version later.

## Supported file formats

CloudScope supports commercial microscopy formats — Olympus / Evident `.oir`, Zeiss `.czi`, and Nikon `.nd2` — and open image formats — TIFF `.tif` and OME-Zarr `.ome.zarr`.

See [Supported file formats](supported-file-formats.md) for format-specific notes.

Support for commercial microscopy formats builds on the Python imaging ecosystem. CloudScope gratefully acknowledges [Christoph Gohlke](https://www.cgohlke.com/){target="_blank" rel="noopener"} for long-standing work on microscopy and file-format tooling.

## Sample data

CloudScope integrates with the [cloudscope-data Repository](https://github.com/mapmanager/cloudscope-data){target="_blank" rel="noopener"}. From the **history menu** (:material-menu:{ .middle }) in the [load/save controls](gui.md#top-header-and-loadsave-controls), choose:

- **Load Velocity Sample Data** — OIR kymograph data for velocity analysis
- **Load Diameter Sample Data** — TIFF kymograph data for diameter analysis

CloudScope downloads and caches the sample folder automatically. Sample data is useful for learning the interface, testing analysis workflows, and confirming that a new installation is working.

See [Using the GUI](gui.md#getting-started-with-sample-data) for screenshots and menu details.

## Basic workflow

A typical CloudScope workflow is:

1. Open CloudScope in the browser or launch the desktop app.
2. Load sample data from the history menu, or open local image files.
3. Select an image file in the file list.
4. Visualize the image and choose or create an ROI.
5. Run a supported analysis.
6. Review results in the GUI.
7. Save or export results.

See [Using the GUI](gui.md) for a visual guide to the main interface.

For comparing analysis results across a loaded folder, see [Pool plots](pool-plots.md).

## Saved files

CloudScope saves analysis state and tabular results next to the source image file. For a source
file named `my_file.tif`, saved files may include:

```text
my_file.tif
my_file.tif.json
my_file.tif.radon_velocity.csv
my_file.tif.diameter.csv
my_file.tif.sum_intensity.csv
```

The JSON file stores metadata, ROIs, analysis parameters, and analysis summaries. CSV files store tabular outputs for analyses that provide CSV export.

Do not delete the `.json` or `.csv` files if you want CloudScope to reload prior ROIs, parameters, and results.

See [Saved file formats](saved-files.md) for a complete description of JSON and CSV contents, including velocity events and each analysis type.

## Current limitations

CloudScope is a general image loading and visualization application, but the current quantitative analysis workflows are focused on line scan kymographs.

Traditional two-dimensional image analysis workflows are not yet implemented as dedicated CloudScope analysis modules.

## Where to go next

- [Install the desktop app](install.md)
- [Using the GUI](gui.md)
- [Pool plots](pool-plots.md)
- [Saved file formats](saved-files.md)
- [End-user recipes](recipes/index.md)
- [Data Scientist Guide](../scientists/index.md)
