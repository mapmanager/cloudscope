# Reproducibility

CloudScope is designed so desktop GUI workflows, browser GUI workflows, scripts, and notebooks use the same `acqstore` scientific backend.

This is important for scientific reproducibility because analysis behavior should not depend on whether a user clicks through the GUI or calls the API from Python.

## Versioned releases

Official CloudScope releases are tied to git tags and published on the [CloudScope Releases](https://github.com/mapmanager/cloudscope/releases){target="_blank" rel="noopener"} page.

A published release provides a reproducible reference point for scientific analysis while allowing active development to continue.

Release artifacts can include:

- source code archives
- desktop application builds
- documentation builds
- version metadata

## Sidecar files

CloudScope saves analysis state and results next to the source image file.

For a source file named `my_file.tif`, saved files may include:

```text
my_file.tif.json
my_file.tif.radon_velocity.csv
my_file.tif.diameter.csv
```

The JSON sidecar records the ROIs, detection parameters, and analysis summaries used to generate results. These files should be retained with the source data when preserving an analysis.

## Same backend across interfaces

CloudScope uses the same `acqstore` backend from:

- desktop GUI
- browser GUI
- Python scripts
- Jupyter notebooks

This reduces divergence between interactive and scripted workflows.
