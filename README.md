# CloudScope

[![Tests](https://github.com/mapmanager/cloudscope/actions/workflows/tests.yml/badge.svg)](https://github.com/mapmanager/cloudscope/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/mapmanager/cloudscope/branch/main/graph/badge.svg)](https://codecov.io/gh/mapmanager/cloudscope)

CloudScope is a desktop and browser application for viewing, annotating, and analyzing acquisition-backed microscopy files. It is designed for scientific image-analysis workflows where the same data and analysis code should be available from the GUI, from scripts, and from reproducible examples.

The desktop app, browser app, and Python scripting workflows all use the same Python powered scientific backend. This is central to CloudScope's reproducibility model: GUI workflows and scripted workflows should execute the same backend analysis code rather than separate reimplementations.

## Try CloudScope

- **Web app:** <https://cloudscope.mapmanager.net>
- **Desktop downloads:** <https://github.com/mapmanager/cloudscope/releases>

The web app is the fastest way to try CloudScope before installing a desktop build. The desktop apps provide the same core GUI and backend analysis workflow for local use on macOS and Windows.

## Supported file formats

CloudScope supports proprietary and commercial microscopy file formats, including Olympus/Evident (oir), Zeiss (czi), and Nikon (nd2). Open scientific image standards including tif, OME-Zarr, and NGFF are also supported.

See [Supported file formats](https://mapmanager.github.io/cloudscope/users/supported-file-formats/) for the full list and format-specific notes.

## Scientific workflows

CloudScope supports ROI-based image analysis workflows including:

- [Velocity analysis](https://mapmanager.github.io/cloudscope/users/recipes/velocity-analysis/)
- [Diameter analysis](https://mapmanager.github.io/cloudscope/users/recipes/diameter-analysis/)
- [Peak detection](https://mapmanager.github.io/cloudscope/users/recipes/sum-intensity-analysis/)
- Velocity-derived
    - [Heart-rate analysis](https://mapmanager.github.io/cloudscope/users/recipes/analyses-from-velocity/heart-rate-analysis/)
    - [Event analyses](https://mapmanager.github.io/cloudscope/users/recipes/analyses-from-velocity/velocity-event-analysis/)

Batch analysis runs across entire folders of raw image files.

For unbiased review, CloudScope supports a [blinded analysis mode](https://mapmanager.github.io/cloudscope/users/blinded-mode/) that hides file and condition identity in the GUI, and can be combined with a [randomized file subset](https://mapmanager.github.io/cloudscope/notebooks/generating-randomized-file-for-analysis/) drawn from a large dataset.

[Pool plots](https://mapmanager.github.io/cloudscope/users/pool-plots/) aggregate analysis results across all files in a loaded folder, so you can filter, group, and plot structured datasets using a range of plot types such as swarm, violin, histogram, and more. Pool plots update in real time as files, analyses, ROIs, and metadata change. CloudScope provides pool plots for [velocity analysis](https://mapmanager.github.io/cloudscope/users/recipes/velocity-analysis/) and [peak detection](https://mapmanager.github.io/cloudscope/users/recipes/sum-intensity-analysis/).

## GUI Optimized Workflows

The GUI is optimized for interactive use with linked panels and widgets, while the backend analysis engine remains scriptable through Python. Visualization and analysis are optimized separately. CloudScope uses image pyramids to display only the resolution required for the current view while preserving full-resolution image data for backend analysis, enabling real-time visualization of large raw image datasets. When working on large datasets, CloudScope supports lazy loading of raw data and analysis results. Analysis uses multiprocessing or multithreading where available, and the same acceleration paths are available from the GUI and scripts.

## Sample data

Example datasets are maintained in the companion repository:

<https://github.com/mapmanager/cloudscope-data>

The CloudScope GUI includes menu items to load the `velocity-sample-data` and `diameter-sample-data` datasets. The same datasets can also be fetched from Python scripts and notebooks through `acqstore.sample_data.ensure_sample()`.

## Documentation

Full documentation is organized by user type:

- [End users](https://mapmanager.github.io/cloudscope/users/): installing, launching, opening data, running analysis, using the GUI, blinded analysis mode, and supported file formats.
- [Scientific users](https://mapmanager.github.io/cloudscope/scientists/) and data scientists: algorithms, parameters, results, runnable notebooks (load and plot, velocity, diameter, peak detection, heart rate, and randomized analysis generation), and Python scripting.
- [Developers](https://mapmanager.github.io/cloudscope/developers/): architecture, local development, testing, desktop builds, deployment, and contributing.

See the [CloudScope documentation](https://mapmanager.github.io/cloudscope/) to get started.

## Developer Install

This workflow requires [uv](https://docs.astral.sh/uv/). Clone the repository, install dependencies, and run the app locally:

```bash
git clone git@github.com:mapmanager/cloudscope.git
cd cloudscope
uv sync
./scripts/run app
```

Run in browser mode:

```bash
./scripts/run web
```

Equivalent direct launches (from the repository root):

```bash
uv run python src/cloudscope/app.py
CLOUDSCOPE_NATIVE=0 uv run python src/cloudscope/app.py
```

Run tests:

```bash
uv run pytest
```

See the [developer documentation](https://mapmanager.github.io/cloudscope/developers/) for Docker, environment variables, testing with coverage, and release builds.
