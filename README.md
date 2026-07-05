# CloudScope

[![Tests](https://github.com/mapmanager/cloudscope/actions/workflows/tests.yml/badge.svg)](https://github.com/mapmanager/cloudscope/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/mapmanager/cloudscope/branch/main/graph/badge.svg)](https://codecov.io/gh/mapmanager/cloudscope)

CloudScope is a desktop and browser application for viewing, annotating, and analyzing acquisition-backed microscopy files. It is designed for scientific image-analysis workflows where the same data and analysis code should be available from the GUI, from scripts, and from reproducible examples.

The desktop app, browser app, and Python scripting workflows all use the same `acqstore` scientific backend. This is central to CloudScope's reproducibility model: GUI workflows and scripted workflows should execute the same backend analysis code rather than separate reimplementations.

## Try CloudScope

- **Web app:** <https://cloudscope.mapmanager.net>
- **Desktop downloads:** <https://github.com/mapmanager/cloudscope/releases>

The web app is the fastest way to try CloudScope before installing a desktop build. The desktop apps provide the same core GUI and backend analysis workflow for local use on macOS and Windows.

## Supported file formats

CloudScope provides native support for commercial microscopy formats and open scientific image formats, including:

- Olympus / Evident `.oir`
- Zeiss `.czi`
- TIFF `.tif`
- OME-Zarr `.ome.zarr`

## Scientific workflows

CloudScope supports ROI-based image analysis workflows including velocity analysis and diameter analysis. The GUI is optimized for interactive use with linked panels and widgets, while the backend analysis engine remains scriptable through Python.

Visualization and analysis are optimized separately. CloudScope can use image pyramids to display only the resolution required for the current view while preserving full-resolution image data for backend `acqstore` analysis. Intensive analysis paths can use multiprocessing or multithreading where available, and the same acceleration paths are available from the GUI and scripts.

## Sample data

Example datasets are maintained in the companion repository:

<https://github.com/mapmanager/cloudscope-data>

The CloudScope GUI includes a menu item to load sample data. The same data can also be fetched from Python scripts and notebooks through `acqstore.sample_data`.

## Documentation

Full documentation is built with MkDocs and organized by user type:

- End users: installing, launching, opening data, running analysis, and using the GUI.
- Scientific users and data scientists: algorithms, parameters, results, notebooks, and scripting with `acqstore`.
- Developers: architecture, local development, testing, desktop builds, deployment, and contributing.

Documentation site: <https://mapmanager.github.io/cloudscope/>

## Minimal developer workflow

Clone the repository, install dependencies with `uv`, and run the app locally:

```bash
uv sync
uv run python src/cloudscope/app.py
```

Run in browser mode:

```bash
CLOUDSCOPE_NATIVE=0 uv run python src/cloudscope/app.py
```

Run tests:

```bash
uv run pytest
```

Build and serve docs locally:

```bash
uv sync --group docs
uv run mkdocs serve
```

See the developer documentation for Docker, environment variables, testing with coverage, and release builds.

 
 