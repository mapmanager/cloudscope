# End User Guide

CloudScope lets you load scientific image files, inspect image data, define or select ROIs, run supported analyses, and export results.

Current quantitative analysis workflows are designed for **line scan kymographs** and include:

- blood flow velocity analysis from line scan kymographs
- vessel diameter analysis from line scan kymographs

CloudScope can load and visualize supported scientific image formats, but the currently implemented quantitative analyses are designed for line scan data.

## Try CloudScope in a browser

The fastest way to try CloudScope is the public browser application:

[Open the CloudScope Web Application](https://cloudscope.mapmanager.net){target="_blank" rel="noopener"}

The browser application uses the same CloudScope GUI and the same `acqstore` scientific backend as the desktop application.

## Install the desktop app

CloudScope desktop is the same application on macOS and Windows. Choose the build for your operating system from the [CloudScope Releases](https://github.com/mapmanager/cloudscope/releases){target="_blank" rel="noopener"} page.

Use official releases when you need stable, repeatable analysis results. Released desktop builds and the matching source code are archived so you can return to the same version later.

## Supported file formats

CloudScope supports commercial microscopy formats and open scientific image formats:

| Format | Notes |
|---|---|
| `.oir` | Olympus / Evident |
| `.czi` | Zeiss |
| `.tif` | TIFF image files |
| `.ome.zarr` | OME-Zarr datasets |

Support for commercial microscopy formats builds on the scientific Python ecosystem. CloudScope gratefully acknowledges [Christoph Gohlke](https://www.cgohlke.com/){target="_blank" rel="noopener"} for long-standing work on microscopy and scientific file-format tooling.

## Sample data

CloudScope integrates with the [cloudscope-data Repository](https://github.com/mapmanager/cloudscope-data){target="_blank" rel="noopener"}. The GUI can fetch sample data so you can try the application without first locating your own image files.

Sample data is useful for learning the interface, testing analysis workflows, and confirming that a new installation is working.

## Basic workflow

A typical CloudScope workflow is:

1. Open CloudScope in the browser or launch the desktop app.
2. Load sample data or open local image files.
3. Select an image file in the file list.
4. Inspect the image and choose or create an ROI.
5. Run a supported analysis.
6. Inspect results in the GUI.
7. Save or export results.

See [Using the GUI](gui.md) for a visual guide to the main interface.

## Saved files

CloudScope saves analysis state and tabular results next to the source image file.

For a source file named `my_file.tif`, CloudScope may save:

```text
my_file.tif
my_file.tif.json
my_file.tif.radon_velocity.csv
my_file.tif.diameter.csv
```

The JSON sidecar stores metadata, ROIs, analysis parameters, and analysis summaries. Analysis CSV files store tabular outputs for analyses that provide CSV export.

Do not delete the `.json` or `.csv` files if you want CloudScope to reload prior ROIs, parameters, and results.

## Current limitations

CloudScope is a general scientific image loading and visualization application, but the current quantitative analysis workflows are focused on line scan kymographs.

Traditional two-dimensional image analysis workflows are not yet implemented as dedicated CloudScope analysis modules.

## Where to go next

- [Using the GUI](gui.md)
- [End-user recipes](recipes.md)
- [Data Scientist Guide](../scientists/)
